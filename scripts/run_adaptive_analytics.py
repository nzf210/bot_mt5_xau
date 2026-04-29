import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DECISION_CSV = ROOT / "data" / "training" / "decision_dataset.csv"
TRADE_CSV = ROOT / "data" / "training" / "trade_outcome_dataset.csv"
OUTPUT_JSON = ROOT / "data" / "exports" / "adaptive_report.json"


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame([])
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame([])


def safe_group_summary(df: pd.DataFrame, group_col: str, pnl_col: str = "pnl") -> list[dict]:
    if df.empty or group_col not in df.columns or pnl_col not in df.columns:
        return []
    grouped = (
        df.groupby(group_col)
        .agg(count=(group_col, "count"), pnl_total=(pnl_col, "sum"), pnl_avg=(pnl_col, "mean"))
        .sort_values(["pnl_total", "count"], ascending=[False, False])
        .reset_index()
    )
    return grouped.to_dict(orient="records")


def _band_metrics(df: pd.DataFrame, source_col: str, labels: list[str], bins: list[float]) -> dict:
    if df.empty or source_col not in df.columns:
        return {}
    tmp = df.copy()
    tmp[source_col] = pd.to_numeric(tmp[source_col], errors="coerce")
    tmp = tmp.dropna(subset=[source_col])
    tmp["band"] = pd.cut(tmp[source_col], bins=bins, labels=labels, right=False)

    result = {}
    for band, g in tmp.groupby("band"):
        if pd.isna(band):
            continue
        total = int(len(g))
        wins = int((g["result"] == "win").sum()) if "result" in g.columns else 0
        pnl_total = float(g["pnl"].sum()) if "pnl" in g.columns else 0.0
        pnl_avg = float(g["pnl"].mean()) if "pnl" in g.columns and total > 0 else 0.0
        result[str(band)] = {
            "trade_count": total,
            "wins": wins,
            "win_rate": round((wins / total) * 100.0, 2) if total > 0 else 0.0,
            "pnl_total": round(pnl_total, 2),
            "pnl_avg": round(pnl_avg, 2),
        }
    return result


def confidence_analysis(decision_df: pd.DataFrame, trade_df: pd.DataFrame) -> dict:
    labels = ["0-59", "60-69", "70-79", "80-100"]
    bins = [0, 60, 70, 80, 101]

    result = {label: {"decision_count": 0} for label in labels}
    if not decision_df.empty and "confidence" in decision_df.columns:
        d = decision_df.copy()
        d["confidence"] = pd.to_numeric(d["confidence"], errors="coerce")
        d = d.dropna(subset=["confidence"])
        d["confidence_band"] = pd.cut(d["confidence"], bins=bins, labels=labels, right=False)
        counts = d.groupby("confidence_band").size().to_dict()
        for k, v in counts.items():
            if pd.isna(k):
                continue
            result[str(k)]["decision_count"] = int(v)

    if not trade_df.empty and "confidence" in trade_df.columns:
        metrics = _band_metrics(trade_df, "confidence", labels, bins)
        for band, values in metrics.items():
            result.setdefault(band, {}).update(values)

    return result


def rr_analysis(decision_df: pd.DataFrame, trade_df: pd.DataFrame) -> dict:
    labels = ["<1.5", "1.5-1.69", "1.7-1.99", "2.0+"]
    bins = [0, 1.5, 1.7, 2.0, 999]

    result = {label: {"decision_count": 0} for label in labels}
    if not decision_df.empty and "risk_reward" in decision_df.columns:
        d = decision_df.copy()
        d["risk_reward"] = pd.to_numeric(d["risk_reward"], errors="coerce")
        d = d.dropna(subset=["risk_reward"])
        d["rr_band"] = pd.cut(d["risk_reward"], bins=bins, labels=labels, right=False)
        counts = d.groupby("rr_band").size().to_dict()
        for k, v in counts.items():
            if pd.isna(k):
                continue
            result[str(k)]["decision_count"] = int(v)

    if not trade_df.empty and "risk_reward" in trade_df.columns:
        metrics = _band_metrics(trade_df, "risk_reward", labels, bins)
        for band, values in metrics.items():
            result.setdefault(band, {}).update(values)

    return result


def session_pnl_analysis(trade_df: pd.DataFrame) -> list[dict]:
    if trade_df.empty or "session" not in trade_df.columns or "pnl" not in trade_df.columns:
        return []
    grouped = (
        trade_df.groupby("session")
        .agg(trade_count=("session", "count"), pnl_total=("pnl", "sum"), pnl_avg=("pnl", "mean"))
        .sort_values(["pnl_total", "trade_count"], ascending=[False, False])
        .reset_index()
    )
    return grouped.to_dict(orient="records")


