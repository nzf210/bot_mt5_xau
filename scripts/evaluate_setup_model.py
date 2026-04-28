from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
TRADE_CSV = ROOT / "data" / "training" / "trade_outcome_dataset.csv"
CANDIDATE_MODEL = ROOT / "models" / "candidates" / "candidate_model.pkl"
CANDIDATE_META = ROOT / "models" / "candidates" / "candidate_model_meta.json"
CURRENT_MODEL = ROOT / "models" / "current" / "model.pkl"
CURRENT_META = ROOT / "models" / "current" / "model_meta.json"
REPORT_PATH = ROOT / "models" / "reports" / "model_evaluation.json"


def evaluate_model(model, X_test, y_test) -> dict:
    pred = model.predict(X_test)
    out = {
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
    }
    if hasattr(model, "predict_proba"):
        try:
            probs = model.predict_proba(X_test)[:, 1]
            out["roc_auc"] = round(float(roc_auc_score(y_test, probs)), 4)
        except Exception:
            out["roc_auc"] = None
    return out


def compare_metrics(candidate_metrics: dict, current_metrics: dict | None) -> dict:
    if not current_metrics:
        return {"candidate_better": True, "reasons": ["no_current_model"]}

    reasons = []
    candidate_better = True
    if candidate_metrics.get("accuracy", 0) < current_metrics.get("accuracy", 0):
        candidate_better = False
        reasons.append("candidate_accuracy_lower_than_current")
    if candidate_metrics.get("roc_auc") is not None and current_metrics.get("roc_auc") is not None:
        if candidate_metrics.get("roc_auc", 0) < current_metrics.get("roc_auc", 0):
            candidate_better = False
            reasons.append("candidate_roc_auc_lower_than_current")
    return {"candidate_better": candidate_better, "reasons": reasons}


def main() -> None:
    if not TRADE_CSV.exists() or not CANDIDATE_MODEL.exists() or not CANDIDATE_META.exists():
        print("Missing trade dataset or candidate model/meta")
        return

    df = pd.read_csv(TRADE_CSV)
    if df.empty or "result" not in df.columns:
        print("Trade dataset is empty or missing result column")
        return

    df = df.copy()
    df["target"] = (df["result"] == "win").astype(int)

    candidate_meta = json.loads(CANDIDATE_META.read_text(encoding="utf-8"))
    feature_cols = candidate_meta.get("numeric_features", []) + candidate_meta.get("categorical_features", [])
    feature_cols = [c for c in feature_cols if c in df.columns]
    if not feature_cols:
        print("No usable feature columns for evaluation")
        return

    X = df[feature_cols]
    y = df["target"]
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y if len(set(y)) > 1 else None,
    )

    candidate_model = joblib.load(CANDIDATE_MODEL)
    candidate_metrics = evaluate_model(candidate_model, X_test, y_test)

    current_metrics = None
    if CURRENT_MODEL.exists() and CURRENT_META.exists():
        current_model = joblib.load(CURRENT_MODEL)
        current_metrics = evaluate_model(current_model, X_test, y_test)

    comparison = compare_metrics(candidate_metrics, current_metrics)
    promotion_recommended = candidate_metrics.get("accuracy", 0) >= 0.5 and len(df) >= 10 and comparison["candidate_better"]

    evaluation = {
        "ok": True,
        "trade_count": int(len(df)),
        "feature_columns_used": feature_cols,
        "candidate_metrics": candidate_metrics,
        "current_metrics": current_metrics,
        "comparison": comparison,
        "promotion_recommended": promotion_recommended,
    }

    REPORT_PATH.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote evaluation report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
