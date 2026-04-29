import json
from pathlib import Path

from app.config import get_settings


ACTIVE_PROFILE_PATH = Path("data/active_profile.json")


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


def _enrich_profile(mode: str) -> dict:
    settings = get_settings()
    profile = PROFILE_MAP.get(mode, PROFILE_MAP["dry_run"]).copy()
    profile["cooldown_minutes"] = settings.cooldown_minutes
    profile["min_confidence"] = settings.min_confidence
    profile["min_risk_reward"] = settings.min_risk_reward
    profile["max_spread_points"] = settings.max_spread_points
    profile["max_open_positions_per_symbol"] = settings.max_open_positions_per_symbol
    return profile


def get_active_profile_mode() -> str:
    if not ACTIVE_PROFILE_PATH.exists():
        return "dry_run"
    try:
        payload = json.loads(ACTIVE_PROFILE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "dry_run"
    mode = str(payload.get("mode", "dry_run"))
    return mode if mode in PROFILE_MAP else "dry_run"


def set_active_profile_mode(mode: str) -> dict:
    if mode not in PROFILE_MAP:
        raise ValueError(f"invalid_profile_mode:{mode}")
    ACTIVE_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"mode": mode}
    ACTIVE_PROFILE_PATH.write_text(json.dumps(payload), encoding="utf-8")
    return {"mode": mode, "profile": _enrich_profile(mode)}


def list_profile_modes() -> list[str]:
    return list(PROFILE_MAP.keys())


def get_profile_settings(mode: str) -> dict:
    return _enrich_profile(mode)
