from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "data" / "exports"
MODELS = ROOT / "models"
OUTPUT = EXPORTS / "approval_summary.json"


def read_json(path: Path, default):
    if not path.exists() or path.stat().st_size == 0:
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main() -> None:
    readiness = read_json(EXPORTS / "dataset_readiness.json", {})
    adaptive = read_json(EXPORTS / "adaptive_report.json", {})
    comparison = read_json(EXPORTS / "config_comparison.json", {})
    evaluation = read_json(MODELS / "reports" / "model_evaluation.json", {})
    rollback = read_json(EXPORTS / "rollback_trigger_check.json", {})

    candidate_env_exists = (EXPORTS / "candidate_config.env").exists()
    recommended_env_exists = (EXPORTS / "recommended_config.env").exists()
    candidate_model_exists = (MODELS / "candidates" / "candidate_model.pkl").exists()
    current_model_exists = (MODELS / "current" / "model.pkl").exists()

    summary = {
        "ok": True,
        "readiness_level": readiness.get("level"),
        "promotion_recommended": bool(evaluation.get("promotion_recommended", False)),
        "rollback_recommended": bool(rollback.get("rollback_recommended", False)),
        "candidate_config_exists": candidate_env_exists,
        "recommended_config_exists": recommended_env_exists,
        "candidate_model_exists": candidate_model_exists,
        "current_model_exists": current_model_exists,
        "config_comparison": comparison,
        "recommended_symbol_session_policy": adaptive.get("recommended_config_values", {}).get("recommended_symbol_session_policy", {}),
        "approval_notes": [],
    }

    if summary["readiness_level"] not in {"training_ready", "promotion_ready"}:
        summary["approval_notes"].append("dataset_not_ready_for_training_or_promotion")
    if summary["rollback_recommended"]:
        summary["approval_notes"].append("rollback_signal_active_review_before_any_apply")
    if not candidate_env_exists and recommended_env_exists:
        summary["approval_notes"].append("recommended_config_exists_but_candidate_not_prepared")
    if summary["promotion_recommended"] and not candidate_model_exists:
        summary["approval_notes"].append("promotion_recommended_but_candidate_model_missing")

    OUTPUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote approval summary to {OUTPUT}")


if __name__ == "__main__":
    main()
