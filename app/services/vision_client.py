from app.schemas import MarketRequest
from app.services.gemini_client import analyze_with_gemini
from app.services.logger_service import log_trade_event


async def analyze_with_vision(market: MarketRequest) -> str:
    log_trade_event("gemini_vision_attempt", {
        "symbol": market.symbol,
        "timeframe": market.timeframe,
        "mode": market.mode,
    })
    return await analyze_with_gemini(market)
