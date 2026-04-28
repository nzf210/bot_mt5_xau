import sqlite3
from app.services.state_store import get_conn
from app.utils.time_utils import utc_date, utc_now_iso


def init_result_store() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                day TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                mode TEXT NOT NULL,
                decision TEXT NOT NULL,
                position_ticket TEXT NOT NULL,
                entry_price REAL NOT NULL,
                close_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                pnl REAL NOT NULL,
                result TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trade_results_day_symbol ON trade_results(day, symbol)"
        )
        conn.commit()


def record_trade_result(symbol: str, timeframe: str, mode: str, decision: str, position_ticket: str, entry_price: float, close_price: float, stop_loss: float, take_profit: float, pnl: float, result: str, notes: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO trade_results(ts, day, symbol, timeframe, mode, decision, position_ticket, entry_price, close_price, stop_loss, take_profit, pnl, result, notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (utc_now_iso(), utc_date(), symbol, timeframe, mode, decision, position_ticket, entry_price, close_price, stop_loss, take_profit, pnl, result, notes),
        )
        conn.commit()


def fetch_trade_results_for_day(day: str | None = None) -> list[sqlite3.Row]:
    target_day = day or utc_date()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM trade_results WHERE day = ? ORDER BY id DESC",
            (target_day,),
        ).fetchall()
        return rows


def sum_pnl_for_day(day: str | None = None) -> float:
    target_day = day or utc_date()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(pnl), 0) AS total_pnl FROM trade_results WHERE day = ?",
            (target_day,),
        ).fetchone()
        return float(row["total_pnl"] if row else 0.0)
