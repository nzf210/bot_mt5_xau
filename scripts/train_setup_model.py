from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
TRADE_CSV = ROOT / "data" / "training" / "trade_outcome_dataset.csv"
CANDIDATES_DIR = ROOT / "models" / "candidates"
REPORTS_DIR = ROOT / "models" / "reports"

NUMERIC_FEATURES = ["confidence", "risk_reward", "spread", "entry_price", "stop_loss", "take_profit", "ema20", "ema50", "rsi14", "macd_main", "macd_signal", "atr14"]
CATEGORICAL_FEATURES = ["symbol", "timeframe", "session", "decision", "mode", "htf_trend", "market_structure", "momentum"]


def main() -> None:
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if not TRADE_CSV.exists():
        print(f"Missing trade dataset: {TRADE_CSV}")
        return

    df = pd.read_csv(TRADE_CSV)
    if df.empty or "result" not in df.columns:
        print("Trade dataset is empty or missing result column")
        return

    df = df.copy()
    df["target"] = (df["result"] == "win").astype(int)

    available_numeric = [c for c in NUMERIC_FEATURES if c in df.columns]
    available_categorical = [c for c in CATEGORICAL_FEATURES if c in df.columns]
    feature_cols = available_numeric + available_categorical
    if not feature_cols:
        print("No usable feature columns found")
        return

    X = df[feature_cols]
    y = df["target"]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                ]),
                available_numeric,
            ),
            (
                "cat",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("encoder", OneHotEncoder(handle_unknown="ignore")),
                ]),
                available_categorical,
            ),
        ]
    )

    model = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000)),
    ])
    model.fit(X, y)

    candidate_model_path = CANDIDATES_DIR / "candidate_model.pkl"
    candidate_meta_path = CANDIDATES_DIR / "candidate_model_meta.json"
    report_path = REPORTS_DIR / "candidate_model_train_report.json"

    joblib.dump(model, candidate_model_path)
    candidate_meta = {
        "model_type": "logistic_regression_v1",
        "numeric_features": available_numeric,
        "categorical_features": available_categorical,
        "trained_on_rows": int(len(df)),
        "target": "win_binary",
    }
    candidate_meta_path.write_text(json.dumps(candidate_meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps({"ok": True, "trained_on_rows": int(len(df)), "candidate_model": str(candidate_model_path), "candidate_meta": str(candidate_meta_path)}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote candidate model to {candidate_model_path}")


if __name__ == "__main__":
    main()
