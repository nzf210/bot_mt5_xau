from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "data" / "bootstrap_settings.json"
DEFAULTS = {
    "target_label": "target_profitable",
}


def load_bootstrap_settings() -> dict:
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


def update_bootstrap_settings(*, target_label: str) -> dict:
    if target_label not in {"target_profitable", "target_tp_hit", "target_rr_positive"}:
        raise ValueError("invalid_bootstrap_target_label")
    payload = load_bootstrap_settings()
    payload["target_label"] = target_label
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
