from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report

ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "data" / "exports" / "bootstrap_candidate_dataset.csv"
MODEL_PATH = ROOT / "models" / "bootstrap" / "bootstrap_model.pkl"
META_PATH = ROOT / "models" / "bootstrap" / "bootstrap_model_meta.json"
OUTPUT_JSON = ROOT / "models" / "bootstrap" / "bootstrap_model_evaluation.json"


def main() -> None:
    if not INPUT_CSV.exists() or not MODEL_PATH.exists() or not META_PATH.exists():
        raise SystemExit("missing bootstrap training artifacts")
    df = pd.read_csv(INPUT_CSV)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    model = joblib.load(MODEL_PATH)

    feature_cols = meta.get("numeric_features", []) + meta.get("categorical_features", [])
    X = df[feature_cols].copy()
    y = df["target_profitable"].astype(int)
    preds = model.predict(X)
    acc = float(accuracy_score(y, preds))
    report = classification_report(y, preds, output_dict=True)

    payload = {
        "ok": True,
        "rows": int(len(df)),
        "accuracy": round(acc, 4),
        "report": report,
        "promotion_candidate": acc >= 0.58,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