def pair_session_analysis(trade_df: pd.DataFrame) -> list[dict]:
    required = {"symbol", "session", "result", "pnl"}
    if trade_df.empty or not required.issubset(set(trade_df.columns)):
        return []

    rows = []
    for (symbol, session), g in trade_df.groupby(["symbol", "session"]):
        total = int(len(g))
        wins = int((g["result"] == "win").sum())
        rows.append({
            "symbol": symbol,
            "session": session,
            "trade_count": total,
            "wins": wins,
            "win_rate": round((wins / total) * 100.0, 2) if total > 0 else 0.0,
            "pnl_total": round(float(g["pnl"].sum()), 2),
            "pnl_avg": round(float(g["pnl"].mean()), 2) if total > 0 else 0.0,
        })

    rows.sort(key=lambda x: (x["pnl_total"], x["win_rate"], x["trade_count"]), reverse=True)
    return rows


def symbol_winrate_analysis(trade_df: pd.DataFrame) -> list[dict]:
    if trade_df.empty or "symbol" not in trade_df.columns or "result" not in trade_df.columns or "pnl" not in trade_df.columns:
        return []
    rows = []
    for symbol, g in trade_df.groupby("symbol"):
        total = len(g)
        wins = int((g["result"] == "win").sum())
        rows.append({
            "symbol": symbol,
            "trade_count": int(total),
            "wins": wins,
            "win_rate": round((wins / total) * 100.0, 2) if total > 0 else 0.0,
            "pnl_total": round(float(g["pnl"].sum()), 2),
            "pnl_avg": round(float(g["pnl"].mean()), 2) if total > 0 else 0.0,
        })
    rows.sort(key=lambda x: (x["pnl_total"], x["win_rate"], x["trade_count"]), reverse=True)
    return rows


def timeframe_winrate_analysis(trade_df: pd.DataFrame) -> list[dict]:
    if trade_df.empty or "timeframe" not in trade_df.columns or "result" not in trade_df.columns or "pnl" not in trade_df.columns:
        return []
    rows = []
    for timeframe, g in trade_df.groupby("timeframe"):
        total = len(g)
        wins = int((g["result"] == "win").sum())
        rows.append({
            "timeframe": timeframe,
            "trade_count": int(total),
            "wins": wins,
            "win_rate": round((wins / total) * 100.0, 2) if total > 0 else 0.0,
            "pnl_total": round(float(g["pnl"].sum()), 2),
            "pnl_avg": round(float(g["pnl"].mean()), 2) if total > 0 else 0.0,
        })
    rows.sort(key=lambda x: (x["pnl_total"], x["win_rate"], x["trade_count"]), reverse=True)
    return rows


def top_filter_reasons(decision_df: pd.DataFrame) -> list[dict]:
    if decision_df.empty or "filter_reason" not in decision_df.columns:
        return []
    vc = decision_df["filter_reason"].fillna("").value_counts().head(10)
    return [{"filter_reason": str(idx), "count": int(val)} for idx, val in vc.items()]


def recommend_confidence_threshold(conf_analysis: dict) -> int | None:
    candidates = []
    mapping = {"60-69": 60, "70-79": 70, "80-100": 80}
    for band, values in conf_analysis.items():
        if band not in mapping:
            continue
        if values.get("trade_count", 0) >= 3 and values.get("pnl_total", 0) > 0:
            candidates.append((mapping[band], values.get("win_rate", 0), values.get("pnl_total", 0)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[1], x[2], x[0]), reverse=True)
    return int(candidates[0][0])


def recommend_rr_threshold(rr_analysis_map: dict) -> float | None:
    mapping = {"1.5-1.69": 1.5, "1.7-1.99": 1.7, "2.0+": 2.0}
    candidates = []
    for band, values in rr_analysis_map.items():
        if band not in mapping:
            continue
        if values.get("trade_count", 0) >= 3 and values.get("pnl_total", 0) > 0:
            candidates.append((mapping[band], values.get("win_rate", 0), values.get("pnl_total", 0)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[1], x[2], x[0]), reverse=True)
    return float(candidates[0][0])


def recommend_disabled_symbols(symbol_rows: list[dict]) -> list[str]:
    disabled = []
    for row in symbol_rows:
        if row["trade_count"] >= 3 and row["pnl_total"] < 0 and row["win_rate"] < 50:
            disabled.append(row["symbol"])
    return disabled


def recommend_allowed_sessions(session_rows: list[dict]) -> list[str]:
    allowed = []
    for row in session_rows:
        if row["trade_count"] >= 2 and row["pnl_total"] > 0:
            allowed.append(row["session"])
    return allowed


def recommend_symbol_session_policy(pair_session_rows: list[dict]) -> dict:
    policy = {}
    for row in pair_session_rows:
        symbol = row.get("symbol")
        session = row.get("session")
        if not symbol or not session:
            continue
        if row.get("trade_count", 0) < 2:
            continue
        if row.get("pnl_total", 0) <= 0:
            continue
        policy.setdefault(symbol, []).append(session)

    for symbol in list(policy.keys()):
        policy[symbol] = sorted(set(policy[symbol]))
    return policy


