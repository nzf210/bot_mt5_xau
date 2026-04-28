import sqlite3
from pathlib import Path
from app.utils.time_utils import utc_date, utc_now_iso


DB_PATH = Path("data/bot_state.sqlite3")


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_state_store() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signal_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                day TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                decision TEXT NOT NULL,
                filter_reason TEXT NOT NULL,
                passed_filter INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signal_events_day_symbol ON signal_events(day, symbol)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signal_events_symbol_timeframe ON signal_events(symbol, timeframe)"
        )
        conn.commit()


def record_signal_event(symbol: str, timeframe: str, decision: str, filter_reason: str, passed_filter: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO signal_events(ts, day, symbol, timeframe, decision, filter_reason, passed_filter) VALUES(?,?,?,?,?,?,?)",
            (utc_now_iso(), utc_date(), symbol, timeframe, decision, filter_reason, 1 if passed_filter else 0),
        )
        conn.commit()


def count_trades_today(symbol: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM signal_events WHERE day = ? AND symbol = ? AND passed_filter = 1 AND decision IN ('BUY','SELL')",
            (utc_date(), symbol),
        ).fetchone()
        return int(row["c"] if row else 0)


def is_duplicate_signal(symbol: str, timeframe: str, decision: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT decision, filter_reason FROM signal_events WHERE symbol = ? AND timeframe = ? ORDER BY id DESC LIMIT 1",
            (symbol, timeframe),
        ).fetchone()
        if not row:
            return False
        return row["decision"] == decision and row["filter_reason"] == "passed"


def get_last_passed_signal_ts(symbol: str, timeframe: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT ts FROM signal_events WHERE symbol = ? AND timeframe = ? AND passed_filter = 1 ORDER BY id DESC LIMIT 1",
            (symbol, timeframe),
        ).fetchone()
        return str(row["ts"]) if row else None
