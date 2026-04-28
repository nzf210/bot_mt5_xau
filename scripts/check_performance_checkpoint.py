from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "data" / "exports" / "adaptive_report.json"
MODEL_EVAL_JSON = ROOT / "models" / "reports" / "model_evaluation.json"
OUTPUT_JSON = ROOT / "data" / "exports" / "performance_checkpoint.json"


def main() -> None:
    if not REPORT_JSON.exists():
        print(f"Missing report: {REPORT_JSON}")
        return

    report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    trade_results = report.get("best_symbols", [])
    top_filters = report.get("top_filter_reasons", [])
    recommended = report.get("recommended_config_values", {})

    model_eval = json.loads(MODEL_EVAL_JSON.read_text(encoding="utf-8")) if MODEL_EVAL_JSON.exists() else {}

    checkpoint = {
        "ok_to_consider_apply": bool(recommended),
        "has_trade_data": len(trade_results) > 0,
        "top_filter_reason": top_filters[0] if top_filters else None,
        "recommended_config_values": recommended,
        "model_evaluation": model_eval,
        "notes": [],
    }

    if not trade_results:
        checkpoint["notes"].append("No trade result data yet, treat recommendation as low confidence.")
    if recommended.get("recommended_min_confidence") is None:
        checkpoint["notes"].append("No strong confidence threshold recommendation yet.")
    if recommended.get("recommended_min_risk_reward") is None:
        checkpoint["notes"].append("No strong RR threshold recommendation yet.")
    if model_eval and not model_eval.get("promotion_recommended", False):
        checkpoint["notes"].append("Current candidate model is not recommended for promotion yet.")
        checkpoint["ok_to_consider_apply"] = False

    OUTPUT_JSON.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote performance checkpoint to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