def build_recommendations(decision_df: pd.DataFrame, trade_df: pd.DataFrame) -> tuple[list[str], dict]:
    recs = []
    symbol_rows = symbol_winrate_analysis(trade_df)
    timeframe_rows = timeframe_winrate_analysis(trade_df)
    session_rows = session_pnl_analysis(trade_df)
    pair_session_rows = pair_session_analysis(trade_df)
    conf = confidence_analysis(decision_df, trade_df)
    rr = rr_analysis(decision_df, trade_df)
    top_filters = top_filter_reasons(decision_df)

    conf_threshold = recommend_confidence_threshold(conf)
    rr_threshold = recommend_rr_threshold(rr)
    disabled_symbols = recommend_disabled_symbols(symbol_rows)
    allowed_sessions = recommend_allowed_sessions(session_rows)
    symbol_session_policy = recommend_symbol_session_policy(pair_session_rows)

    if symbol_rows:
        recs.append(f"Best symbol by pnl: {symbol_rows[0]['symbol']} ({symbol_rows[0]['pnl_total']})")
        if len(symbol_rows) > 1:
            recs.append(f"Worst symbol by pnl: {symbol_rows[-1]['symbol']} ({symbol_rows[-1]['pnl_total']})")
    if timeframe_rows:
        recs.append(f"Best timeframe by pnl: {timeframe_rows[0]['timeframe']} ({timeframe_rows[0]['pnl_total']})")
    if conf_threshold is not None:
        recs.append(f"Recommended MIN_CONFIDENCE: {conf_threshold}")
    if rr_threshold is not None:
        recs.append(f"Recommended MIN_RISK_REWARD: {rr_threshold}")
    if disabled_symbols:
        recs.append(f"Consider disabling weak symbols: {', '.join(disabled_symbols)}")
    if allowed_sessions:
        recs.append(f"Recommended session allowlist: {', '.join(allowed_sessions)}")
    if top_filters:
        recs.append(f"Most frequent filter reason: {top_filters[0]['filter_reason']} ({top_filters[0]['count']}x)")
    if pair_session_rows:
        best_pair_session = pair_session_rows[0]
        recs.append(
            f"Best pair-session by pnl: {best_pair_session['symbol']} @ {best_pair_session['session']} ({best_pair_session['pnl_total']})"
        )

    machine = {
        "recommended_min_confidence": conf_threshold,
        "recommended_min_risk_reward": rr_threshold,
        "recommended_disabled_symbols": disabled_symbols,
        "recommended_allowed_sessions": allowed_sessions,
        "recommended_symbol_session_policy": symbol_session_policy,
    }
    return recs, machine


def enrich_trade_dataset(trade_df: pd.DataFrame, decision_df: pd.DataFrame) -> pd.DataFrame:
    if trade_df.empty or decision_df.empty:
        return trade_df
    if "symbol" not in trade_df.columns or "symbol" not in decision_df.columns:
        return trade_df

    enrich_cols = [c for c in ["symbol", "timeframe", "session", "confidence", "risk_reward"] if c in decision_df.columns]
    if len(enrich_cols) < 2:
        return trade_df

    dedup = decision_df[enrich_cols].drop_duplicates(subset=[c for c in ["symbol", "timeframe"] if c in enrich_cols], keep="last")
    merge_keys = [c for c in ["symbol", "timeframe"] if c in trade_df.columns and c in dedup.columns]
    if not merge_keys:
        return trade_df
    return trade_df.merge(dedup, on=merge_keys, how="left")


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    decision_df = safe_read_csv(DECISION_CSV)
    trade_df = safe_read_csv(TRADE_CSV)
    trade_df = enrich_trade_dataset(trade_df, decision_df)

    symbol_rows = symbol_winrate_analysis(trade_df)
    timeframe_rows = timeframe_winrate_analysis(trade_df)
    session_rows = session_pnl_analysis(trade_df)
    pair_session_rows = pair_session_analysis(trade_df)
    conf = confidence_analysis(decision_df, trade_df)
    rr = rr_analysis(decision_df, trade_df)
    filter_rows = top_filter_reasons(decision_df)
    recommendations_text, recommendations_machine = build_recommendations(decision_df, trade_df)

    report = {
        "best_symbols": symbol_rows[:5],
        "worst_symbols": list(reversed(symbol_rows[-5:] if symbol_rows else [])),
        "best_timeframes": timeframe_rows[:5],
        "session_analysis": session_rows,
        "pair_session_analysis": pair_session_rows,
        "best_pair_sessions": pair_session_rows[:10],
        "worst_pair_sessions": list(reversed(pair_session_rows[-10:] if pair_session_rows else [])),
        "confidence_analysis": conf,
        "risk_reward_analysis": rr,
        "top_filter_reasons": filter_rows,
        "recommended_config_changes": recommendations_text,
        "recommended_config_values": recommendations_machine,
    }

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Wrote adaptive analytics report to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
