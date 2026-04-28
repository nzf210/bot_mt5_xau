from datetime import datetime, timedelta, timezone
from app.services.state_store import get_conn
from app.services.symbol_service import get_symbol_currencies
from app.utils.time_utils import utc_now_iso


IMPACT_WINDOWS = {
    "high": (30, 30),
    "medium": (15, 15),
    "low": (0, 0),
}


def init_news_store() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                event_id TEXT NOT NULL,
                title TEXT NOT NULL,
                currency TEXT NOT NULL,
                impact TEXT NOT NULL,
                event_time TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                raw_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_events_time ON news_events(event_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_events_currency_time ON news_events(currency, event_time)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_news_events_source_event_id ON news_events(source, event_id)")
        conn.commit()


def cache_news_events(events: list[dict], source: str = "external") -> int:
    inserted = 0
    with get_conn() as conn:
        for event in events:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO news_events(source, event_id, title, currency, impact, event_time, fetched_at, raw_json) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        source,
                        str(event["event_id"]),
                        event["title"],
                        event["currency"],
                        event["impact"].lower(),
                        event["event_time"],
                        utc_now_iso(),
                        str(event),
                    ),
                )
                inserted += 1
            except Exception:
                continue
        conn.commit()
    return inserted


def get_relevant_news(symbol: str) -> list[dict]:
    currencies = get_symbol_currencies(symbol)
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in currencies)
        rows = conn.execute(
            f"SELECT * FROM news_events WHERE currency IN ({placeholders}) ORDER BY event_time ASC",
            tuple(currencies),
        ).fetchall()
    return [dict(row) for row in rows]


def has_external_news_blackout(symbol: str, now: datetime | None = None) -> tuple[bool, str, dict | None]:
    current = now or datetime.now(timezone.utc)
    for event in get_relevant_news(symbol):
        impact = str(event["impact"]).lower()
        if impact not in IMPACT_WINDOWS or impact == "low":
            continue
        before_min, after_min = IMPACT_WINDOWS[impact]
        try:
            event_dt = datetime.fromisoformat(str(event["event_time"]).replace("Z", "+00:00"))
        except ValueError:
            continue
        start = event_dt - timedelta(minutes=before_min)
        end = event_dt + timedelta(minutes=after_min)
        if start <= current <= end:
            return True, f"news_blackout_external_{impact}", event
    return False, "", None
