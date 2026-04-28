from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "data" / "exports" / "adaptive_report.json"
OUTPUT_JSON = ROOT / "data" / "exports" / "rollback_trigger_check.json"


def main() -> None:
    if not REPORT_JSON.exists():
        print(f"Missing report: {REPORT_JSON}")
        return

    report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    worst_symbols = report.get("worst_symbols", [])
    trigger = {
        "rollback_recommended": False,
        "reasons": [],
    }

    for row in worst_symbols:
        if row.get("trade_count", 0) >= 3 and row.get("pnl_total", 0) < 0:
            trigger["rollback_recommended"] = True
            trigger["reasons"].append(
                f"Weak symbol persists: {row.get('symbol')} pnl={row.get('pnl_total')} trade_count={row.get('trade_count')}"
            )

    OUTPUT_JSON.write_text(json.dumps(trigger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote rollback trigger check to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
