import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "bot_state.sqlite3"
DECISION_CSV = ROOT / "data" / "training" / "decision_dataset.csv"
OUTPUT = ROOT / "data" / "training" / "trade_outcome_dataset.csv"

QUERY = """
SELECT
  ts AS timestamp_open,
  symbol,
  timeframe,
  mode,
  decision,
  entry_price,
  close_price,
  stop_loss,
  take_profit,
  pnl,
  result,
  position_ticket
FROM trade_results
ORDER BY id DESC
"""

DECISION_ENRICH_COLS = [
    "symbol",
    "timeframe",
    "session",
    "confidence",
    "risk_reward",
    "spread",
    "ema20",
    "ema50",
    "rsi14",
    "macd_main",
    "macd_signal",
    "atr14",
    "htf_trend",
    "market_structure",
    "momentum",
]


def enrich_with_decision_data(trade_df: pd.DataFrame) -> pd.DataFrame:
    if trade_df.empty or not DECISION_CSV.exists():
        return trade_df

    decision_df = pd.read_csv(DECISION_CSV)
    if decision_df.empty:
        return trade_df

    available_cols = [c for c in DECISION_ENRICH_COLS if c in decision_df.columns]
    if "symbol" not in available_cols or "timeframe" not in available_cols:
        return trade_df

    dedup = decision_df[available_cols].drop_duplicates(subset=["symbol", "timeframe"], keep="last")
    return trade_df.merge(dedup, on=["symbol", "timeframe"], how="left")


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not DB.exists():
        pd.DataFrame([]).to_csv(OUTPUT, index=False)
        print(f"No SQLite DB found, wrote empty CSV to {OUTPUT}")
        return

    conn = sqlite3.connect(DB)
    try:
        df = pd.read_sql_query(QUERY, conn)
    except Exception:
        df = pd.DataFrame([])
    finally:
        conn.close()

    df = enrich_with_decision_data(df)
    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df)} trade rows to {OUTPUT}")


if __name__ == "__main__":
    main()
