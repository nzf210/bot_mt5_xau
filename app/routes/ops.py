import json
import shlex
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.kill_switch_service import set_kill_switch
from app.services.llm_review_settings_service import update_llm_review_settings
from app.services.local_engine_settings_service import update_local_engine_settings
from app.services.bootstrap_settings_service import update_bootstrap_settings
from app.services.ops_summary_service import build_ops_summary
from app.services.autopilot_service import load_autopilot_summary, apply_autopilot_preset_to_local_state
from app.services.profile_service import set_active_profile_mode
from app.services.replay_experiments_service import append_replay_experiment, load_replay_baseline, save_replay_baseline
from app.services.replay_lab_service import STATUS_PATH, load_replay_lab_settings, update_replay_lab_settings


templates = Jinja2Templates(directory="app/templates")
router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]


def _run_script(script_rel: str, script_args: list[str] | None = None) -> tuple[bool, str]:
    script_path = ROOT / script_rel
    cmd = [sys.executable, str(script_path)] + (script_args or [])
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or proc.stderr or "").strip().replace("\n", " | ")[:500]
    if not output:
        output = f"exit={proc.returncode} cmd={' '.join(shlex.quote(part) for part in cmd)}"
    return proc.returncode == 0, output


@router.get("/ops/summary")
async def ops_summary() -> dict:
    return build_ops_summary()


@router.get("/ops", response_class=HTMLResponse)
async def ops_dashboard(request: Request) -> HTMLResponse:
    summary = build_ops_summary()
    return templates.TemplateResponse(
        request,
        "ops_dashboard.html",
        {
            "title": "MT5 AI Bot Ops Control Panel",
            "summary": summary,
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
        },
    )


@router.post("/ops/profile")
async def ops_set_profile(mode: str = Form(...)) -> RedirectResponse:
    try:
        set_active_profile_mode(mode)
        return RedirectResponse(url=f"/ops?message=profile_updated:{mode}", status_code=303)
    except ValueError:
        return RedirectResponse(url=f"/ops?error=invalid_profile:{mode}", status_code=303)


@router.post("/ops/kill-switch")
async def ops_set_kill_switch(active: str = Form(...), reason: str = Form("")) -> RedirectResponse:
    normalized = active.strip().lower()
    if normalized not in {"true", "false"}:
        return RedirectResponse(url=f"/ops?error=invalid_kill_switch_value:{active}", status_code=303)
    payload = set_kill_switch(normalized == "true", reason)
    return RedirectResponse(
        url=f"/ops?message=kill_switch_updated:{str(payload.get('active')).lower()}",
        status_code=303,
    )


@router.post("/ops/approval/prepare-config")
async def ops_prepare_candidate_config() -> RedirectResponse:
    autopilot = load_autopilot_summary()
    if autopilot.get("mode") == "off":
        return RedirectResponse(url="/ops?error=approval_prepare_blocked_by_autopilot_off", status_code=303)
    if not autopilot.get("allow_config_tuning"):
        return RedirectResponse(url="/ops?error=approval_prepare_blocked_by_autopilot_tuning_disabled", status_code=303)
    ok1, out1 = _run_script("scripts/generate_config_recommendation.py")
    ok2, out2 = _run_script("scripts/auto_apply_candidate_config.py") if ok1 else (False, "skipped")
    ok3, out3 = _run_script("scripts/compare_config_vs_recommendation.py") if ok2 else (False, "skipped")
    ok4, out4 = _run_script("scripts/build_approval_summary.py") if ok3 else (False, "skipped")
    if ok1 and ok2 and ok3 and ok4:
        return RedirectResponse(url="/ops?message=approval_prepare_config_ok", status_code=303)
    return RedirectResponse(url=f"/ops?error=approval_prepare_config_failed:{out1}|{out2}|{out3}|{out4}", status_code=303)


@router.post("/ops/approval/backup-model")
async def ops_backup_current_model() -> RedirectResponse:
    ok, out = _run_script("scripts/backup_current_model.py")
    if ok:
        return RedirectResponse(url="/ops?message=approval_backup_model_ok", status_code=303)
    return RedirectResponse(url=f"/ops?error=approval_backup_model_failed:{out}", status_code=303)


@router.post("/ops/approval/apply-config")
async def ops_apply_candidate_config(confirm: str = Form("")) -> RedirectResponse:
    summary = build_ops_summary()
    autopilot = summary.get("autopilot", {})
    approval = summary.get("approval", {})
    if confirm.strip().lower() != "apply":
        return RedirectResponse(url="/ops?error=approval_apply_config_requires_confirm_apply", status_code=303)
    if autopilot.get("mode") == "off":
        return RedirectResponse(url="/ops?error=approval_apply_config_blocked_by_autopilot_off", status_code=303)
    if autopilot.get("require_approval_for_major_changes", True) and autopilot.get("mode") != "full":
        return RedirectResponse(url="/ops?error=approval_apply_config_requires_full_autopilot_or_policy_override", status_code=303)
    if approval.get("rollback_recommended"):
        return RedirectResponse(url="/ops?error=approval_apply_config_blocked_by_rollback_signal", status_code=303)
    if not approval.get("candidate_config_exists"):
        return RedirectResponse(url="/ops?error=approval_apply_config_missing_candidate", status_code=303)
    ok, out = _run_script("scripts/approve_candidate_config.py")
    if not ok:
        return RedirectResponse(url=f"/ops?error=approval_apply_config_failed:{out}", status_code=303)
    _run_script("scripts/compare_config_vs_recommendation.py")
    _run_script("scripts/build_approval_summary.py")
    return RedirectResponse(url="/ops?message=approval_apply_config_ok", status_code=303)


