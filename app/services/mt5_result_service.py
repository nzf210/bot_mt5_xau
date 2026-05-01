from pydantic import BaseModel
from app.services.result_store import record_trade_result
from app.services.logger_service import log_trade_event


class TradeResultIngest(BaseModel):
    symbol: str
    timeframe: str
    mode: str
    decision_id: str = ""
    decision: str
    position_ticket: str
    entry_price: float
    close_price: float
    stop_loss: float
    take_profit: float
    pnl: float
    result: str
    notes: str = ""
    close_reason: str = ""
    tp_hit: bool = False
    sl_hit: bool = False


def ingest_trade_result(payload: TradeResultIngest) -> dict:
    record_trade_result(
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        mode=payload.mode,
        decision_id=payload.decision_id,
        decision=payload.decision,
        position_ticket=payload.position_ticket,
        entry_price=payload.entry_price,
        close_price=payload.close_price,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        pnl=payload.pnl,
        result=payload.result,
        notes=payload.notes,
        close_reason=payload.close_reason,
        tp_hit=payload.tp_hit,
        sl_hit=payload.sl_hit,
    )
    log_trade_event("trade_result_ingested", payload.model_dump())
    return {
        "ok": True,
        "ingested": True,
        "close_reason": payload.close_reason,
        "tp_hit": payload.tp_hit,
        "sl_hit": payload.sl_hit,
    }
