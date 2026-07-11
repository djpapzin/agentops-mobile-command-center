from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .config import settings
from .db import init_db, recent_approvals, recent_runs, summary
from .demo import build_safe_to_merge_card, handle_command, review_email_triage


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.db_path)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _ensure_db() -> None:
    init_db(settings.db_path)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    _ensure_db()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "summary": summary(settings.db_path),
            "runs": recent_runs(8, settings.db_path),
            "approvals": recent_approvals(8, settings.db_path),
            "public_url": settings.public_url,
        },
    )


@app.get("/api/health")
def health():
    _ensure_db()
    data = summary(settings.db_path)
    data.update({"status": "ok", "app_name": settings.app_name})
    return data


@app.get("/api/summary")
def api_summary():
    _ensure_db()
    return summary(settings.db_path)


@app.get("/api/runs")
def api_runs():
    _ensure_db()
    return {"runs": recent_runs(25, settings.db_path), "approvals": recent_approvals(25, settings.db_path)}


@app.post("/api/telegram/demo")
def telegram_demo(payload: dict):
    _ensure_db()
    text = payload.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text")
    result = handle_command(text, db_path=settings.db_path)
    return {"reply": result.text, "payload": result.payload}


@app.get("/api/demo/pr-review")
def demo_pr_review():
    _ensure_db()
    return handle_command(f"/review_pr {settings.demo_pr_url}").payload


@app.get("/api/demo/storage")
def demo_storage():
    _ensure_db()
    return handle_command("/storage").payload


@app.get("/api/demo/email-triage")
def demo_email_triage():
    _ensure_db()
    return review_email_triage()


@app.get("/api/demo/live-demo")
def demo_live_demo():
    _ensure_db()
    return handle_command("/live_demo").payload


@app.get("/api/demo/safe-to-merge")
def demo_safe_to_merge():
    _ensure_db()
    return build_safe_to_merge_card()


@app.get("/api/export")
def api_export():
    _ensure_db()
    return JSONResponse(
        {
            "summary": summary(settings.db_path),
            "runs": recent_runs(100, settings.db_path),
            "approvals": recent_approvals(100, settings.db_path),
        }
    )
