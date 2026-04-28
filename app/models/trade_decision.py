from pydantic import BaseModel, Field


class TradeDecision(BaseModel):
    decision: str = Field(default="WAIT")
    confidence: int = Field(default=0, ge=0, le=100)
    entry: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0
    reason: str = ""
    warnings: list[str] = Field(default_factory=list)
    source: str = "ai"
    passed_filter: bool = False
    filter_reason: str = ""
