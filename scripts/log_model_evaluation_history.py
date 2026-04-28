from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
EVAL_REPORT = ROOT / "models" / "reports" / "model_evaluation.json"
HISTORY_JSONL = ROOT / "models" / "reports" / "model_evaluation_history.jsonl"


def main() -> None:
    if not EVAL_REPORT.exists():
        print(f"Missing evaluation report: {EVAL_REPORT}")
        return

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation": json.loads(EVAL_REPORT.read_text(encoding="utf-8")),
    }
    HISTORY_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"Appended model evaluation history to {HISTORY_JSONL}")


if __name__ == "__main__":
    main()
