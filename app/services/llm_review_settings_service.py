from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "data" / "llm_review_settings.json"

DEFAULT_SETTINGS = {
    "enabled": True,
    "cadence": "3h",
    "last_run_at": None,
    "next_run_at": None,
    "last_status": None,
}

CADENCE_TO_HOURS = {
    "manual_only": None,
    "1h": 1,
    "3h": 3,
    "6h": 6,
    "12h": 12,
    "24h": 24,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.replace(microsecond=0).isoformat() if dt else None


def load_llm_review_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_SETTINGS.copy()
    merged = DEFAULT_SETTINGS.copy()
    merged.update(payload if isinstance(payload, dict) else {})
    return merged


def save_llm_review_settings(settings: dict) -> dict:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return settings


def update_llm_review_settings(enabled: bool | None = None, cadence: str | None = None) -> dict:
    settings = load_llm_review_settings()
    if enabled is not None:
        settings["enabled"] = bool(enabled)
    if cadence is not None:
        if cadence not in CADENCE_TO_HOURS:
            raise ValueError(f"invalid_cadence:{cadence}")
        settings["cadence"] = cadence
        if cadence == "manual_only":
            settings["next_run_at"] = None
        else:
            settings["next_run_at"] = _iso(_utc_now() + timedelta(hours=CADENCE_TO_HOURS[cadence] or 0))
    return save_llm_review_settings(settings)


def mark_llm_review_run(status: str) -> dict:
    settings = load_llm_review_settings()
    now = _utc_now()
    settings["last_run_at"] = _iso(now)
    settings["last_status"] = status
    cadence = settings.get("cadence", "3h")
    hours = CADENCE_TO_HOURS.get(cadence)
    settings["next_run_at"] = _iso(now + timedelta(hours=hours)) if hours else None
    return save_llm_review_settings(settings)


def llm_review_due(settings: dict | None = None) -> bool:
    settings = settings or load_llm_review_settings()
    if not settings.get("enabled", True):
        return False
    cadence = settings.get("cadence", "3h")
    if cadence == "manual_only":
        return False
    next_run_at = settings.get("next_run_at")
    if not next_run_at:
        return True
    try:
        next_dt = datetime.fromisoformat(str(next_run_at))
    except Exception:
        return True
    return _utc_now() >= next_dt
