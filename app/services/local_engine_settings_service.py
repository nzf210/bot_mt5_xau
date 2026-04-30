from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "data" / "local_engine_settings.json"
DEFAULTS = {
    "spread_atr_max_ratio": 0.12,
    "rsi_bullish_threshold": 52.0,
    "rsi_bearish_threshold": 48.0,
    "min_rr_threshold": 1.0,
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


def update_local_engine_settings(*, spread_atr_max_ratio: float, rsi_bullish_threshold: float, rsi_bearish_threshold: float, min_rr_threshold: float) -> dict:
    if spread_atr_max_ratio <= 0:
        raise ValueError("invalid_spread_atr_max_ratio")
    if not (0 <= rsi_bearish_threshold <= 100 and 0 <= rsi_bullish_threshold <= 100):
        raise ValueError("invalid_rsi_threshold")
    if min_rr_threshold <= 0:
        raise ValueError("invalid_min_rr_threshold")
    payload = load_local_engine_settings()
    payload["spread_atr_max_ratio"] = round(float(spread_atr_max_ratio), 4)
    payload["rsi_bullish_threshold"] = round(float(rsi_bullish_threshold), 2)
    payload["rsi_bearish_threshold"] = round(float(rsi_bearish_threshold), 2)
    payload["min_rr_threshold"] = round(float(min_rr_threshold), 2)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
