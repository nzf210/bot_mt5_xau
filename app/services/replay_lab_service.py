from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
STATUS_PATH = DATA_DIR / "learning" / "replay_lab_status.json"
SETTINGS_PATH = DATA_DIR / "replay_lab_settings.json"
DEFAULT_SETTINGS = {
    "csv_path": "data/imports/xauusd_m5.csv",
    "symbol": "XAUUSD",
    "timeframe": "M5",
    "higher_timeframe": "H1",
    "mode": "dry_run",
    "lookback_bars": 10,
    "outcome_horizon_bars": 12,
    "output_prefix": "xauusd_m5_replay",
}


def load_replay_lab_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(DEFAULT_SETTINGS)
    if not isinstance(payload, dict):
        return dict(DEFAULT_SETTINGS)
    merged = dict(DEFAULT_SETTINGS)
    merged.update(payload)
    return merged


def update_replay_lab_settings(**kwargs) -> dict:
    payload = load_replay_lab_settings()
    payload.update(kwargs)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def load_replay_lab_status() -> dict:
    if not STATUS_PATH.exists():
        return {"available": False}
    try:
        payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"available": False}
    payload["available"] = True
    return payload
