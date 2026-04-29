from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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

    cycle = {
        "ok": True,
        "started_at": utc_now(),
        "finished_at": None,
        "steps": [],
        "gates": {},
        "outputs": {},
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
    allow_training = readiness_level in {"training_ready", "promotion_ready"}
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
        cycle["steps"].append({
            "name": "train_setup_model",
            "script": "scripts/train_setup_model.py",
            "skipped": True,
            "reason": f"readiness_level={readiness_level}",
        })
        cycle["steps"].append({
            "name": "evaluate_setup_model",
            "script": "scripts/evaluate_setup_model.py",
            "skipped": True,
            "reason": f"readiness_level={readiness_level}",
        })

    evaluation = read_json(ROOT / "models" / "reports" / "model_evaluation.json", {})
    promotion_recommended = bool(evaluation.get("promotion_recommended", False))
    cycle["gates"]["promotion_recommended"] = promotion_recommended
    cycle["gates"]["allow_promotion"] = False

    cycle["steps"].append({
        "name": "promote_candidate_model",
        "script": "scripts/promote_candidate_model.py",
        "skipped": True,
        "reason": "manual_approval_required",
    })

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
