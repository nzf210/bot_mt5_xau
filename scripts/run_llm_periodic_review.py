from __future__ import annotations

import json
from pathlib import Path

from app.services.llm_review_settings_service import llm_review_due, load_llm_review_settings, mark_llm_review_run

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "data" / "exports"
OUTPUT = EXPORTS / "llm_periodic_review.json"


def read_json(path: Path, default):
    if not path.exists() or path.stat().st_size == 0:
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main() -> None:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    settings = load_llm_review_settings()

    if not llm_review_due(settings):
        payload = {
            "ok": True,
            "skipped": True,
            "reason": "not_due",
            "settings": settings,
        }
        OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    adaptive = read_json(EXPORTS / "adaptive_report.json", {})
    readiness = read_json(EXPORTS / "dataset_readiness.json", {})
    approval = read_json(EXPORTS / "approval_summary.json", {})

    summary_lines = []
    if readiness:
        summary_lines.append(f"Dataset readiness: {readiness.get('level')}")
    best_pair_sessions = adaptive.get("best_pair_sessions", [])
    if best_pair_sessions:
        top = best_pair_sessions[0]
        summary_lines.append(f"Top pair-session currently: {top.get('symbol')} @ {top.get('session')} pnl={top.get('pnl_total')}")
    approval_notes = approval.get("approval_notes", [])
    if approval_notes:
        summary_lines.append("Approval notes: " + ", ".join(approval_notes[:3]))
    if not summary_lines:
        summary_lines.append("No major review findings yet. Continue collecting runtime data.")

    payload = {
        "ok": True,
        "skipped": False,
        "settings": settings,
        "summary": summary_lines,
        "recommended_actions": [
            "review ops dashboard",
            "inspect approval summary before applying any config changes",
            "continue collecting runtime decisions and trade outcomes",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mark_llm_review_run("ok")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
