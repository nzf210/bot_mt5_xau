from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.llm_review_client import run_periodic_llm_review
from app.services.llm_review_settings_service import llm_review_due, load_llm_review_settings, mark_llm_review_run

EXPORTS = ROOT / "data" / "exports"
OUTPUT = EXPORTS / "llm_periodic_review.json"


def read_json(path: Path, default):
    if not path.exists() or path.stat().st_size == 0:
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _build_review_payload(summary_lines: list[str], readiness: dict, adaptive: dict, approval: dict) -> dict:
    return {
        "summary_lines": summary_lines,
        "dataset_readiness": readiness,
        "adaptive_report_excerpt": {
            "best_pair_sessions": adaptive.get("best_pair_sessions", []),
            "worst_pair_sessions": adaptive.get("worst_pair_sessions", []),
            "recommended_config_values": adaptive.get("recommended_config_values", {}),
        },
        "approval_summary": {
            "readiness_level": approval.get("readiness_level"),
            "approval_notes": approval.get("approval_notes", []),
            "promotion_recommended": approval.get("promotion_recommended"),
            "rollback_recommended": approval.get("rollback_recommended"),
        },
    }


async def _run_review() -> dict:
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
        return payload

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

    llm_result = None
    llm_error = None
    try:
        review_payload = _build_review_payload(summary_lines, readiness, adaptive, approval)
        llm_json = await run_periodic_llm_review(review_payload)
        llm_result = {
            "provider": "openai_cli",
            "review": llm_json,
        }
    except Exception as exc:
        llm_error = str(exc)

    payload = {
        "ok": True,
        "skipped": False,
        "settings": settings,
        "summary": summary_lines,
        "llm_result": llm_result,
        "llm_error": llm_error,
        "recommended_actions": [
            "review ops dashboard",
            "inspect approval summary before applying any config changes",
            "continue collecting runtime decisions and trade outcomes",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mark_llm_review_run("ok" if llm_error is None else "error")
    return payload


def main() -> None:
    payload = asyncio.run(_run_review())
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
