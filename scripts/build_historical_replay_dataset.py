from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from app.schemas import Candle, Indicators, MarketRequest, NewsContext, PositionContext, SupportResistance, TrendContext
from app.services.local_decision_engine import generate_local_decision
from app.services.risk_filter import apply_risk_filter

EXPORTS = ROOT / "data" / "exports"


@dataclass
class ReplayConfig:
    symbol: str
    timeframe: str
    higher_timeframe: str
    mode: str
    lookback_bars: int
    outcome_horizon_bars: int
    point_size: float
    session_tz: str = "UTC"


def _read_csv_flexible(csv_path: Path) -> pd.DataFrame:
    candidates = [
        {"sep": ","},
        {"sep": ";"},
        {"sep": "\t"},
        {"sep": r"\s+", "engine": "python"},
        {"sep": None, "engine": "python"},
    ]
    last_error = None
    for kwargs in candidates:
        try:
            df = pd.read_csv(csv_path, **kwargs)
            if not df.empty or len(df.columns) > 1:
                return df
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return pd.read_csv(csv_path)


def _split_single_column_mt5(df: pd.DataFrame) -> pd.DataFrame:
    if len(df.columns) != 1:
        return df
    col = str(df.columns[0])
    if "<DATE>" not in col and "\t" not in col and " " not in col:
        return df

    rows = [col]
    rows.extend(df.iloc[:, 0].dropna().astype(str).tolist())
    split_rows = [row.strip().split() for row in rows if str(row).strip()]
    if len(split_rows) < 2:
        return df

    width = len(split_rows[0])
    if width < 5:
        return df

    normalized = []
    for parts in split_rows:
        if len(parts) >= width:
            normalized.append(parts[:width])
    if len(normalized) < 2:
        return df

    return pd.DataFrame(normalized[1:], columns=normalized[0])


