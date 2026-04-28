from pydantic import BaseModel
from app.services.result_store import record_trade_result
from app.services.logger_service import log_trade_event


class TradeResultIngest(BaseModel):
    symbol: str
    timeframe: str
    mode: str
    decision: str
    position_ticket: str
    entry_price: float
    close_price: float
    stop_loss: float
    take_profit: float
    pnl: float
    result: str
    notes: str = ""


def ingest_trade_result(payload: TradeResultIngest) -> dict:
    record_trade_result(
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        mode=payload.mode,
        decision=payload.decision,
        position_ticket=payload.position_ticket,
        entry_price=payload.entry_price,
        close_price=payload.close_price,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        pnl=payload.pnl,
        result=payload.result,
        notes=payload.notes,
    )
    log_trade_event("trade_result_ingested", payload.model_dump())
    return {"ok": True, "ingested": True}
