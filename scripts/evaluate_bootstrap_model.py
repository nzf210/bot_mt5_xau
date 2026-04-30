from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix

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
    if "time" in df.columns:
        df = df.sort_values("time").reset_index(drop=True)
    split_idx = max(int(len(df) * 0.8), 1)
    valid_df = df.iloc[split_idx:].copy()
    if valid_df.empty:
        valid_df = df.copy()

    target_label = meta.get("target", "target_profitable")
    X = valid_df[feature_cols].copy()
    y = valid_df[target_label].astype(int)
    preds = model.predict(X)
    acc = float(accuracy_score(y, preds))
    bal_acc = float(balanced_accuracy_score(y, preds))
    report = classification_report(y, preds, output_dict=True)
    cm = confusion_matrix(y, preds).tolist()

    payload = {
        "ok": True,
        "rows": int(len(df)),
        "validation_rows": int(len(valid_df)),
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "confusion_matrix": cm,
        "report": report,
        "target": target_label,
        "intended_use": "secondary_quality_filter",
        "quality_filter_candidate": bal_acc >= 0.53 and len(valid_df) >= 100,
        "promotion_candidate": False,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
