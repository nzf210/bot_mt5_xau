from __future__ import annotations

import json
from pathlib import Path

from app.services.autopilot_service import resolve_runtime_guardrails

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "data" / "local_engine_settings.json"
DEFAULTS = {
    "spread_atr_max_ratio": 0.12,
    "rsi_bullish_threshold": 52.0,
    "rsi_bearish_threshold": 48.0,
    "min_rr_threshold": 1.0,
    "trend_strictness": "strict",
    "trend_mode": "ema_position",
}


def load_local_engine_settings() -> dict:
    if not SETTINGS_PATH.exists():
        base = dict(DEFAULTS)
    else:
        try:
            payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        base = dict(DEFAULTS)
        base.update(payload)

    runtime = resolve_runtime_guardrails({})
    preset = runtime.get("local_engine", {})
    merged = dict(base)
    for key, value in preset.items():
        merged[key] = value
    return merged


def update_local_engine_settings(*, spread_atr_max_ratio: float, rsi_bullish_threshold: float, rsi_bearish_threshold: float, min_rr_threshold: float, trend_strictness: str, trend_mode: str) -> dict:
    if spread_atr_max_ratio <= 0:
        raise ValueError("invalid_spread_atr_max_ratio")
    if not (0 <= rsi_bearish_threshold <= 100 and 0 <= rsi_bullish_threshold <= 100):
        raise ValueError("invalid_rsi_threshold")
    if min_rr_threshold <= 0:
        raise ValueError("invalid_min_rr_threshold")
    if trend_strictness not in {"strict", "moderate", "loose"}:
        raise ValueError("invalid_trend_strictness")
    if trend_mode not in {"ema_position", "ema_slope", "hybrid"}:
        raise ValueError("invalid_trend_mode")
    payload = load_local_engine_settings()
    payload["spread_atr_max_ratio"] = round(float(spread_atr_max_ratio), 4)
    payload["rsi_bullish_threshold"] = round(float(rsi_bullish_threshold), 2)
    payload["rsi_bearish_threshold"] = round(float(rsi_bearish_threshold), 2)
    payload["min_rr_threshold"] = round(float(min_rr_threshold), 2)
    payload["trend_strictness"] = trend_strictness
    payload["trend_mode"] = trend_mode
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
