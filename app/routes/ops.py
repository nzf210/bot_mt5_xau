import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.kill_switch_service import set_kill_switch
from app.services.llm_review_settings_service import update_llm_review_settings
from app.services.ops_summary_service import build_ops_summary
from app.services.profile_service import set_active_profile_mode


templates = Jinja2Templates(directory="app/templates")
router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]


def _run_script(script_rel: str) -> tuple[bool, str]:
    script_path = ROOT / script_rel
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or proc.stderr or "").strip().replace("\n", " | ")[:300]
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
    approval = summary.get("approval", {})
    if confirm.strip().lower() != "apply":
        return RedirectResponse(url="/ops?error=approval_apply_config_requires_confirm_apply", status_code=303)
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


@router.post("/ops/llm-review/run-now")
async def ops_run_llm_review_now() -> RedirectResponse:
    ok, out = _run_script("scripts/run_llm_periodic_review.py --force")
    if not ok:
        return RedirectResponse(url=f"/ops?error=llm_review_run_failed:{out}", status_code=303)
    return RedirectResponse(url="/ops?message=llm_review_run_ok", status_code=303)
