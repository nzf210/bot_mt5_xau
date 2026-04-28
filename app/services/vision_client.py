from app.schemas import MarketRequest
from app.services.gemini_client import analyze_with_gemini


async def analyze_with_vision(market: MarketRequest) -> str:
    return await analyze_with_gemini(market)
