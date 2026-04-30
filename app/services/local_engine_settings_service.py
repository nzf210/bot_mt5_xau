from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "data" / "local_engine_settings.json"
DEFAULTS = {
    "spread_atr_max_ratio": 0.12,
}


def load_local_engine_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULTS)
    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(DEFAULTS)
    if not isinstance(payload, dict):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update(payload)
    return merged


def update_local_engine_settings(*, spread_atr_max_ratio: float) -> dict:
    if spread_atr_max_ratio <= 0:
        raise ValueError("invalid_spread_atr_max_ratio")
    payload = load_local_engine_settings()
    payload["spread_atr_max_ratio"] = round(float(spread_atr_max_ratio), 4)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
