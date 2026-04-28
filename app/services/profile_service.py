from app.config import get_settings


PROFILE_MAP = {
    "dry_run": {
        "allow_live_trading": False,
        "max_trades_per_day": 0,
        "enable_vision": False,
    },
    "demo": {
        "allow_live_trading": False,
        "max_trades_per_day": 3,
        "enable_vision": False,
    },
    "live": {
        "allow_live_trading": True,
        "max_trades_per_day": 2,
        "enable_vision": False,
    },
}


def get_profile_settings(mode: str) -> dict:
    settings = get_settings()
    profile = PROFILE_MAP.get(mode, PROFILE_MAP["dry_run"]).copy()
    profile["cooldown_minutes"] = settings.cooldown_minutes
    profile["min_confidence"] = settings.min_confidence
    profile["min_risk_reward"] = settings.min_risk_reward
    profile["max_spread_points"] = settings.max_spread_points
    profile["max_open_positions_per_symbol"] = settings.max_open_positions_per_symbol
    return profile
