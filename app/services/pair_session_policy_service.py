import json

from app.config import get_settings
from app.services.symbol_service import normalize_symbol


OVERRIDE_KEYS = {
    "min_confidence",
    "min_risk_reward",
    "max_spread_points",
    "cooldown_minutes",
    "max_open_positions_per_symbol",
    "max_trades_per_day",
}


def _load_policy_map() -> dict:
    settings = get_settings()
    raw = settings.symbol_session_policy_json.strip() or "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_pair_session_policy(symbol: str, session: str, base_profile: dict) -> dict:
    settings = get_settings()
    policy_map = _load_policy_map()
    normalized_symbol = normalize_symbol(symbol)
    symbol_policy = policy_map.get(normalized_symbol, {}) if isinstance(policy_map, dict) else {}

    effective_profile = dict(base_profile)
    allowed_sessions = settings.allowed_sessions
    matched_symbol_policy = False
    matched_session_override = False

    if isinstance(symbol_policy, dict) and symbol_policy:
        matched_symbol_policy = True
        custom_allowed = symbol_policy.get("allowed_sessions")
        if isinstance(custom_allowed, list) and custom_allowed:
            allowed_sessions = [str(s).strip() for s in custom_allowed if str(s).strip()]

        session_map = symbol_policy.get("sessions", {})
        session_override = session_map.get(session, {}) if isinstance(session_map, dict) else {}
        if isinstance(session_override, dict) and session_override:
            matched_session_override = True
            for key in OVERRIDE_KEYS:
                if key in session_override:
                    effective_profile[key] = session_override[key]

    return {
        "normalized_symbol": normalized_symbol,
        "allowed_sessions": allowed_sessions,
        "profile": effective_profile,
        "matched_symbol_policy": matched_symbol_policy,
        "matched_session_override": matched_session_override,
    }
