from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from app.schemas import Candle, Indicators, MarketRequest, NewsContext, PositionContext, SupportResistance, TrendContext
from app.services.local_decision_engine import generate_local_decision
from app.services.risk_filter import apply_risk_filter

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "data" / "exports"


@dataclass
class ReplayConfig:
    symbol: str
    timeframe: str
    higher_timeframe: str
    mode: str
    lookback_bars: int
    outcome_horizon_bars: int
    session_tz: str = "UTC"


def load_bars(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    cols = {c.lower(): c for c in df.columns}
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in cols]
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    rename_map = {
        cols["time"]: "time",
        cols["open"]: "open",
        cols["high"]: "high",
        cols["low"]: "low",
        cols["close"]: "close",
    }
    if "spread" in cols:
        rename_map[cols["spread"]] = "spread"
    if "tick_volume" in cols:
        rename_map[cols["tick_volume"]] = "tick_volume"
    df = df.rename(columns=rename_map)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)
    if "spread" not in df.columns:
        df["spread"] = 0.0
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema50"] = out["close"].ewm(span=50, adjust=False).mean()

    delta = out["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    out["rsi14"] = 100 - (100 / (1 + rs.astype(float)))
    out["rsi14"] = out["rsi14"].fillna(50.0)

    ema12 = out["close"].ewm(span=12, adjust=False).mean()
    ema26 = out["close"].ewm(span=26, adjust=False).mean()
    out["macd_main"] = ema12 - ema26
    out["macd_signal"] = out["macd_main"].ewm(span=9, adjust=False).mean()

    prev_close = out["close"].shift(1)
    tr = pd.concat([
        (out["high"] - out["low"]),
        (out["high"] - prev_close).abs(),
        (out["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14).mean().fillna(0.0)

    out["support_1"] = out["low"].rolling(20).min().shift(1)
    out["support_2"] = out["low"].rolling(40).min().shift(1)
    out["resistance_1"] = out["high"].rolling(20).max().shift(1)
    out["resistance_2"] = out["high"].rolling(40).max().shift(1)

    out["ema20_htf"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema50_htf"] = out["close"].ewm(span=50, adjust=False).mean()
    out["htf_trend"] = "neutral"
    out.loc[out["ema20_htf"] > out["ema50_htf"], "htf_trend"] = "bullish"
    out.loc[out["ema20_htf"] < out["ema50_htf"], "htf_trend"] = "bearish"
    out["market_structure"] = "neutral"
    out.loc[out["ema20"] > out["ema50"], "market_structure"] = "higher_highs_higher_lows"
    out.loc[out["ema20"] < out["ema50"], "market_structure"] = "lower_highs_lower_lows"
    out["momentum"] = "neutral"
    out.loc[out["macd_main"] >= out["macd_signal"], "momentum"] = "bullish"
    out.loc[out["macd_main"] < out["macd_signal"], "momentum"] = "bearish"
    return out


def session_from_ts(ts: pd.Timestamp) -> str:
    hour = ts.hour
    if 0 <= hour < 7:
        return "Asia"
    if 7 <= hour < 12:
        return "London"
    if 12 <= hour < 16:
        return "Overlap"
    if 16 <= hour < 21:
        return "NewYork"
    return "Asia"


def build_market_request(df: pd.DataFrame, idx: int, cfg: ReplayConfig) -> MarketRequest:
    row = df.iloc[idx]
    hist = df.iloc[idx - cfg.lookback_bars + 1: idx + 1]
    ohlc = [
        Candle(
            t=bars.time.isoformat(),
            o=float(bars.open),
            h=float(bars.high),
            l=float(bars.low),
            c=float(bars.close),
        )
        for bars in hist.itertuples()
    ]
    close_price = float(row.close)
    spread = float(row.spread or 0.0)
    point_spread = spread if spread > 0 else max(close_price * 0.00005, 0.01)
    bid = close_price
    ask = close_price + point_spread
    return MarketRequest(
        symbol=cfg.symbol,
        timeframe=cfg.timeframe,
        higher_timeframe=cfg.higher_timeframe,
        session=session_from_ts(row.time),
        bid=bid,
        ask=ask,
        spread=point_spread,
        ohlc=ohlc,
        indicators=Indicators(
            ema20=float(row.ema20),
            ema50=float(row.ema50),
            rsi14=float(row.rsi14),
            macd_main=float(row.macd_main),
            macd_signal=float(row.macd_signal),
            atr14=float(row.atr14),
        ),
        support_resistance=SupportResistance(
            support_1=float(row.support_1 or close_price),
            support_2=float(row.support_2 or close_price),
            resistance_1=float(row.resistance_1 or close_price),
            resistance_2=float(row.resistance_2 or close_price),
        ),
        trend_context=TrendContext(
            htf_trend=str(row.htf_trend),
            market_structure=str(row.market_structure),
            momentum=str(row.momentum),
        ),
        position_context=PositionContext(open_positions=0, has_buy_position=False, has_sell_position=False),
        news_context=NewsContext(mt5_news_available=False, mt5_blackout_active=False, mt5_reason=""),
        mode=cfg.mode,
    )


def evaluate_outcome(df: pd.DataFrame, idx: int, decision, horizon: int) -> dict:
    if decision.decision not in {"BUY", "SELL"}:
        return {
            "outcome_label": "no_trade",
            "outcome_pnl": 0.0,
            "bars_held": 0,
            "tp_hit": False,
            "sl_hit": False,
            "mfe": 0.0,
            "mae": 0.0,
        }

    future = df.iloc[idx + 1: idx + 1 + horizon]
    if future.empty:
        return {
            "outcome_label": "insufficient_future",
            "outcome_pnl": 0.0,
            "bars_held": 0,
            "tp_hit": False,
            "sl_hit": False,
            "mfe": 0.0,
            "mae": 0.0,
        }

    entry = float(decision.entry)
    stop_loss = float(decision.stop_loss)
    take_profit = float(decision.take_profit)
    tp_hit = False
    sl_hit = False
    bars_held = 0
    mfe = 0.0
    mae = 0.0
    exit_price = float(future.iloc[-1].close)

    for i, row in enumerate(future.itertuples(), start=1):
        bars_held = i
        if decision.decision == "BUY":
            mfe = max(mfe, float(row.high) - entry)
            mae = min(mae, float(row.low) - entry)
            if float(row.low) <= stop_loss:
                sl_hit = True
                exit_price = stop_loss
                break
            if float(row.high) >= take_profit:
                tp_hit = True
                exit_price = take_profit
                break
        else:
            mfe = max(mfe, entry - float(row.low))
            mae = min(mae, entry - float(row.high))
            if float(row.high) >= stop_loss:
                sl_hit = True
                exit_price = stop_loss
                break
            if float(row.low) <= take_profit:
                tp_hit = True
                exit_price = take_profit
                break

    if decision.decision == "BUY":
        pnl = exit_price - entry
    else:
        pnl = entry - exit_price

    label = "tp_hit" if tp_hit else "sl_hit" if sl_hit else "expired_win" if pnl > 0 else "expired_loss" if pnl < 0 else "expired_flat"
    return {
        "outcome_label": label,
        "outcome_pnl": round(float(pnl), 6),
        "bars_held": bars_held,
        "tp_hit": tp_hit,
        "sl_hit": sl_hit,
        "mfe": round(float(mfe), 6),
        "mae": round(float(mae), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--higher-timeframe", default="H1")
    parser.add_argument("--mode", default="dry_run")
    parser.add_argument("--lookback-bars", type=int, default=10)
    parser.add_argument("--outcome-horizon-bars", type=int, default=12)
    parser.add_argument("--output-prefix", default="historical_replay")
    args = parser.parse_args()

    cfg = ReplayConfig(
        symbol=args.symbol,
        timeframe=args.timeframe,
        higher_timeframe=args.higher_timeframe,
        mode=args.mode,
        lookback_bars=args.lookback_bars,
        outcome_horizon_bars=args.outcome_horizon_bars,
    )

    EXPORTS.mkdir(parents=True, exist_ok=True)
    df = add_features(load_bars(Path(args.csv)))

    rows: list[dict] = []
    start_idx = max(cfg.lookback_bars - 1, 50)
    end_idx = len(df) - cfg.outcome_horizon_bars
    for idx in range(start_idx, max(start_idx, end_idx)):
        row = df.iloc[idx]
        if pd.isna(row.support_1) or pd.isna(row.resistance_1) or float(row.atr14) <= 0:
            continue
        market = build_market_request(df, idx, cfg)
        decision = generate_local_decision(market)
        filtered = apply_risk_filter(decision, market)
        outcome = evaluate_outcome(df, idx, filtered, cfg.outcome_horizon_bars)
        rows.append({
            "time": row.time.isoformat(),
            "symbol": cfg.symbol,
            "timeframe": cfg.timeframe,
            "session": market.session,
            "mode": cfg.mode,
            "decision": filtered.decision,
            "confidence": filtered.confidence,
            "entry": filtered.entry,
            "stop_loss": filtered.stop_loss,
            "take_profit": filtered.take_profit,
            "risk_reward": filtered.risk_reward,
            "reason": filtered.reason,
            "source": filtered.source,
            "passed_filter": filtered.passed_filter,
            "filter_reason": filtered.filter_reason,
            "ema20": market.indicators.ema20,
            "ema50": market.indicators.ema50,
            "rsi14": market.indicators.rsi14,
            "macd_main": market.indicators.macd_main,
            "macd_signal": market.indicators.macd_signal,
            "atr14": market.indicators.atr14,
            "spread": market.spread,
            "support_1": market.support_resistance.support_1,
            "support_2": market.support_resistance.support_2,
            "resistance_1": market.support_resistance.resistance_1,
            "resistance_2": market.support_resistance.resistance_2,
            "htf_trend": market.trend_context.htf_trend,
            "market_structure": market.trend_context.market_structure,
            "momentum": market.trend_context.momentum,
            **outcome,
        })

    replay_df = pd.DataFrame(rows)
    csv_out = EXPORTS / f"{args.output_prefix}_dataset.csv"
    json_out = EXPORTS / f"{args.output_prefix}_summary.json"
    replay_df.to_csv(csv_out, index=False)

    trade_rows = replay_df[replay_df["decision"].isin(["BUY", "SELL"]) ] if not replay_df.empty else replay_df
    summary = {
        "ok": True,
        "config": asdict(cfg),
        "input_csv": str(Path(args.csv)),
        "output_csv": str(csv_out),
        "rows": int(len(replay_df)),
        "trade_rows": int(len(trade_rows)),
        "buy_count": int((replay_df["decision"] == "BUY").sum()) if not replay_df.empty else 0,
        "sell_count": int((replay_df["decision"] == "SELL").sum()) if not replay_df.empty else 0,
        "wait_count": int((replay_df["decision"] == "WAIT").sum()) if not replay_df.empty else 0,
        "passed_filter_count": int((replay_df["passed_filter"] == True).sum()) if not replay_df.empty else 0,
        "tp_hit_count": int((replay_df["outcome_label"] == "tp_hit").sum()) if not replay_df.empty else 0,
        "sl_hit_count": int((replay_df["outcome_label"] == "sl_hit").sum()) if not replay_df.empty else 0,
        "net_outcome_pnl": round(float(replay_df["outcome_pnl"].sum()), 6) if not replay_df.empty else 0.0,
    }
    json_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
