import json
from pathlib import Path
from app.config import get_settings
from app.models.trade_decision import TradeDecision
from app.schemas import MarketRequest
from app.utils.time_utils import utc_now_iso


settings = get_settings()


def _append_jsonl(path: str, payload: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def log_ai_decision(market: MarketRequest, raw_model_text: str, decision: TradeDecision, phase: str) -> None:
    _append_jsonl(settings.decision_log_path, {
        "time": utc_now_iso(),
        "phase": phase,
        "symbol": market.symbol,
        "timeframe": market.timeframe,
        "mode": market.mode,
        "market": market.model_dump(),
        "raw_model_text": raw_model_text,
        "decision": decision.model_dump(),
    })


def log_trade_event(event_type: str, payload: dict) -> None:
    _append_jsonl(settings.event_log_path, {
        "time": utc_now_iso(),
        "event_type": event_type,
        **payload,
    })
