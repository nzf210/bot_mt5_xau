from pathlib import Path
import json
from collections import Counter
from app.config import get_settings
from app.services.result_store import fetch_trade_results_for_day


def _build_trade_summary(trade_rows, symbol: str | None = None, timeframe: str | None = None) -> dict:
    pnl_total = 0.0
    wins = 0
    losses = 0
    trade_count = 0
    by_result = Counter()
    by_symbol = Counter()
    by_timeframe = Counter()

    for row in trade_rows:
        if symbol and row["symbol"] != symbol:
            continue
        if timeframe and row["timeframe"] != timeframe:
            continue
        trade_count += 1
        pnl_total += float(row["pnl"])
        result = row["result"]
        by_result[result] += 1
        by_symbol[row["symbol"]] += 1
        by_timeframe[row["timeframe"]] += 1
        if result == "win":
            wins += 1
        elif result == "loss":
            losses += 1

    win_rate = (wins / trade_count * 100.0) if trade_count > 0 else 0.0
    return {
        "trade_count": trade_count,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "pnl_total": round(pnl_total, 2),
        "by_result": dict(by_result),
        "by_symbol": dict(by_symbol),
        "by_timeframe": dict(by_timeframe),
    }


def build_daily_review() -> dict:
    settings = get_settings()
    decision_path = Path(settings.decision_log_path)

    counts = Counter()
    filter_reasons = Counter()
    by_symbol = Counter()

    if decision_path.exists():
        with decision_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                decision = (row.get("decision") or {}).get("decision", "UNKNOWN")
                reason = (row.get("decision") or {}).get("filter_reason", "")
                symbol = row.get("symbol", "UNKNOWN")
                counts[decision] += 1
                filter_reasons[reason] += 1
                by_symbol[symbol] += 1

    return {
        "ok": True,
        "summary": "daily_review_ready",
        "decision_counts": dict(counts),
        "top_filter_reasons": dict(filter_reasons.most_common(10)),
        "decision_by_symbol": dict(by_symbol),
        "trade_results": _build_trade_summary(fetch_trade_results_for_day()),
    }


def build_symbol_review(symbol: str) -> dict:
    return {
        "ok": True,
        "symbol": symbol,
        "trade_results": _build_trade_summary(fetch_trade_results_for_day(), symbol=symbol),
    }


def build_timeframe_review(timeframe: str) -> dict:
    return {
        "ok": True,
        "timeframe": timeframe,
        "trade_results": _build_trade_summary(fetch_trade_results_for_day(), timeframe=timeframe),
    }
