from typing import Literal
from pydantic import BaseModel, Field
from app.models.trade_decision import TradeDecision


class Candle(BaseModel):
    t: str
    o: float
    h: float
    l: float
    c: float


class Indicators(BaseModel):
    ema20: float
    ema50: float
    rsi14: float
    macd_main: float | None = None
    macd_signal: float | None = None
    atr14: float


class SupportResistance(BaseModel):
    support_1: float
    support_2: float
    resistance_1: float
    resistance_2: float


class TrendContext(BaseModel):
    htf_trend: Literal["bullish", "bearish", "neutral"]
    market_structure: str
    momentum: str


class PositionContext(BaseModel):
    open_positions: int = 0
    has_buy_position: bool = False
    has_sell_position: bool = False


class NewsContext(BaseModel):
    mt5_news_available: bool = False
    mt5_blackout_active: bool = False
    mt5_reason: str = ""


class MarketRequest(BaseModel):
    symbol: str
    timeframe: str
    higher_timeframe: str
    session: str
    bid: float
    ask: float
    spread: float
    ohlc: list[Candle] = Field(min_length=3)
    indicators: Indicators
    support_resistance: SupportResistance
    trend_context: TrendContext
    position_context: PositionContext
    news_context: NewsContext | None = None
    mode: Literal["dry_run", "demo", "live"] = "dry_run"
    chart_image_base64: str | None = None
    chart_image_mime: str | None = None


class AnalyzeResponse(BaseModel):
    ok: bool = True
    phase: str
    decision: TradeDecision
    raw_model_text: str = ""
