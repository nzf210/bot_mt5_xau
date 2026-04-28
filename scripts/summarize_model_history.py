from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
HISTORY_JSONL = ROOT / "models" / "reports" / "model_evaluation_history.jsonl"
OUTPUT_JSON = ROOT / "models" / "reports" / "model_history_summary.json"


def main() -> None:
    if not HISTORY_JSONL.exists():
        print(f"Missing history file: {HISTORY_JSONL}")
        return

    rows = []
    for line in HISTORY_JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    summary = {
        "entries": len(rows),
        "latest": rows[-1] if rows else None,
    }
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote model history summary to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
