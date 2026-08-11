import hmac
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db
from .ai_service import analyze_menu
from .image_service import generate_image
from .scraper import fetch_weekly_menu
from .teams import send_today_card
from .utils import korean_date, menu_hash

logger = logging.getLogger("lunch.web")
BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_app):
    try:
        db.init_schema()
    except Exception as exc:
        logger.warning("스키마 초기화 건너뜀(%s)", exc)
    yield


app = FastAPI(title="AI 점심 큐레이터", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["comma"] = lambda n: f"{n:,}" if isinstance(n, (int, float)) else (n or "-")
templates.env.filters["kdate"] = lambda d: korean_date(d) if d else ""


@app.get("/", response_class=HTMLResponse)
def page_today(request: Request):
    return templates.TemplateResponse(request, "index.html", {"menu": _safe(db.get_today), "active": "today"})


@app.get("/history", response_class=HTMLResponse)
def page_history(request: Request):
    days = _safe(lambda: db.get_history(30)) or []
    return templates.TemplateResponse(request, "history.html", {"days": days, "active": "history"})


@app.get("/stats", response_class=HTMLResponse)
def page_stats(request: Request):
    stats = _safe(db.get_stats) or {"total_menus": 0, "cached_images": 0, "top_dishes": []}
    return templates.TemplateResponse(request, "stats.html", {"stats": stats, "active": "stats"})


@app.get("/api/today")
def api_today():
    return _safe(db.get_today)


@app.get("/api/history")
def api_history():
    return _safe(lambda: db.get_history(30)) or []


@app.get("/api/stats")
def api_stats():
    return _safe(db.get_stats) or {}


def _check_token(authorization):
    expected = os.getenv("COLLECT_TOKEN", "")
    provided = (authorization or "").removeprefix("Bearer ").strip()
    if not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid or missing token")


@app.post("/api/collect-weekly", status_code=202)
def collect_weekly(background_tasks: BackgroundTasks, authorization: str = Header(default=None)):
    _check_token(authorization)
    background_tasks.add_task(_run_weekly_collect)  # 무거운 작업은 백그라운드로, 즉시 202
    return {"status": "accepted", "message": "주간 수집을 시작했습니다."}


@app.post("/api/send-today")
def send_today(authorization: str = Header(default=None)):
    _check_token(authorization)
    menu = db.get_today()
    if not menu:
        return {"status": "no_menu", "message": "오늘 등록된 메뉴가 없습니다."}
    ok = send_today_card(menu, os.getenv("APP_BASE_URL", "http://localhost:8000"))
    return {"status": "sent" if ok else "failed"}


@app.get("/health")
def health():
    try:
        db.ping()
        return {"status": "ok"}
    except Exception:
        return JSONResponse({"status": "degraded"}, status_code=503)


def _safe(fn):
    try:
        return fn()
    except Exception as exc:
        logger.warning("DB 조회 실패(%s)", exc)
        return None


def _run_weekly_collect():
    week = fetch_weekly_menu(os.getenv("MENU_SOURCE_URL"))
    for day in week:
        menus = day["menus"]
        digest = menu_hash(menus)
        analysis = analyze_menu(menus)
        image_url = generate_image(menus, digest, get_cached=db.get_cached_image, save_cached=db.save_cached_image)
        db.upsert_menu(day["date"], digest, menus, analysis, image_url)
    logger.info("주간 수집 완료. %d일치", len(week))
