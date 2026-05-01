from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.autopilot_service import load_autopilot_summary
EXPORTS_DIR = ROOT / "data" / "exports"
LEARNING_DIR = ROOT / "data" / "learning"
STATUS_JSON = LEARNING_DIR / "learning_cycle_status.json"
LOG_JSONL = LEARNING_DIR / "learning_cycle_history.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_step(name: str, script_rel: str) -> dict:
    script_path = ROOT / script_rel
    started_at = utc_now()
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    ended_at = utc_now()
    return {
        "name": name,
        "script": script_rel,
        "started_at": started_at,
        "ended_at": ended_at,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def read_json(path: Path, default):
    if not path.exists() or path.stat().st_size == 0:
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_readiness_level() -> str:
    payload = read_json(EXPORTS_DIR / "dataset_readiness.json", {})
    return str(payload.get("level", "insufficient_data"))


def summarize_outputs() -> dict:
    return {
        "dataset_readiness": read_json(EXPORTS_DIR / "dataset_readiness.json", {}),
        "adaptive_report_exists": (EXPORTS_DIR / "adaptive_report.json").exists(),
        "model_evaluation": read_json(ROOT / "models" / "reports" / "model_evaluation.json", {}),
        "rollback_trigger": read_json(EXPORTS_DIR / "rollback_trigger_check.json", {}),
        "candidate_model_exists": (ROOT / "models" / "candidates" / "candidate_model.pkl").exists(),
        "current_model_exists": (ROOT / "models" / "current" / "model.pkl").exists(),
    }


def main() -> None:
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)

    autopilot = load_autopilot_summary()

    cycle = {
        "ok": True,
        "started_at": utc_now(),
        "finished_at": None,
        "steps": [],
        "gates": {},
        "outputs": {},
        "autopilot": autopilot,
    }

    base_steps = [
        ("build_decision_dataset", "scripts/build_decision_dataset.py"),
        ("build_trade_dataset", "scripts/build_trade_dataset.py"),
        ("check_dataset_readiness", "scripts/check_dataset_readiness.py"),
        ("run_adaptive_analytics", "scripts/run_adaptive_analytics.py"),
        ("check_rollback_trigger", "scripts/check_rollback_trigger.py"),
    ]

    for name, script in base_steps:
        step = run_step(name, script)
        cycle["steps"].append(step)
        if not step["ok"]:
            cycle["ok"] = False

    readiness_level = load_readiness_level()
    cycle["gates"]["readiness_level"] = readiness_level
    autopilot_effective = autopilot.get("effective", {})
    training_allowed_by_mode = bool(autopilot_effective.get("prepare_recommendations", False))
    cycle["gates"]["training_allowed_by_autopilot"] = training_allowed_by_mode
    allow_training = readiness_level in {"training_ready", "promotion_ready"} and training_allowed_by_mode
    cycle["gates"]["allow_training"] = allow_training

    if allow_training:
        for name, script in [
            ("train_setup_model", "scripts/train_setup_model.py"),
            ("evaluate_setup_model", "scripts/evaluate_setup_model.py"),
        ]:
            step = run_step(name, script)
            cycle["steps"].append(step)
            if not step["ok"]:
                cycle["ok"] = False
    else:
        skip_reason = f"readiness_level={readiness_level}"
        if not training_allowed_by_mode:
            skip_reason = f"autopilot_mode_blocks_training:{autopilot.get('mode')}"
        cycle["steps"].append({
            "name": "train_setup_model",
            "script": "scripts/train_setup_model.py",
            "skipped": True,
            "reason": skip_reason,
        })
        cycle["steps"].append({
            "name": "evaluate_setup_model",
            "script": "scripts/evaluate_setup_model.py",
            "skipped": True,
            "reason": skip_reason,
        })

    evaluation = read_json(ROOT / "models" / "reports" / "model_evaluation.json", {})
    promotion_recommended = bool(evaluation.get("promotion_recommended", False))
    cycle["gates"]["promotion_recommended"] = promotion_recommended
    allow_promotion = bool(autopilot_effective.get("allow_model_promotion", False)) and promotion_recommended
    cycle["gates"]["allow_promotion"] = allow_promotion

    if allow_promotion:
        step = run_step("promote_candidate_model", "scripts/promote_candidate_model.py")
        cycle["steps"].append(step)
        if not step["ok"]:
            cycle["ok"] = False
    else:
        reason = "manual_approval_required"
        if not autopilot_effective.get("allow_model_promotion", False):
            reason = f"autopilot_mode_blocks_promotion:{autopilot.get('mode')}"
        elif not promotion_recommended:
            reason = "promotion_not_recommended"
        cycle["steps"].append({
            "name": "promote_candidate_model",
            "script": "scripts/promote_candidate_model.py",
            "skipped": True,
            "reason": reason,
        })

    rollback_signal = read_json(EXPORTS_DIR / "rollback_trigger_check.json", {})
    if autopilot.get("mode") == "full" and autopilot_effective.get("apply_low_risk_tuning", False):
        if rollback_signal.get("rollback_recommended", False):
            cycle["steps"].append({
                "name": "autopilot_low_risk_tuning_apply",
                "script": "internal",
                "skipped": True,
                "reason": "rollback_signal_active",
            })
        elif cycle["gates"].get("allow_promotion"):
            cycle["steps"].append({
                "name": "autopilot_low_risk_tuning_apply",
                "script": "internal",
                "skipped": True,
                "reason": "promotion_path_active",
            })
        else:
            for name, script in [
                ("generate_config_recommendation", "scripts/generate_config_recommendation.py"),
                ("auto_apply_candidate_config", "scripts/auto_apply_candidate_config.py"),
                ("compare_config_vs_recommendation", "scripts/compare_config_vs_recommendation.py"),
                ("build_approval_summary", "scripts/build_approval_summary.py"),
            ]:
                step = run_step(name, script)
                cycle["steps"].append(step)
                if not step["ok"]:
                    cycle["ok"] = False
                    break

    cycle["outputs"] = summarize_outputs()
    cycle["finished_at"] = utc_now()

    STATUS_JSON.write_text(json.dumps(cycle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with LOG_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(cycle, ensure_ascii=False) + "\n")

    print(json.dumps({
        "ok": cycle["ok"],
        "status_file": str(STATUS_JSON),
        "history_file": str(LOG_JSONL),
        "readiness_level": readiness_level,
        "allow_training": allow_training,
        "promotion_recommended": promotion_recommended,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
