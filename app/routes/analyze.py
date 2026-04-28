from fastapi import APIRouter, HTTPException
from app.config import get_settings
from app.schemas import AnalyzeResponse, MarketRequest
from app.services.decision_parser import build_wait_decision, parse_trade_decision, validate_trade_decision
from app.services.gemini_client import analyze_with_gemini
from app.services.logger_service import log_ai_decision, log_trade_event
from app.services.risk_filter import apply_risk_filter
from pydantic import BaseModel
from app.services.review_service import build_daily_review, build_symbol_review, build_timeframe_review
from app.services.mt5_result_service import TradeResultIngest, ingest_trade_result
from app.services.kill_switch_service import get_kill_switch, set_kill_switch
from app.services.news_service import cache_news_events
from app.services.profile_service import get_profile_settings
from app.services.vision_client import analyze_with_vision


router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(market: MarketRequest) -> AnalyzeResponse:
    settings = get_settings()
    phase = "A"
    raw_model_text = ""
    try:
        raw_model_text = await (analyze_with_vision(market) if settings.enable_vision and market.chart_image_base64 else analyze_with_gemini(market))
        phase = "D" if settings.enable_vision and market.chart_image_base64 else "A"
    except Exception as exc:
        decision = build_wait_decision(f"gemini_request_failed:{type(exc).__name__}")
        log_ai_decision(market, raw_model_text, decision, phase)
        raise HTTPException(status_code=502, detail=decision.reason)

    decision = parse_trade_decision(raw_model_text)
    valid, reason = validate_trade_decision(decision)
    if not valid:
        decision = build_wait_decision(reason)

    decision = apply_risk_filter(decision, market)
    if market.mode in {"demo", "live"}:
        phase = "C"
    if settings.enable_vision and market.chart_image_base64:
        phase = "D"
    if market.mode == "live" and settings.allow_live_trading and not settings.emergency_stop:
        phase = "E"

    log_ai_decision(market, raw_model_text, decision, phase)
    log_trade_event("decision_emitted", {"symbol": market.symbol, "timeframe": market.timeframe, "mode": market.mode, "decision": decision.model_dump()})
    return AnalyzeResponse(ok=True, phase=phase, decision=decision, raw_model_text=raw_model_text)


class KillSwitchPayload(BaseModel):
    active: bool
    reason: str = ""


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "ok": True,
        "app": settings.app_name,
        "env": settings.app_env,
        "live_allowed": settings.allow_live_trading,
        "emergency_stop": settings.emergency_stop,
        "vision_enabled": settings.enable_vision,
        "kill_switch": get_kill_switch(),
    }


@router.get("/review/daily")
async def daily_review() -> dict:
    return build_daily_review()


@router.post("/trade-result")
async def trade_result(payload: TradeResultIngest) -> dict:
    return ingest_trade_result(payload)


@router.get("/review/symbol/{symbol}")
async def symbol_review(symbol: str) -> dict:
    return build_symbol_review(symbol)


@router.get("/review/timeframe/{timeframe}")
async def timeframe_review(timeframe: str) -> dict:
    return build_timeframe_review(timeframe)


@router.get("/profile/{mode}")
async def profile(mode: str) -> dict:
    return {"ok": True, "mode": mode, "profile": get_profile_settings(mode)}


@router.get("/kill-switch")
async def kill_switch_status() -> dict:
    return {"ok": True, "kill_switch": get_kill_switch()}


@router.post("/kill-switch")
async def kill_switch_set(payload: KillSwitchPayload) -> dict:
    return {"ok": True, "kill_switch": set_kill_switch(payload.active, payload.reason)}


@router.post("/news/cache")
async def news_cache(payload: list[dict]) -> dict:
    inserted = cache_news_events(payload)
    return {"ok": True, "inserted": inserted}
