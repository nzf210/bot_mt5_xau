from app.schemas import MarketRequest


DECISION_SCHEMA = {
    "decision": "BUY|SELL|WAIT",
    "confidence": 0,
    "entry": 0,
    "stop_loss": 0,
    "take_profit": 0,
    "risk_reward": 0,
    "reason": "",
    "warnings": [],
}


def build_prompt(market: MarketRequest, enable_vision: bool = False) -> str:
    vision_note = "You may also use the provided chart image for context. " if enable_vision and market.chart_image_base64 else ""
    return (
        "You are a disciplined forex trading assistant. "
        + vision_note
        + "Analyze the structured market data and return ONLY valid JSON. "
        + "Choose one decision: BUY, SELL, or WAIT. Prefer WAIT if setup is weak, conflicting, risky, or unclear. "
        + "Use trend, momentum, volatility, support/resistance, spread, and higher timeframe context. "
        + "Do not return markdown or explanation outside JSON. "
        + f"Return exactly this schema: {DECISION_SCHEMA}"
    )
