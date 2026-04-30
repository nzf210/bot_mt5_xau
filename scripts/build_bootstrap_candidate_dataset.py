from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LEARNING_DIR = ROOT / "data" / "learning"
BASELINE_PATH = LEARNING_DIR / "replay_baseline.json"
OUTPUT_CSV = ROOT / "data" / "exports" / "bootstrap_candidate_dataset.csv"
OUTPUT_JSON = ROOT / "data" / "exports" / "bootstrap_candidate_summary.json"


def main() -> None:
    if not BASELINE_PATH.exists():
        raise SystemExit("missing replay baseline")
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    output_csv = Path(baseline.get("output_csv", ""))
    if not output_csv.exists():
        raise SystemExit(f"missing replay dataset csv: {output_csv}")

    df = pd.read_csv(output_csv)
    if df.empty:
        raise SystemExit("replay dataset empty")

    candidate = df[df["decision"].isin(["BUY", "SELL"])].copy()
    if candidate.empty:
        raise SystemExit("no tradable rows in replay dataset")

    candidate["target_profitable"] = candidate["outcome_pnl"].fillna(0.0) > 0
    candidate.to_csv(OUTPUT_CSV, index=False)

    summary = {
        "ok": True,
        "rows": int(len(candidate)),
        "buy_rows": int((candidate["decision"] == "BUY").sum()),
        "sell_rows": int((candidate["decision"] == "SELL").sum()),
        "profitable_rows": int(candidate["target_profitable"].sum()),
        "loss_rows": int((~candidate["target_profitable"]).sum()),
        "output_csv": str(OUTPUT_CSV),
    }
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
