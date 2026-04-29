from __future__ import annotations

from shutil import which
from typing import Awaitable, Callable

from app.config import get_settings
from app.schemas import MarketRequest
from app.services.gemini_cli_client import analyze_with_gemini_cli
from app.services.gemini_client import analyze_with_gemini
from app.services.openai_cli_client import analyze_with_openai_cli


ProviderHandler = Callable[[MarketRequest], Awaitable[str]]


def _normalize_provider_name(name: str) -> str:
    normalized = name.strip().lower()
    aliases = {
        "cli": "gemini_cli",
        "api": "gemini_api",
        "gemini-cli": "gemini_cli",
        "gemini-api": "gemini_api",
    }
    return aliases.get(normalized, normalized)


def get_provider_registry() -> dict[str, dict]:
    settings = get_settings()
    return {
        "gemini_cli": {
            "name": "gemini_cli",
            "kind": "cli",
            "enabled": settings.gemini_cli_enabled,
            "available": which("gemini") is not None,
            "auth_mode": "local_cli_session",
            "model": settings.gemini_model,
            "handler": analyze_with_gemini_cli,
        },
        "gemini_api": {
            "name": "gemini_api",
            "kind": "api",
            "enabled": settings.gemini_api_enabled,
            "available": bool(settings.gemini_api_key and settings.gemini_api_key != "replace_me"),
            "auth_mode": "api_key",
            "model": settings.gemini_model,
            "handler": analyze_with_gemini,
        },
        "openai_cli": {
            "name": "openai_cli",
            "kind": "cli",
            "enabled": settings.openai_cli_enabled,
            "available": which("codex") is not None,
            "auth_mode": "chatgpt_session",
            "model": "gpt-5.4",
            "handler": analyze_with_openai_cli,
        },
    }


def get_provider_priority() -> list[str]:
    settings = get_settings()
    raw = [p.strip() for p in settings.gemini_provider_priority.split(",") if p.strip()]
    normalized = [_normalize_provider_name(p) for p in raw]
    return normalized or ["gemini_cli", "gemini_api"]


def get_provider_status_summary() -> dict:
    registry = get_provider_registry()
    priority = get_provider_priority()
    providers: list[dict] = []
    for name in priority:
        provider = registry.get(name)
        if not provider:
            providers.append({
                "name": name,
                "enabled": False,
                "available": False,
                "kind": "unknown",
                "auth_mode": "unknown",
                "model": None,
                "status": "unknown_provider",
            })
            continue
        providers.append({
            "name": provider["name"],
            "enabled": provider["enabled"],
            "available": provider["available"],
            "kind": provider["kind"],
            "auth_mode": provider["auth_mode"],
            "model": provider["model"],
            "status": "ready" if provider["enabled"] and provider["available"] else "not_ready",
        })

    return {
        "priority": priority,
        "providers": providers,
        "policy": "cli_first" if priority and registry.get(priority[0], {}).get("kind") == "cli" else "mixed",
    }
