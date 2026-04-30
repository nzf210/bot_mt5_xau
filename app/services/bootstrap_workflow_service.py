from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "data" / "exports"
MODELS = ROOT / "models" / "bootstrap"
SETTINGS = ROOT / "data" / "bootstrap_settings.json"


def read_json(path: Path, default):
    if not path.exists() or path.stat().st_size == 0:
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_bootstrap_workflow_summary() -> dict:
    dataset = read_json(EXPORTS / "bootstrap_candidate_summary.json", {})
    model_meta = read_json(MODELS / "bootstrap_model_meta.json", {})
    evaluation = read_json(MODELS / "bootstrap_model_evaluation.json", {})
    settings = read_json(SETTINGS, {"target_label": "target_profitable"})
    return {
        "settings": settings,
        "dataset": dataset,
        "model": model_meta,
        "evaluation": evaluation,
    }
