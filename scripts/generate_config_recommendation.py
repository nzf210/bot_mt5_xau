import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "data" / "exports" / "adaptive_report.json"
THRESHOLD_JSON = ROOT / "models" / "reports" / "model_threshold_tuning.json"
OUTPUT_ENV = ROOT / "data" / "exports" / "recommended_config.env"


def main() -> None:
    if not REPORT_JSON.exists():
        print(f"Missing report: {REPORT_JSON}")
        return

    report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    cfg = report.get("recommended_config_values", {})

    tuned_threshold = ""
    if THRESHOLD_JSON.exists():
        threshold_payload = json.loads(THRESHOLD_JSON.read_text(encoding="utf-8"))
        tuned_threshold = threshold_payload.get("recommended_model_score_threshold", "")

    lines = [
        f"MIN_CONFIDENCE={cfg.get('recommended_min_confidence', '')}",
        f"MIN_RISK_REWARD={cfg.get('recommended_min_risk_reward', '')}",
        f"MODEL_SCORE_THRESHOLD={tuned_threshold}",
        f"DEFAULT_SESSION_ALLOWLIST={','.join(cfg.get('recommended_allowed_sessions', []))}",
        f"DISABLED_SYMBOLS={','.join(cfg.get('recommended_disabled_symbols', []))}",
    ]
    OUTPUT_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote recommended config to {OUTPUT_ENV}")


if __name__ == "__main__":
    main()
