from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.config import get_settings
from app.services.kill_switch_service import get_kill_switch
from app.services.profile_service import get_active_profile_mode, get_profile_settings, list_profile_modes
from app.services.provider_registry import get_provider_status_summary
from app.services.result_store import fetch_trade_results_for_day, init_result_store, sum_pnl_for_day
from app.services.review_service import build_daily_review
from app.services.state_store import init_state_store


def _read_recent_decision_context() -> dict:
    settings = get_settings()
    decision_path = Path(settings.decision_log_path)
    if not decision_path.exists():
        return {
            "latest_mode": None,
            "latest_symbol": None,
            "latest_timeframe": None,
            "latest_phase": None,
            "latest_time": None,
            "decision_count": 0,
        }

    latest_row: dict | None = None
    decision_count = 0
    with decision_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            latest_row = row
            decision_count += 1

    if not latest_row:
        return {
            "latest_mode": None,
            "latest_symbol": None,
            "latest_timeframe": None,
            "latest_phase": None,
            "latest_time": None,
            "decision_count": 0,
        }

    return {
        "latest_mode": latest_row.get("mode"),
        "latest_symbol": latest_row.get("symbol"),
        "latest_timeframe": latest_row.get("timeframe"),
        "latest_phase": latest_row.get("phase"),
        "latest_time": latest_row.get("time"),
        "decision_count": decision_count,
    }


def _build_provider_summary() -> dict:
    settings = get_settings()
    provider_summary = get_provider_status_summary()
    return {
        **provider_summary,
        "cli_enabled": settings.gemini_cli_enabled,
        "api_enabled": settings.gemini_api_enabled,
        "default_model": settings.gemini_model,
    }


def _build_guardrail_summary(mode: str) -> dict:
    settings = get_settings()
    profile = get_profile_settings(mode)
    return {
        "mode": mode,
        "profile": profile,
        "emergency_stop": settings.emergency_stop,
        "allow_live_trading": settings.allow_live_trading,
        "allowed_sessions": settings.allowed_sessions,
        "max_daily_loss": settings.max_daily_loss,
        "model_score_threshold": settings.model_score_threshold,
    }


def _build_readiness(review: dict, kill_switch: dict, mode: str) -> dict:
    settings = get_settings()
    reasons: list[str] = []
    level = "ready"

    if kill_switch.get("active"):
        level = "danger"
        reasons.append(f"kill_switch_active:{kill_switch.get('reason', '')}".rstrip(":"))

    if settings.emergency_stop and level != "danger":
        level = "caution"
        reasons.append("emergency_stop_enabled")

    if mode == "live" and not settings.allow_live_trading:
        level = "caution"
        reasons.append("live_mode_not_allowed")

    trade_results = review.get("trade_results", {})
    pnl_total = float(trade_results.get("pnl_total", 0.0))
    if pnl_total <= -abs(settings.max_daily_loss):
        level = "danger"
        reasons.append("max_daily_loss_reached")

    top_filter_reasons = review.get("top_filter_reasons", {})
    dominant_filters = Counter(top_filter_reasons)
    if dominant_filters.get("duplicate_signal", 0) >= 3 and level == "ready":
        level = "caution"
        reasons.append("duplicate_signal_spike")

    if not reasons:
        reasons.append("system_ready")

    return {
        "level": level,
        "reasons": reasons,
    }


def build_ops_summary() -> dict:
    settings = get_settings()
    init_state_store()
    init_result_store()
    review = build_daily_review()
    recent = _read_recent_decision_context()
    mode = get_active_profile_mode()
    kill_switch = get_kill_switch()
    trade_rows = fetch_trade_results_for_day()

    return {
        "ok": True,
        "app": {
            "name": settings.app_name,
            "env": settings.app_env,
            "host": settings.app_host,
            "port": settings.app_port,
            "log_level": settings.log_level,
        },
        "runtime": {
            "vision_enabled": settings.enable_vision,
            "decision_log_path": settings.decision_log_path,
            "event_log_path": settings.event_log_path,
            "trade_results_today": len(trade_rows),
            "pnl_today": round(sum_pnl_for_day(), 2),
        },
        "kill_switch": kill_switch,
        "guardrails": {
            **_build_guardrail_summary(mode),
            "available_modes": list_profile_modes(),
        },
        "provider": _build_provider_summary(),
        "activity": recent,
        "reviews": {
            "daily": review,
        },
        "readiness": _build_readiness(review, kill_switch, mode),
    }
