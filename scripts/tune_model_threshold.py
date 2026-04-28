from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

ROOT = Path(__file__).resolve().parents[1]
TRADE_CSV = ROOT / "data" / "training" / "trade_outcome_dataset.csv"
CURRENT_MODEL = ROOT / "models" / "current" / "model.pkl"
CURRENT_META = ROOT / "models" / "current" / "model_meta.json"
OUTPUT_JSON = ROOT / "models" / "reports" / "model_threshold_tuning.json"


def main() -> None:
    if not TRADE_CSV.exists() or not CURRENT_MODEL.exists() or not CURRENT_META.exists():
        print("Missing trade dataset or current model/meta")
        return

    df = pd.read_csv(TRADE_CSV)
    if df.empty or "result" not in df.columns:
        print("Trade dataset empty or missing result")
        return

    meta = json.loads(CURRENT_META.read_text(encoding="utf-8"))
    feature_cols = meta.get("numeric_features", []) + meta.get("categorical_features", [])
    feature_cols = [c for c in feature_cols if c in df.columns]
    if not feature_cols:
        print("No usable feature columns for threshold tuning")
        return

    df = df.copy()
    df["target"] = (df["result"] == "win").astype(int)
    X = df[feature_cols]
    y = df["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y if len(set(y)) > 1 else None)

    model = joblib.load(CURRENT_MODEL)
    probs = model.predict_proba(X_test)[:, 1]

    candidates = []
    for threshold in [0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]:
        pred = (probs >= threshold).astype(int)
        acc = float(accuracy_score(y_test, pred))
        candidates.append({"threshold": threshold, "accuracy": round(acc, 4)})

    best = sorted(candidates, key=lambda x: (x["accuracy"], x["threshold"]), reverse=True)[0]
    payload = {
        "ok": True,
        "candidates": candidates,
        "recommended_model_score_threshold": best["threshold"],
        "best_accuracy": best["accuracy"],
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote threshold tuning report to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
