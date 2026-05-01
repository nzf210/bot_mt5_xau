from app.config import get_settings
from app.services.local_engine_settings_service import update_local_engine_settings

VALID_MODES = {"off", "semi", "full"}
VALID_SCOPES = {"observe_only", "demo_learning", "guarded_live"}

PRESET_GUARDRAILS = {
    "off": {
        "min_confidence": 72,
        "min_risk_reward": 1.7,
        "max_open_positions_per_symbol": 1,
        "cooldown_minutes": 30,
        "max_daily_loss": 100,
        "local_engine": {
            "spread_atr_max_ratio": 0.12,
            "rsi_bullish_threshold": 52.0,
            "rsi_bearish_threshold": 48.0,
            "min_rr_threshold": 1.0,
            "trend_strictness": "strict",
            "trend_mode": "ema_position",
        },
    },
    "semi": {
        "min_confidence": 60,
        "min_risk_reward": 1.2,
        "max_open_positions_per_symbol": 1,
        "cooldown_minutes": 30,
        "max_daily_loss": 30,
        "local_engine": {
            "spread_atr_max_ratio": 0.16,
            "rsi_bullish_threshold": 50.0,
            "rsi_bearish_threshold": 50.0,
            "min_rr_threshold": 0.9,
            "trend_strictness": "moderate",
            "trend_mode": "hybrid",
        },
    },
    "full": {
        "min_confidence": 58,
        "min_risk_reward": 1.1,
        "max_open_positions_per_symbol": 1,
        "cooldown_minutes": 20,
        "max_daily_loss": 25,
        "local_engine": {
            "spread_atr_max_ratio": 0.2,
            "rsi_bullish_threshold": 49.0,
            "rsi_bearish_threshold": 51.0,
            "min_rr_threshold": 0.8,
            "trend_strictness": "loose",
            "trend_mode": "hybrid",
        },
    },
}


def resolve_runtime_guardrails(base_profile: dict) -> dict:
    summary = load_autopilot_summary()
    mode = summary.get("mode", "off")
    preset = summary.get("preset_guardrails", {})
    effective = dict(base_profile)

    if mode in {"semi", "full"}:
        if "min_confidence" in preset:
            effective["min_confidence"] = preset["min_confidence"]
        if "min_risk_reward" in preset:
            effective["min_risk_reward"] = preset["min_risk_reward"]
        if "max_open_positions_per_symbol" in preset:
            effective["max_open_positions_per_symbol"] = preset["max_open_positions_per_symbol"]
        if "cooldown_minutes" in preset:
            effective["cooldown_minutes"] = preset["cooldown_minutes"]

    return {
        "autopilot": summary,
        "profile": effective,
        "local_engine": dict(preset.get("local_engine", {})),
    }


def apply_autopilot_preset_to_local_state() -> dict:
    summary = load_autopilot_summary()
    preset = summary.get("preset_guardrails", {})
    local_engine = preset.get("local_engine", {}) or {}
    if not local_engine:
        return {"ok": False, "reason": "missing_local_engine_preset", "autopilot": summary}

    updated = update_local_engine_settings(
        spread_atr_max_ratio=float(local_engine.get("spread_atr_max_ratio", 0.12)),
        rsi_bullish_threshold=float(local_engine.get("rsi_bullish_threshold", 52.0)),
        rsi_bearish_threshold=float(local_engine.get("rsi_bearish_threshold", 48.0)),
        min_rr_threshold=float(local_engine.get("min_rr_threshold", 1.0)),
        trend_strictness=str(local_engine.get("trend_strictness", "strict")),
        trend_mode=str(local_engine.get("trend_mode", "ema_position")),
    )
    return {"ok": True, "autopilot": summary, "applied_local_engine": updated}


def load_autopilot_summary() -> dict:
    settings = get_settings()
    mode = settings.autopilot_mode.strip().lower()
    scope = settings.autopilot_scope.strip().lower()

    if mode not in VALID_MODES:
        mode = "off"
    if scope not in VALID_SCOPES:
        scope = "demo_learning"

    is_observe_only = scope == "observe_only"
    is_demo_learning = scope == "demo_learning"
    is_guarded_live = scope == "guarded_live"

    return {
        "mode": mode,
        "scope": scope,
        "scheduler_enabled": settings.autopilot_scheduler_enabled,
        "cadence_hours": settings.autopilot_cadence_hours,
        "allow_config_tuning": settings.autopilot_allow_config_tuning,
        "allow_model_promotion": settings.autopilot_allow_model_promotion,
        "require_approval_for_major_changes": settings.autopilot_require_approval_for_major_changes,
        "preset_guardrails": PRESET_GUARDRAILS.get(mode, PRESET_GUARDRAILS["off"]),
        "effective": {
            "collect_data": mode in {"semi", "full"},
            "run_learning_cycle": mode in {"semi", "full"} and settings.autopilot_scheduler_enabled,
            "prepare_recommendations": mode in {"semi", "full"},
            "apply_low_risk_tuning": mode in {"semi", "full"} and settings.autopilot_allow_config_tuning,
            "allow_model_promotion": mode == "full" and settings.autopilot_allow_model_promotion,
            "observe_only": is_observe_only,
            "demo_learning": is_demo_learning,
            "guarded_live_scope": is_guarded_live,
            "live_trading_effectively_allowed": is_guarded_live and settings.allow_live_trading,
        },
        "notes": [
            "Autopilot does not auto-enable live trading.",
            "Scheduler flag is declarative until the host scheduler is configured.",
            "Major changes should remain approval-gated when approval flag is on.",
        ],
    }
