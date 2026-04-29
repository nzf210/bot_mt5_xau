from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.kill_switch_service import set_kill_switch
from app.services.ops_summary_service import build_ops_summary
from app.services.profile_service import set_active_profile_mode


templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


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
