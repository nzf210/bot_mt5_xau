from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.routes.analyze import router as analyze_router
from app.routes.ops import router as ops_router
from app.services.state_store import init_state_store
from app.services.result_store import init_result_store
from app.services.news_service import init_news_store


settings = get_settings()
app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(analyze_router)
app.include_router(ops_router)


@app.on_event("startup")
async def startup_event() -> None:
    init_state_store()
    init_result_store()
    init_news_store()
