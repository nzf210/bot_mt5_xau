from pathlib import Path
import os
import json

ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "data" / "exports" / "adaptive_report.json"
ENV_FILE = ROOT / ".env"
OUTPUT_JSON = ROOT / "data" / "exports" / "config_comparison.json"


def read_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def main() -> None:
    current = read_env(ENV_FILE)
    report = json.loads(REPORT_JSON.read_text(encoding="utf-8")) if REPORT_JSON.exists() else {}
    rec = report.get("recommended_config_values", {})

    comparison = {
        "MIN_CONFIDENCE": {
            "current": current.get("MIN_CONFIDENCE"),
            "recommended": rec.get("recommended_min_confidence"),
        },
        "MIN_RISK_REWARD": {
            "current": current.get("MIN_RISK_REWARD"),
            "recommended": rec.get("recommended_min_risk_reward"),
        },
        "DEFAULT_SESSION_ALLOWLIST": {
            "current": current.get("DEFAULT_SESSION_ALLOWLIST"),
            "recommended": ",".join(rec.get("recommended_allowed_sessions", [])),
        },
        "DISABLED_SYMBOLS": {
            "current": current.get("DISABLED_SYMBOLS"),
            "recommended": ",".join(rec.get("recommended_disabled_symbols", [])),
        },
    }

    OUTPUT_JSON.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote config comparison to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
