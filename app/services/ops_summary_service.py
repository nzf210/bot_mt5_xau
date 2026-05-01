from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.config import get_settings
from app.services.kill_switch_service import get_kill_switch
from app.services.llm_review_settings_service import load_llm_review_settings
from app.services.local_engine_settings_service import load_local_engine_settings
from app.services.profile_service import get_active_profile_mode, get_profile_settings, list_profile_modes
from app.services.bootstrap_workflow_service import load_bootstrap_workflow_summary
from app.services.autopilot_service import load_autopilot_summary
from app.services.replay_experiments_service import load_recent_replay_experiments, load_replay_baseline
from app.services.replay_lab_service import load_replay_lab_settings, load_replay_lab_status
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


def _load_adaptive_report_summary() -> dict:
    report_path = Path("data/exports/adaptive_report.json")
    if not report_path.exists():
        return {
            "available": False,
            "best_pair_sessions": [],
            "worst_pair_sessions": [],
            "recommended_symbol_session_policy": {},
        }
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "available": False,
            "best_pair_sessions": [],
            "worst_pair_sessions": [],
            "recommended_symbol_session_policy": {},
        }

    cfg = report.get("recommended_config_values", {})
    return {
        "available": True,
        "best_pair_sessions": report.get("best_pair_sessions", []),
        "worst_pair_sessions": report.get("worst_pair_sessions", []),
        "recommended_symbol_session_policy": cfg.get("recommended_symbol_session_policy", {}),
    }


def _load_pair_session_policy_summary() -> dict:
    settings = get_settings()
    raw = settings.symbol_session_policy_json.strip() or "{}"
    try:
        policy = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "configured": False,
            "policy": {},
        }
    if not isinstance(policy, dict):
        return {
            "configured": False,
            "policy": {},
        }
    return {
        "configured": bool(policy),
        "policy": policy,
    }


def _empty_learning_cycle_summary() -> dict:
    return {
        "available": False,
        "ok": None,
        "started_at": None,
        "finished_at": None,
        "readiness_level": None,
        "allow_training": None,
        "promotion_recommended": None,
        "rollback_recommended": None,
        "readiness_report": {},
        "steps": [],
    }


def _load_learning_cycle_summary() -> dict:
    status_path = Path("data/learning/learning_cycle_status.json")
    if not status_path.exists():
        return _empty_learning_cycle_summary()

    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _empty_learning_cycle_summary()

    rollback = status.get("outputs", {}).get("rollback_trigger", {})
    return {
        "available": True,
        "ok": status.get("ok"),
        "started_at": status.get("started_at"),
        "finished_at": status.get("finished_at"),
        "readiness_level": status.get("gates", {}).get("readiness_level"),
        "allow_training": status.get("gates", {}).get("allow_training"),
        "promotion_recommended": status.get("gates", {}).get("promotion_recommended"),
        "rollback_recommended": rollback.get("rollback_recommended"),
        "readiness_report": status.get("outputs", {}).get("dataset_readiness", {}),
        "steps": status.get("steps", []),
    }


def _load_approval_summary() -> dict:
    path = Path("data/exports/approval_summary.json")
    if not path.exists():
        return {
            "available": False,
            "approval_notes": [],
            "config_comparison": {},
            "recommended_symbol_session_policy": {},
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "available": False,
            "approval_notes": [],
            "config_comparison": {},
            "recommended_symbol_session_policy": {},
        }
    payload["available"] = True
    return payload


def _load_llm_review_summary() -> dict:
    settings = load_llm_review_settings()
    path = Path("data/exports/llm_periodic_review.json")
    if not path.exists():
        return {
            "available": False,
            "settings": settings,
            "summary": [],
            "recommended_actions": [],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "available": False,
            "settings": settings,
            "summary": [],
            "recommended_actions": [],
        }
    payload["available"] = True
    payload.setdefault("settings", settings)
    return payload


def build_ops_summary() -> dict:
    settings = get_settings()
    init_state_store()
    init_result_store()
    review = build_daily_review()
    recent = _read_recent_decision_context()
    mode = get_active_profile_mode()
    kill_switch = get_kill_switch()
    trade_rows = fetch_trade_results_for_day()
    adaptive = _load_adaptive_report_summary()
    pair_session_policy = _load_pair_session_policy_summary()
    learning_cycle = _load_learning_cycle_summary()
    approval = _load_approval_summary()
    llm_review = _load_llm_review_summary()
    local_engine_settings = load_local_engine_settings()
    replay_lab_settings = load_replay_lab_settings()
    replay_lab_status = load_replay_lab_status()
    replay_baseline = load_replay_baseline()
    replay_experiments = load_recent_replay_experiments()
    bootstrap_workflow = load_bootstrap_workflow_summary()
    autopilot = load_autopilot_summary()

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
            "adaptive": adaptive,
        },
        "pair_session_policy": pair_session_policy,
        "learning_cycle": learning_cycle,
        "approval": approval,
        "llm_review": llm_review,
        "local_engine": {
            "settings": local_engine_settings,
        },
        "replay_lab": {
            "settings": replay_lab_settings,
            "status": replay_lab_status,
            "baseline": replay_baseline,
            "recent_runs": replay_experiments,
        },
        "bootstrap_workflow": bootstrap_workflow,
        "autopilot": autopilot,
        "readiness": _build_readiness(review, kill_switch, mode),
    }
