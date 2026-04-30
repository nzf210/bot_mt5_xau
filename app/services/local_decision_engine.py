from __future__ import annotations

from app.models.trade_decision import TradeDecision
from app.schemas import MarketRequest
from app.services.model_service import score_market_with_model


def _append_debug_warning(warnings: list[str], key: str, value: str) -> None:
    warnings.append(f"{key}={value}")


def _rr(entry: float, stop_loss: float, take_profit: float) -> float:
    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


def _build_wait(reason: str, warnings: list[str] | None = None) -> TradeDecision:
    return TradeDecision(
        decision="WAIT",
        confidence=0,
        entry=0.0,
        stop_loss=0.0,
        take_profit=0.0,
        risk_reward=0.0,
        reason=reason,
        warnings=warnings or [],
        source="local",
    )


def generate_local_decision(market: MarketRequest) -> TradeDecision:
    warnings: list[str] = []

    if len(market.ohlc) < 3:
        return _build_wait("Not enough candle history for local analysis", ["Need at least 3 candles"])

    last = market.ohlc[-1]
    close_price = float(last.c)
    ema20 = float(market.indicators.ema20)
    ema50 = float(market.indicators.ema50)
    rsi14 = float(market.indicators.rsi14)
    atr14 = float(market.indicators.atr14)
    macd_main = float(market.indicators.macd_main or 0.0)
    macd_signal = float(market.indicators.macd_signal or 0.0)
    spread = float(market.spread)
    spread_price = abs(float(market.ask) - float(market.bid))
    atr_spread_ratio = (spread_price / atr14) if atr14 > 0 else 0.0

    bullish_trend = close_price > ema20 > ema50 and market.trend_context.htf_trend == "bullish"
    bearish_trend = close_price < ema20 < ema50 and market.trend_context.htf_trend == "bearish"
    bullish_momentum = rsi14 >= 55 and macd_main >= macd_signal
    bearish_momentum = rsi14 <= 45 and macd_main <= macd_signal

    if atr14 <= 0:
        warnings.append("ATR unavailable or invalid")
    if spread <= 0:
        warnings.append("Spread invalid")
    _append_debug_warning(warnings, "spread_points", f"{spread:.2f}")
    _append_debug_warning(warnings, "spread_price", f"{spread_price:.5f}")
    _append_debug_warning(warnings, "atr14", f"{atr14:.5f}")
    _append_debug_warning(warnings, "spread_atr_ratio", f"{atr_spread_ratio:.4f}")
    if atr14 > 0 and atr_spread_ratio > 0.08:
        return _build_wait("Spread too high relative to current volatility", warnings + ["Spread/ATR ratio too high"])

    support_1 = float(market.support_resistance.support_1)
    resistance_1 = float(market.support_resistance.resistance_1)
    support_2 = float(market.support_resistance.support_2)
    resistance_2 = float(market.support_resistance.resistance_2)

    if bullish_trend and bullish_momentum and close_price > support_1:
        entry = float(market.ask)
        stop_loss = min(support_1, close_price - atr14)
        take_profit = max(resistance_1, close_price + (atr14 * 2.0))
        rr = _rr(entry, stop_loss, take_profit)
        if rr < 1.2:
            return _build_wait("Bullish setup exists but reward-to-risk is still too weak", warnings + [f"RR={rr}"])
        confidence = 82 if rr >= 1.7 else 74
        _append_debug_warning(warnings, "bullish_trend", str(bullish_trend).lower())
        _append_debug_warning(warnings, "bullish_momentum", str(bullish_momentum).lower())
        td = TradeDecision(
            decision="BUY",
            confidence=confidence,
            entry=round(entry, 5),
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            risk_reward=rr,
            reason="Bullish local setup from trend, EMA alignment, RSI, MACD, and support context",
            warnings=warnings,
            source="local",
        )
        model_check = score_market_with_model(market, td)
        if model_check.get("model_loaded") and not model_check.get("allow", True):
            return _build_wait("Bullish setup rejected by local model score", warnings + [str(model_check.get("reason"))])
        return td

    if bearish_trend and bearish_momentum and close_price < resistance_1:
        entry = float(market.bid)
        stop_loss = max(resistance_1, close_price + atr14)
        take_profit = min(support_1, close_price - (atr14 * 2.0), support_2 if support_2 > 0 else close_price - (atr14 * 2.0))
        rr = _rr(entry, stop_loss, take_profit)
        if rr < 1.2:
            return _build_wait("Bearish setup exists but reward-to-risk is still too weak", warnings + [f"RR={rr}"])
        confidence = 82 if rr >= 1.7 else 74
        _append_debug_warning(warnings, "bearish_trend", str(bearish_trend).lower())
        _append_debug_warning(warnings, "bearish_momentum", str(bearish_momentum).lower())
        td = TradeDecision(
            decision="SELL",
            confidence=confidence,
            entry=round(entry, 5),
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            risk_reward=rr,
            reason="Bearish local setup from trend, EMA alignment, RSI, MACD, and resistance context",
            warnings=warnings,
            source="local",
        )
        model_check = score_market_with_model(market, td)
        if model_check.get("model_loaded") and not model_check.get("allow", True):
            return _build_wait("Bearish setup rejected by local model score", warnings + [str(model_check.get("reason"))])
        return td

    if close_price >= resistance_2 or close_price <= support_2:
        warnings.append("Price is extended near outer support/resistance")

    _append_debug_warning(warnings, "bullish_trend", str(bullish_trend).lower())
    _append_debug_warning(warnings, "bearish_trend", str(bearish_trend).lower())
    _append_debug_warning(warnings, "bullish_momentum", str(bullish_momentum).lower())
    _append_debug_warning(warnings, "bearish_momentum", str(bearish_momentum).lower())
    return _build_wait(
        "Local setup is weak, conflicting, or incomplete",
        warnings + ["WAIT preferred until trend and momentum align more clearly"],
    )