def load_bars(csv_path: Path) -> pd.DataFrame:
    df = _read_csv_flexible(csv_path)
    df = _split_single_column_mt5(df)
    raw_cols = list(df.columns)
    normalized_cols = {str(c).strip().lower().replace(" ", "_"): c for c in raw_cols}

    rename_map: dict[str, str] = {}

    time_col = normalized_cols.get("time")
    date_col = normalized_cols.get("date")
    open_col = normalized_cols.get("open")
    high_col = normalized_cols.get("high")
    low_col = normalized_cols.get("low")
    close_col = normalized_cols.get("close")
    spread_col = normalized_cols.get("spread")
    tick_volume_col = normalized_cols.get("tick_volume") or normalized_cols.get("tickvol")

    if not time_col and date_col and "time" in normalized_cols:
        df["time_combined"] = df[date_col].astype(str).str.strip() + " " + df[normalized_cols["time"]].astype(str).str.strip()
        time_col = "time_combined"
    elif not time_col and date_col and "<time>" in normalized_cols:
        df["time_combined"] = df[date_col].astype(str).str.strip() + " " + df[normalized_cols["<time>"]].astype(str).str.strip()
        time_col = "time_combined"

    if not time_col and "<date>" in normalized_cols and "<time>" in normalized_cols:
        df["time_combined"] = df[normalized_cols["<date>"]].astype(str).str.strip() + " " + df[normalized_cols["<time>"]].astype(str).str.strip()
        time_col = "time_combined"

    if not open_col:
        open_col = normalized_cols.get("<open>")
    if not high_col:
        high_col = normalized_cols.get("<high>")
    if not low_col:
        low_col = normalized_cols.get("<low>")
    if not close_col:
        close_col = normalized_cols.get("<close>")
    if not spread_col:
        spread_col = normalized_cols.get("<spread>")
    if not tick_volume_col:
        tick_volume_col = normalized_cols.get("<tickvol>") or normalized_cols.get("tick_volume")
    if not time_col:
        time_col = normalized_cols.get("<date>")

    required_map = {
        "time": time_col,
        "open": open_col,
        "high": high_col,
        "low": low_col,
        "close": close_col,
    }
    missing = [key for key, value in required_map.items() if not value]
    if missing:
        raise ValueError(f"missing required columns: {missing} | raw_columns={raw_cols}")

    rename_map[time_col] = "time"
    rename_map[open_col] = "open"
    rename_map[high_col] = "high"
    rename_map[low_col] = "low"
    rename_map[close_col] = "close"
    if spread_col:
        rename_map[spread_col] = "spread"
    if tick_volume_col:
        rename_map[tick_volume_col] = "tick_volume"

    df = df.rename(columns=rename_map)
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    df = df.dropna(subset=["time", "open", "high", "low", "close"]).copy()
    for col in ["open", "high", "low", "close", "spread"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "tick_volume" in df.columns:
        df["tick_volume"] = pd.to_numeric(df["tick_volume"], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).copy()
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
    safe_avg_loss = avg_loss.replace(0, None)
    rs = avg_gain / safe_avg_loss
    out["rsi14"] = 100 - (100 / (1 + rs))
    out["rsi14"] = pd.to_numeric(out["rsi14"], errors="coerce").fillna(50.0)

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


def timeframe_to_pandas_rule(tf: str) -> str:
    mapping = {
        "M1": "1min",
        "M5": "5min",
        "M15": "15min",
        "M30": "30min",
        "H1": "1h",
        "H4": "4h",
        "D1": "1D",
    }
    return mapping.get(tf.upper(), "1h")


def build_htf_features(df: pd.DataFrame, higher_timeframe: str) -> pd.DataFrame:
    rule = timeframe_to_pandas_rule(higher_timeframe)
    htf = (
        df.set_index("time")[["open", "high", "low", "close"]]
        .resample(rule)
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
        .reset_index()
    )
    htf["ema20_htf"] = htf["close"].ewm(span=20, adjust=False).mean()
    htf["ema50_htf"] = htf["close"].ewm(span=50, adjust=False).mean()
    htf["htf_trend"] = "neutral"
    htf.loc[htf["ema20_htf"] > htf["ema50_htf"], "htf_trend"] = "bullish"
    htf.loc[htf["ema20_htf"] < htf["ema50_htf"], "htf_trend"] = "bearish"
    return htf[["time", "ema20_htf", "ema50_htf", "htf_trend"]]


def merge_htf_context(df: pd.DataFrame, higher_timeframe: str) -> pd.DataFrame:
    htf = build_htf_features(df, higher_timeframe).sort_values("time")
    base = df.sort_values("time").copy()
    merged = pd.merge_asof(base, htf, on="time", direction="backward")
    merged["htf_trend"] = merged["htf_trend"].fillna("neutral")
    return merged


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
    spread_points = float(row.spread or 0.0)
    spread_price = (spread_points * float(cfg.point_size)) if spread_points > 0 else max(close_price * 0.00005, float(cfg.point_size))
    bid = close_price
    ask = close_price + spread_price
    return MarketRequest(
        symbol=cfg.symbol,
        timeframe=cfg.timeframe,
        higher_timeframe=cfg.higher_timeframe,
        session=session_from_ts(row.time),
        bid=bid,
        ask=ask,
        spread=spread_points,
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
    parser.add_argument("--point-size", type=float, default=0.01)
    args = parser.parse_args()

    cfg = ReplayConfig(
        symbol=args.symbol,
        timeframe=args.timeframe,
        higher_timeframe=args.higher_timeframe,
        mode=args.mode,
        lookback_bars=args.lookback_bars,
        outcome_horizon_bars=args.outcome_horizon_bars,
        point_size=args.point_size,
    )

    EXPORTS.mkdir(parents=True, exist_ok=True)
    df = add_features(load_bars(Path(args.csv)))
    df = merge_htf_context(df, cfg.higher_timeframe)

    rows: list[dict] = []
    start_idx = max(cfg.lookback_bars - 1, 50)
    end_idx = len(df) - cfg.outcome_horizon_bars
    for idx in range(start_idx, max(start_idx, end_idx)):
        row = df.iloc[idx]
        if pd.isna(row.support_1) or pd.isna(row.resistance_1) or float(row.atr14) <= 0:
            continue
        market = build_market_request(df, idx, cfg)
        raw_decision = generate_local_decision(market)
        filtered = apply_risk_filter(raw_decision.model_copy(deep=True), market)
        outcome = evaluate_outcome(df, idx, filtered, cfg.outcome_horizon_bars)
        rows.append({
            "time": row.time.isoformat(),
            "symbol": cfg.symbol,
            "timeframe": cfg.timeframe,
            "session": market.session,
            "mode": cfg.mode,
            "raw_decision": raw_decision.decision,
            "raw_confidence": raw_decision.confidence,
            "raw_entry": raw_decision.entry,
            "raw_stop_loss": raw_decision.stop_loss,
            "raw_take_profit": raw_decision.take_profit,
            "raw_risk_reward": raw_decision.risk_reward,
            "raw_reason": raw_decision.reason,
            "raw_warnings": " | ".join(raw_decision.warnings or []),
            "filtered_decision": filtered.decision,
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
            "point_size": cfg.point_size,
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
    top_filter_reasons = {}
    top_raw_reasons = {}
    top_raw_warnings = {}
    if not replay_df.empty and "filter_reason" in replay_df.columns:
        counts = replay_df["filter_reason"].fillna("unknown").value_counts().head(10)
        top_filter_reasons = {str(k): int(v) for k, v in counts.items()}
    if not replay_df.empty and "raw_reason" in replay_df.columns:
        counts = replay_df["raw_reason"].fillna("unknown").value_counts().head(10)
        top_raw_reasons = {str(k): int(v) for k, v in counts.items()}
    if not replay_df.empty and "raw_warnings" in replay_df.columns:
        warning_counter: Counter[str] = Counter()
        for raw in replay_df["raw_warnings"].fillna("").tolist():
            for item in [part.strip() for part in str(raw).split("|") if part.strip()]:
                warning_counter[item] += 1
        top_raw_warnings = {str(k): int(v) for k, v in warning_counter.most_common(10)}
    summary = {
        "ok": True,
        "config": asdict(cfg),
        "input_csv": str(Path(args.csv)),
        "output_csv": str(csv_out),
        "rows": int(len(replay_df)),
        "trade_rows": int(len(trade_rows)),
        "raw_buy_count": int((replay_df["raw_decision"] == "BUY").sum()) if not replay_df.empty else 0,
        "raw_sell_count": int((replay_df["raw_decision"] == "SELL").sum()) if not replay_df.empty else 0,
        "raw_wait_count": int((replay_df["raw_decision"] == "WAIT").sum()) if not replay_df.empty else 0,
        "buy_count": int((replay_df["decision"] == "BUY").sum()) if not replay_df.empty else 0,
        "sell_count": int((replay_df["decision"] == "SELL").sum()) if not replay_df.empty else 0,
        "wait_count": int((replay_df["decision"] == "WAIT").sum()) if not replay_df.empty else 0,
        "passed_filter_count": int((replay_df["passed_filter"] == True).sum()) if not replay_df.empty else 0,
        "top_raw_reasons": top_raw_reasons,
        "top_raw_warnings": top_raw_warnings,
        "top_filter_reasons": top_filter_reasons,
        "tp_hit_count": int((replay_df["outcome_label"] == "tp_hit").sum()) if not replay_df.empty else 0,
        "sl_hit_count": int((replay_df["outcome_label"] == "sl_hit").sum()) if not replay_df.empty else 0,
        "net_outcome_pnl": round(float(replay_df["outcome_pnl"].sum()), 6) if not replay_df.empty else 0.0,
    }
    json_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
