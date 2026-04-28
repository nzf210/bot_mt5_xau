import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DECISION_LOG = ROOT / "logs" / "ai_decisions.jsonl"
OUTPUT = ROOT / "data" / "training" / "decision_dataset.csv"


def flatten_row(row: dict) -> dict:
    market = row.get("market", {})
    indicators = market.get("indicators", {})
    sr = market.get("support_resistance", {})
    trend = market.get("trend_context", {})
    pos = market.get("position_context", {})
    news = market.get("news_context", {}) or {}
    decision = row.get("decision", {})

    return {
        "timestamp": row.get("time", ""),
        "symbol": row.get("symbol", market.get("symbol", "")),
        "timeframe": row.get("timeframe", market.get("timeframe", "")),
        "higher_timeframe": market.get("higher_timeframe", ""),
        "session": market.get("session", ""),
        "mode": market.get("mode", ""),
        "bid": market.get("bid", 0),
        "ask": market.get("ask", 0),
        "spread": market.get("spread", 0),
        "ema20": indicators.get("ema20", 0),
        "ema50": indicators.get("ema50", 0),
        "rsi14": indicators.get("rsi14", 0),
        "macd_main": indicators.get("macd_main", 0),
        "macd_signal": indicators.get("macd_signal", 0),
        "atr14": indicators.get("atr14", 0),
        "support_1": sr.get("support_1", 0),
        "support_2": sr.get("support_2", 0),
        "resistance_1": sr.get("resistance_1", 0),
        "resistance_2": sr.get("resistance_2", 0),
        "htf_trend": trend.get("htf_trend", ""),
        "market_structure": trend.get("market_structure", ""),
        "momentum": trend.get("momentum", ""),
        "open_positions": pos.get("open_positions", 0),
        "has_buy_position": pos.get("has_buy_position", False),
        "has_sell_position": pos.get("has_sell_position", False),
        "mt5_news_available": news.get("mt5_news_available", False),
        "mt5_blackout_active": news.get("mt5_blackout_active", False),
        "mt5_reason": news.get("mt5_reason", ""),
        "ai_decision": decision.get("decision", ""),
        "decision": decision.get("decision", ""),
        "confidence": decision.get("confidence", 0),
        "entry": decision.get("entry", 0),
        "entry_price": decision.get("entry", 0),
        "stop_loss": decision.get("stop_loss", 0),
        "take_profit": decision.get("take_profit", 0),
        "risk_reward": decision.get("risk_reward", 0),
        "reason": decision.get("reason", ""),
        "passed_filter": decision.get("passed_filter", False),
        "filter_reason": decision.get("filter_reason", ""),
        "phase": row.get("phase", ""),
        "raw_model_text": row.get("raw_model_text", ""),
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not DECISION_LOG.exists():
        pd.DataFrame([]).to_csv(OUTPUT, index=False)
        print(f"No decision log found, wrote empty CSV to {OUTPUT}")
        return

    rows = []
    with DECISION_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(flatten_row(row))

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df)} decision rows to {OUTPUT}")


if __name__ == "__main__":
    main()
