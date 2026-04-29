from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DECISION_CSV = ROOT / "data" / "training" / "decision_dataset.csv"
TRADE_CSV = ROOT / "data" / "training" / "trade_outcome_dataset.csv"
MODEL_EVAL_JSON = ROOT / "models" / "reports" / "model_evaluation.json"
OUTPUT_JSON = ROOT / "data" / "exports" / "dataset_readiness.json"


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame([])
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame([])


def unique_count(df: pd.DataFrame, col: str) -> int:
    if df.empty or col not in df.columns:
        return 0
    return int(df[col].dropna().astype(str).nunique())


def count_result(df: pd.DataFrame, label: str) -> int:
    if df.empty or "result" not in df.columns:
        return 0
    return int((df["result"].astype(str).str.lower() == label).sum())


def evaluate_levels(metrics: dict, model_eval: dict) -> tuple[str, dict]:
    decision_rows = metrics["decision_rows"]
    closed_trades = metrics["closed_trades"]
    win_count = metrics["win_count"]
    loss_count = metrics["loss_count"]
    symbol_count = metrics["symbol_count"]
    timeframe_count = metrics["timeframe_count"]
    session_count = metrics["session_count"]

    checks = {
        "analytics_ready": (
            decision_rows >= 30
            and closed_trades >= 10
            and win_count >= 1
            and loss_count >= 1
            and symbol_count >= 1
            and timeframe_count >= 1
            and session_count >= 1
        ),
        "training_ready": (
            decision_rows >= 60
            and closed_trades >= 30
            and win_count >= 10
            and loss_count >= 10
            and timeframe_count >= 2
            and session_count >= 2
            and symbol_count >= 2
        ),
        "promotion_ready": (
            decision_rows >= 100
            and closed_trades >= 50
            and win_count >= 15
            and loss_count >= 15
            and timeframe_count >= 2
            and session_count >= 2
            and symbol_count >= 2
            and (
                not model_eval
                or model_eval.get("promotion_recommended", False)
            )
        ),
    }

    if checks["promotion_ready"]:
        level = "promotion_ready"
    elif checks["training_ready"]:
        level = "training_ready"
    elif checks["analytics_ready"]:
        level = "analytics_ready"
    else:
        level = "insufficient_data"

    return level, checks


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    decision_df = safe_read_csv(DECISION_CSV)
    trade_df = safe_read_csv(TRADE_CSV)
    model_eval = json.loads(MODEL_EVAL_JSON.read_text(encoding="utf-8")) if MODEL_EVAL_JSON.exists() else {}

    metrics = {
        "decision_rows": int(len(decision_df)),
        "closed_trades": int(len(trade_df)),
        "win_count": count_result(trade_df, "win"),
        "loss_count": count_result(trade_df, "loss"),
        "symbol_count": unique_count(trade_df, "symbol"),
        "timeframe_count": unique_count(trade_df, "timeframe"),
        "session_count": unique_count(trade_df, "session"),
    }

    level, checks = evaluate_levels(metrics, model_eval)

    notes = []
    if metrics["decision_rows"] < 30:
        notes.append("Decision dataset still too small for analytics confidence.")
    if metrics["closed_trades"] < 10:
        notes.append("Closed trade sample still too small.")
    if metrics["win_count"] == 0 or metrics["loss_count"] == 0:
        notes.append("Need both win and loss examples before serious learning.")
    if metrics["session_count"] < 2 and metrics["closed_trades"] >= 30:
        notes.append("Training sample may be too narrow by session.")
    if metrics["timeframe_count"] < 2 and metrics["closed_trades"] >= 30:
        notes.append("Training sample may be too narrow by timeframe.")

    payload = {
        "ok": True,
        "level": level,
        "metrics": metrics,
        "checks": checks,
        "model_evaluation_present": bool(model_eval),
        "model_promotion_recommended": bool(model_eval.get("promotion_recommended", False)) if model_eval else False,
        "notes": notes,
    }

    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Wrote dataset readiness report to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
