from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "data" / "exports" / "bootstrap_candidate_dataset.csv"
MODEL_DIR = ROOT / "models" / "bootstrap"
MODEL_PATH = MODEL_DIR / "bootstrap_model.pkl"
META_PATH = MODEL_DIR / "bootstrap_model_meta.json"

NUMERIC = [
    "confidence", "risk_reward", "spread", "ema20", "ema50", "rsi14", "macd_main", "macd_signal", "atr14",
    "entry", "stop_loss", "take_profit",
]
CATEGORICAL = ["decision", "session", "timeframe"]


def main() -> None:
    if not INPUT_CSV.exists():
        raise SystemExit("missing bootstrap candidate dataset")
    df = pd.read_csv(INPUT_CSV)
    if df.empty:
        raise SystemExit("bootstrap candidate dataset empty")

    if "time" in df.columns:
        df = df.sort_values("time").reset_index(drop=True)
    split_idx = max(int(len(df) * 0.8), 1)
    train_df = df.iloc[:split_idx].copy()
    valid_df = df.iloc[split_idx:].copy()
    if valid_df.empty:
        valid_df = train_df.copy()

    y = train_df["target_profitable"].astype(int)
    X = train_df[[c for c in NUMERIC + CATEGORICAL if c in train_df.columns]].copy()

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), [c for c in NUMERIC if c in X.columns]),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), [c for c in CATEGORICAL if c in X.columns]),
        ]
    )
    model = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(n_estimators=200, random_state=42, min_samples_leaf=5)),
    ])
    model.fit(X, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    meta = {
        "ok": True,
        "rows": int(len(df)),
        "train_rows": int(len(train_df)),
        "validation_rows": int(len(valid_df)),
        "numeric_features": [c for c in NUMERIC if c in X.columns],
        "categorical_features": [c for c in CATEGORICAL if c in X.columns],
        "target": "target_profitable",
        "model_type": "random_forest_classifier",
        "model_path": str(MODEL_PATH),
    }
    META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