@router.post("/ops/approval/rebuild-summary")
async def ops_rebuild_approval_summary() -> RedirectResponse:
    steps = [
        "scripts/compare_config_vs_recommendation.py",
        "scripts/build_approval_summary.py",
    ]
    outputs = []
    for script in steps:
        ok, out = _run_script(script)
        outputs.append(out)
        if not ok:
            return RedirectResponse(url=f"/ops?error=approval_rebuild_summary_failed:{'|'.join(outputs)}", status_code=303)
    return RedirectResponse(url="/ops?message=approval_rebuild_summary_ok", status_code=303)


@router.post("/ops/learning/run-cycle")
async def ops_run_learning_cycle_manual(confirm: str = Form("")) -> RedirectResponse:
    if confirm.strip().lower() != "run":
        return RedirectResponse(url="/ops?error=learning_run_cycle_requires_confirm_run", status_code=303)
    ok, out = _run_script("scripts/run_learning_cycle.py")
    if not ok:
        return RedirectResponse(url=f"/ops?error=learning_run_cycle_failed:{out}", status_code=303)
    _run_script("scripts/build_approval_summary.py")
    return RedirectResponse(url="/ops?message=learning_run_cycle_ok", status_code=303)


@router.post("/ops/replay-lab/settings")
async def ops_update_replay_lab_settings(
    csv_path: str = Form(...),
    symbol: str = Form(...),
    timeframe: str = Form(...),
    higher_timeframe: str = Form(...),
    mode: str = Form("dry_run"),
    lookback_bars: str = Form("10"),
    outcome_horizon_bars: str = Form("12"),
    output_prefix: str = Form("historical_replay"),
    point_size: str = Form("0.01"),
) -> RedirectResponse:
    try:
        update_replay_lab_settings(
            csv_path=csv_path.strip(),
            symbol=symbol.strip(),
            timeframe=timeframe.strip(),
            higher_timeframe=higher_timeframe.strip(),
            mode=mode.strip(),
            lookback_bars=int(lookback_bars),
            outcome_horizon_bars=int(outcome_horizon_bars),
            output_prefix=output_prefix.strip(),
            point_size=float(point_size),
        )
    except Exception as exc:
        return RedirectResponse(url=f"/ops?error=replay_lab_settings_failed:{str(exc)}", status_code=303)
    return RedirectResponse(url="/ops?message=replay_lab_settings_updated", status_code=303)


