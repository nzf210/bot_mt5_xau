from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas import Candle, Indicators, MarketRequest, NewsContext, PositionContext, SupportResistance, TrendContext
from app.services.gemini_provider import analyze_with_provider_fallback
from app.services.llm_review_settings_service import llm_review_due, load_llm_review_settings, mark_llm_review_run

EXPORTS = ROOT / "data" / "exports"
OUTPUT = EXPORTS / "llm_periodic_review.json"


def read_json(path: Path, default):
    if not path.exists() or path.stat().st_size == 0:
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _build_review_market(summary_lines: list[str]) -> MarketRequest:
    text = " | ".join(summary_lines)[:500]
    return MarketRequest(
        symbol="REVIEW",
        timeframe="H3",
        higher_timeframe="D1",
        session="Review",
        bid=0.0,
        ask=0.0,
        spread=0.0,
        ohlc=[
            Candle(t="review-1", o=0.0, h=0.0, l=0.0, c=0.0),
            Candle(t="review-2", o=0.0, h=0.0, l=0.0, c=0.0),
            Candle(t="review-3", o=0.0, h=0.0, l=0.0, c=0.0),
        ],
        indicators=Indicators(ema20=0.0, ema50=0.0, rsi14=50.0, macd_main=0.0, macd_signal=0.0, atr14=0.0),
        support_resistance=SupportResistance(support_1=0.0, support_2=0.0, resistance_1=0.0, resistance_2=0.0),
        trend_context=TrendContext(htf_trend="neutral", market_structure=text, momentum="review"),
        position_context=PositionContext(open_positions=0, has_buy_position=False, has_sell_position=False),
        news_context=NewsContext(mt5_news_available=False, mt5_blackout_active=False, mt5_reason=""),
        mode="dry_run",
    )


async def _run_review() -> dict:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    settings = load_llm_review_settings()

    if not llm_review_due(settings):
        payload = {
            "ok": True,
            "skipped": True,
            "reason": "not_due",
            "settings": settings,
        }
        OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return payload

    adaptive = read_json(EXPORTS / "adaptive_report.json", {})
    readiness = read_json(EXPORTS / "dataset_readiness.json", {})
    approval = read_json(EXPORTS / "approval_summary.json", {})

    summary_lines = []
    if readiness:
        summary_lines.append(f"Dataset readiness: {readiness.get('level')}")
    best_pair_sessions = adaptive.get("best_pair_sessions", [])
    if best_pair_sessions:
        top = best_pair_sessions[0]
        summary_lines.append(f"Top pair-session currently: {top.get('symbol')} @ {top.get('session')} pnl={top.get('pnl_total')}")
    approval_notes = approval.get("approval_notes", [])
    if approval_notes:
        summary_lines.append("Approval notes: " + ", ".join(approval_notes[:3]))
    if not summary_lines:
        summary_lines.append("No major review findings yet. Continue collecting runtime data.")

    llm_result = None
    llm_error = None
    try:
        review_market = _build_review_market(summary_lines)
        llm_text, provider_used = await analyze_with_provider_fallback(review_market)
        llm_result = {
            "provider": provider_used,
            "raw_text": llm_text[:4000],
        }
    except Exception as exc:
        llm_error = str(exc)

    payload = {
        "ok": True,
        "skipped": False,
        "settings": settings,
        "summary": summary_lines,
        "llm_result": llm_result,
        "llm_error": llm_error,
        "recommended_actions": [
            "review ops dashboard",
            "inspect approval summary before applying any config changes",
            "continue collecting runtime decisions and trade outcomes",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mark_llm_review_run("ok" if llm_error is None else "error")
    return payload


def main() -> None:
    payload = asyncio.run(_run_review())
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
