from datetime import datetime, timezone
from app.config import get_settings
from app.models.trade_decision import TradeDecision
from app.schemas import MarketRequest
from app.services.kill_switch_service import get_kill_switch
from app.services.model_service import score_market_with_model
from app.services.news_service import has_external_news_blackout
from app.services.profile_service import get_profile_settings
from app.services.result_store import sum_pnl_for_day
from app.services.state_store import count_trades_today, get_last_passed_signal_ts, is_duplicate_signal, record_signal_event


def _cooldown_active(symbol: str, timeframe: str, cooldown_minutes: int) -> bool:
    last_ts = get_last_passed_signal_ts(symbol, timeframe)
    if not last_ts:
        return False
    try:
        last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
    except ValueError:
        return False
    now_dt = datetime.now(timezone.utc)
    delta_minutes = (now_dt - last_dt).total_seconds() / 60.0
    return delta_minutes < cooldown_minutes


def apply_risk_filter(td: TradeDecision, market: MarketRequest) -> TradeDecision:
    settings = get_settings()
    profile = get_profile_settings(market.mode)
    kill_switch = get_kill_switch()

    if kill_switch.get("active"):
        td.passed_filter = False
        td.filter_reason = f"kill_switch_active:{kill_switch.get('reason','')}"
        return td

    if settings.emergency_stop:
        td.passed_filter = False
        td.filter_reason = "emergency_stop_enabled"
        return td

    if market.news_context and market.news_context.mt5_blackout_active:
        td.passed_filter = False
        td.filter_reason = market.news_context.mt5_reason or "news_blackout_mt5"
        record_signal_event(market.symbol, market.timeframe, td.decision, td.filter_reason, td.passed_filter)
        return td

    if td.decision == "WAIT":
        td.passed_filter = False
        td.filter_reason = td.reason or "wait_decision"
        return td

    news_blocked, news_reason, _event = has_external_news_blackout(market.symbol)
    if news_blocked:
        td.passed_filter = False
        td.filter_reason = news_reason
        record_signal_event(market.symbol, market.timeframe, td.decision, td.filter_reason, td.passed_filter)
        return td

    model_check = score_market_with_model(market)
    if not model_check.get("allow", True):
        td.passed_filter = False
        td.filter_reason = model_check.get("reason", "model_score_blocked")
        record_signal_event(market.symbol, market.timeframe, td.decision, td.filter_reason, td.passed_filter)
        return td

    if market.spread > profile["max_spread_points"]:
        td.passed_filter = False
        td.filter_reason = "spread_too_high"
        return td

    if td.confidence < profile["min_confidence"]:
        td.passed_filter = False
        td.filter_reason = "confidence_too_low"
        return td

    if td.risk_reward < profile["min_risk_reward"]:
        td.passed_filter = False
        td.filter_reason = "risk_reward_too_low"
        return td

    if market.position_context.open_positions >= profile["max_open_positions_per_symbol"]:
        td.passed_filter = False
        td.filter_reason = "max_open_positions_reached"
        return td

    if market.session not in settings.allowed_sessions:
        td.passed_filter = False
        td.filter_reason = "session_not_allowed"
        return td

    if count_trades_today(market.symbol) >= profile["max_trades_per_day"]:
        td.passed_filter = False
        td.filter_reason = "max_trades_per_day_reached"
        record_signal_event(market.symbol, market.timeframe, td.decision, td.filter_reason, td.passed_filter)
        return td

    if is_duplicate_signal(market.symbol, market.timeframe, td.decision):
        td.passed_filter = False
        td.filter_reason = "duplicate_signal"
        record_signal_event(market.symbol, market.timeframe, td.decision, td.filter_reason, td.passed_filter)
        return td

    if _cooldown_active(market.symbol, market.timeframe, profile["cooldown_minutes"]):
        td.passed_filter = False
        td.filter_reason = "cooldown_active"
        record_signal_event(market.symbol, market.timeframe, td.decision, td.filter_reason, td.passed_filter)
        return td

    if sum_pnl_for_day() <= -abs(settings.max_daily_loss):
        td.passed_filter = False
        td.filter_reason = "max_daily_loss_reached"
        record_signal_event(market.symbol, market.timeframe, td.decision, td.filter_reason, td.passed_filter)
        return td

    if market.mode == "live" and not profile["allow_live_trading"]:
        td.passed_filter = False
        td.filter_reason = "live_mode_not_allowed_by_profile"
        record_signal_event(market.symbol, market.timeframe, td.decision, td.filter_reason, td.passed_filter)
        return td

    td.passed_filter = True
    td.filter_reason = "passed"
    record_signal_event(market.symbol, market.timeframe, td.decision, td.filter_reason, td.passed_filter)
    return td