@router.post("/ops/replay-lab/run")
async def ops_run_replay_lab() -> RedirectResponse:
    settings = load_replay_lab_settings()
    script_path = ROOT / "scripts" / "build_historical_replay_dataset.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--csv", settings["csv_path"],
        "--symbol", settings["symbol"],
        "--timeframe", settings["timeframe"],
        "--higher-timeframe", settings["higher_timeframe"],
        "--mode", settings["mode"],
        "--lookback-bars", str(settings["lookback_bars"]),
        "--outcome-horizon-bars", str(settings["outcome_horizon_bars"]),
        "--output-prefix", settings["output_prefix"],
        "--point-size", str(settings.get("point_size", 0.01)),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode == 0 and stdout:
        STATUS_PATH.write_text(stdout + "\n", encoding="utf-8")
        try:
            append_replay_experiment(json.loads(stdout))
        except json.JSONDecodeError:
            pass
        return RedirectResponse(url="/ops?message=replay_lab_run_ok", status_code=303)
    error_payload = {
        "available": True,
        "ok": False,
        "returncode": proc.returncode,
        "stdout": stdout[-4000:],
        "stderr": stderr[-4000:],
    }
    STATUS_PATH.write_text(json.dumps(error_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    short_error = (stderr or stdout or f"returncode={proc.returncode}").replace("\n", " | ")[:500]
    return RedirectResponse(url=f"/ops?error=replay_lab_run_failed:{short_error}", status_code=303)


@router.post("/ops/replay-lab/save-baseline")
async def ops_save_replay_baseline() -> RedirectResponse:
    status_payload = STATUS_PATH.read_text(encoding="utf-8").strip() if STATUS_PATH.exists() else ""
    if not status_payload:
        return RedirectResponse(url="/ops?error=replay_baseline_missing_status", status_code=303)
    try:
        payload = json.loads(status_payload)
    except json.JSONDecodeError:
        return RedirectResponse(url="/ops?error=replay_baseline_invalid_status", status_code=303)
    save_replay_baseline(payload)
    return RedirectResponse(url="/ops?message=replay_baseline_saved", status_code=303)


@router.post("/ops/bootstrap/settings")
async def ops_update_bootstrap_settings(target_label: str = Form("target_profitable")) -> RedirectResponse:
    try:
        update_bootstrap_settings(target_label=target_label)
    except ValueError as exc:
        return RedirectResponse(url=f"/ops?error={str(exc)}", status_code=303)
    return RedirectResponse(url="/ops?message=bootstrap_settings_updated", status_code=303)


@router.post("/ops/bootstrap/build-candidate")
async def ops_build_bootstrap_candidate() -> RedirectResponse:
    ok, out = _run_script("scripts/build_bootstrap_candidate_dataset.py")
    if not ok:
        return RedirectResponse(url=f"/ops?error=bootstrap_build_failed:{out}", status_code=303)
    return RedirectResponse(url="/ops?message=bootstrap_build_ok", status_code=303)


@router.post("/ops/bootstrap/train-model")
async def ops_train_bootstrap_model() -> RedirectResponse:
    ok, out = _run_script("scripts/train_bootstrap_model.py")
    if not ok:
        return RedirectResponse(url=f"/ops?error=bootstrap_train_failed:{out}", status_code=303)
    return RedirectResponse(url="/ops?message=bootstrap_train_ok", status_code=303)


@router.post("/ops/bootstrap/evaluate-model")
async def ops_evaluate_bootstrap_model() -> RedirectResponse:
    ok, out = _run_script("scripts/evaluate_bootstrap_model.py")
    if not ok:
        return RedirectResponse(url=f"/ops?error=bootstrap_evaluate_failed:{out}", status_code=303)
    return RedirectResponse(url="/ops?message=bootstrap_evaluate_ok", status_code=303)


@router.post("/ops/llm-review/settings")
async def ops_update_llm_review_settings(enabled: str = Form("true"), cadence: str = Form("3h")) -> RedirectResponse:
    normalized = enabled.strip().lower()
    if normalized not in {"true", "false"}:
        return RedirectResponse(url=f"/ops?error=invalid_llm_review_enabled:{enabled}", status_code=303)
    try:
        update_llm_review_settings(enabled=(normalized == "true"), cadence=cadence)
    except ValueError as exc:
        return RedirectResponse(url=f"/ops?error={str(exc)}", status_code=303)
    return RedirectResponse(url="/ops?message=llm_review_settings_updated", status_code=303)


@router.post("/ops/autopilot/apply-preset")
async def ops_apply_autopilot_preset(confirm: str = Form("")) -> RedirectResponse:
    summary = load_autopilot_summary()
    if confirm.strip().lower() != "apply":
        return RedirectResponse(url="/ops?error=autopilot_apply_preset_requires_confirm_apply", status_code=303)
    if summary.get("mode") == "off":
        return RedirectResponse(url="/ops?error=autopilot_apply_preset_blocked_in_off_mode", status_code=303)
    result = apply_autopilot_preset_to_local_state()
    if not result.get("ok"):
        return RedirectResponse(url=f"/ops?error=autopilot_apply_preset_failed:{result.get('reason','unknown')}", status_code=303)
    return RedirectResponse(url="/ops?message=autopilot_apply_preset_ok", status_code=303)


@router.post("/ops/local-engine/settings")
async def ops_update_local_engine_settings(
    spread_atr_max_ratio: str = Form("0.12"),
    rsi_bullish_threshold: str = Form("52"),
    rsi_bearish_threshold: str = Form("48"),
    min_rr_threshold: str = Form("1.0"),
    trend_strictness: str = Form("strict"),
    trend_mode: str = Form("ema_position"),
) -> RedirectResponse:
    try:
        update_local_engine_settings(
            spread_atr_max_ratio=float(spread_atr_max_ratio),
            rsi_bullish_threshold=float(rsi_bullish_threshold),
            rsi_bearish_threshold=float(rsi_bearish_threshold),
            min_rr_threshold=float(min_rr_threshold),
            trend_strictness=trend_strictness.strip(),
            trend_mode=trend_mode.strip(),
        )
    except ValueError as exc:
        return RedirectResponse(url=f"/ops?error={str(exc)}", status_code=303)
    return RedirectResponse(url="/ops?message=local_engine_settings_updated", status_code=303)


@router.post("/ops/llm-review/run-now")
async def ops_run_llm_review_now() -> RedirectResponse:
    ok, out = _run_script("scripts/run_llm_periodic_review.py", ["--force"])
    if not ok:
        return RedirectResponse(url=f"/ops?error=llm_review_run_failed:{out}", status_code=303)
    return RedirectResponse(url="/ops?message=llm_review_run_ok", status_code=303)
