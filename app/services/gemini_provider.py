from app.config import get_settings
from app.schemas import MarketRequest
from app.services.gemini_cli_client import analyze_with_gemini_cli
from app.services.gemini_client import analyze_with_gemini
from app.services.logger_service import log_trade_event


async def analyze_with_provider_fallback(market: MarketRequest) -> tuple[str, str]:
    settings = get_settings()
    priority = [p.strip().lower() for p in settings.gemini_provider_priority.split(",") if p.strip()]
    errors: list[str] = []

    for provider in priority:
        if provider == "cli" and settings.gemini_cli_enabled:
            log_trade_event("gemini_cli_attempt", {
                "symbol": market.symbol,
                "timeframe": market.timeframe,
                "mode": market.mode,
            })
            try:
                text = await analyze_with_gemini_cli(market)
                log_trade_event("gemini_provider_selected", {
                    "provider": "cli",
                    "symbol": market.symbol,
                    "timeframe": market.timeframe,
                    "mode": market.mode,
                    "raw_length": len(text),
                })
                return text, "cli"
            except Exception as exc:
                msg = str(exc)
                errors.append(f"cli:{msg}")
                log_trade_event("gemini_cli_failed", {
                    "symbol": market.symbol,
                    "timeframe": market.timeframe,
                    "mode": market.mode,
                    "error": msg,
                })

        if provider == "api" and settings.gemini_api_enabled:
            log_trade_event("gemini_api_attempt", {
                "symbol": market.symbol,
                "timeframe": market.timeframe,
                "mode": market.mode,
            })
            try:
                text = await analyze_with_gemini(market)
                log_trade_event("gemini_provider_selected", {
                    "provider": "api",
                    "symbol": market.symbol,
                    "timeframe": market.timeframe,
                    "mode": market.mode,
                    "raw_length": len(text),
                })
                return text, "api"
            except Exception as exc:
                msg = str(exc)
                errors.append(f"api:{msg}")
                log_trade_event("gemini_api_failed", {
                    "symbol": market.symbol,
                    "timeframe": market.timeframe,
                    "mode": market.mode,
                    "error": msg,
                })

    raise RuntimeError("all_gemini_providers_failed | " + " | ".join(errors))
