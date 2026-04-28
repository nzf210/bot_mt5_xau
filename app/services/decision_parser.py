from app.models.trade_decision import TradeDecision
from app.utils.json_utils import extract_first_json_block, safe_json_loads


VALID_DECISIONS = {"BUY", "SELL", "WAIT"}


def build_wait_decision(reason: str, source: str = "fallback") -> TradeDecision:
    return TradeDecision(decision="WAIT", confidence=0, reason=reason, source=source, passed_filter=False, filter_reason=reason)


def parse_trade_decision(raw_text: str) -> TradeDecision:
    json_text = extract_first_json_block(raw_text)
    data = safe_json_loads(json_text)
    if not data:
        return build_wait_decision("invalid_json")
    try:
        td = TradeDecision(**data)
    except Exception:
        return build_wait_decision("schema_validation_failed")
    if td.decision not in VALID_DECISIONS:
        return build_wait_decision("invalid_decision")
    return td


def validate_trade_decision(td: TradeDecision) -> tuple[bool, str]:
    if td.decision == "WAIT":
        return True, "wait_decision"
    if td.entry <= 0 or td.stop_loss <= 0 or td.take_profit <= 0:
        return False, "non_positive_price_fields"
    if td.risk_reward <= 0:
        return False, "invalid_risk_reward"
    if td.decision == "BUY" and not (td.stop_loss < td.entry < td.take_profit):
        return False, "buy_price_relationship_invalid"
    if td.decision == "SELL" and not (td.take_profit < td.entry < td.stop_loss):
        return False, "sell_price_relationship_invalid"
    return True, "ok"
