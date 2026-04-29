from app.schemas import MarketRequest
from app.services.logger_service import log_trade_event
from app.services.provider_registry import get_provider_priority, get_provider_registry


async def analyze_with_provider_fallback(market: MarketRequest) -> tuple[str, str]:
    registry = get_provider_registry()
    priority = get_provider_priority()
    errors: list[str] = []

    for provider_name in priority:
        provider = registry.get(provider_name)
        if not provider:
            errors.append(f"{provider_name}:unknown_provider")
            continue
        if not provider.get("enabled"):
            errors.append(f"{provider_name}:disabled")
            continue
        if not provider.get("available"):
            errors.append(f"{provider_name}:not_available")
            continue

        log_trade_event("llm_provider_attempt", {
            "provider": provider_name,
            "symbol": market.symbol,
            "timeframe": market.timeframe,
            "mode": market.mode,
        })
        try:
            handler = provider.get("handler")
            if handler is None:
                raise RuntimeError("missing_handler")
            text = await handler(market)
            log_trade_event("llm_provider_selected", {
                "provider": provider_name,
                "symbol": market.symbol,
                "timeframe": market.timeframe,
                "mode": market.mode,
                "raw_length": len(text),
            })
            return text, provider_name
        except Exception as exc:
            msg = str(exc)
            errors.append(f"{provider_name}:{msg}")
            log_trade_event("llm_provider_failed", {
                "provider": provider_name,
                "symbol": market.symbol,
                "timeframe": market.timeframe,
                "mode": market.mode,
                "error": msg,
            })

    raise RuntimeError("all_llm_providers_failed | " + " | ".join(errors))
