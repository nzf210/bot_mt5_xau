from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "data" / "exports" / "adaptive_report.json"
COMPARE_JSON = ROOT / "data" / "exports" / "config_comparison.json"
HISTORY_JSONL = ROOT / "data" / "exports" / "adaptive_tuning_history.jsonl"


def main() -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "adaptive_report": json.loads(REPORT_JSON.read_text(encoding="utf-8")) if REPORT_JSON.exists() else {},
        "config_comparison": json.loads(COMPARE_JSON.read_text(encoding="utf-8")) if COMPARE_JSON.exists() else {},
    }
    HISTORY_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"Appended tuning history to {HISTORY_JSONL}")


if __name__ == "__main__":
    main()
