"""Private planner web UI. One user, data on this server, no git."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
import os
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from planner.engine import (
    Board,
    PROJECTS,
    Task,
    lint_formulation,
    normalize_project,
    parse_due,
    score_priority,
    should_decompose,
    suggest_next_steps,
)
from planner.server import auth, db

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))


def data_path() -> Path:
    return Path(os.environ.get("PLANER_DATA", HERE.parent / "data" / "planer.sqlite"))


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        auth.env_password()
        auth.env_secret()
        if getattr(application.state, "conn", None) is None:
            application.state.conn = db.connect(data_path())
        yield
        application.state.conn.close()

    application = FastAPI(
        title="Планер",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.conn = db.connect(data_path())
    application.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("PLANER_SECRET", "dev-only-change-me-16"),
        same_site="lax",
        https_only=os.environ.get("PLANER_HTTPS", "") in {"1", "true", "yes"},
        max_age=60 * 60 * 24 * 30,
    )
    application.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
    _register_routes(application)
    return application


def _conn(request: Request):
    return request.app.state.conn


def _guard(request: Request):
    return auth.login_redirect(request)


def _focus(request: Request) -> str:
    return db.get_setting(_conn(request), "focus", "")


def _board(request: Request):
    rows = db.list_tasks(_conn(request), include_done=True)
    tasks = [db.row_to_task(row) for row in rows]
    return rows, Board(tasks=tasks)


def _decorate(request: Request, rows):
    today = date.today()
    focus = _focus(request) or None
    decorated = []
    for row in rows:
        task = db.row_to_task(row)
        scored = score_priority(task, today=today, focus=focus)
        decorated.append(
            {
                "row": row,
                "task": task,
                "score": scored,
                "issues": lint_formulation(task),
                "decompose": should_decompose(task),
            }
        )
    decorated.sort(
        key=lambda item: (item["score"].code, -item["score"].score, item["row"]["id"])
    )
    return decorated


def _register_routes(application: FastAPI) -> None:
    @application.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, error: str = ""):
        if auth.is_logged_in(request):
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(request, "login.html", {"error": error})

    @application.post("/login")
    def login_submit(request: Request, user: str = Form(...), password: str = Form(...)):
        ip = auth.client_ip(request)
        if not auth.login_allowed(ip):
            return templates.TemplateResponse(
                request,
                "login.html",
                {"error": "Слишком много попыток. Подождите 15 минут."},
                status_code=429,
            )
        try:
            ok = auth.check_password(user.strip(), password)
        except RuntimeError:
            ok = False
        if not ok:
            auth.record_failure(ip)
            return templates.TemplateResponse(
                request,
                "login.html",
                {"error": "Неверный логин или пароль."},
                status_code=401,
            )
        request.session["uid"] = auth.env_user()
        return RedirectResponse("/", status_code=303)

    @application.post("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @application.get("/", response_class=HTMLResponse)
    def board(request: Request, project: str = ""):
        redirect = _guard(request)
        if redirect:
            return redirect
        rows, engine_board = _board(request)
        open_rows = [row for row in rows if row["status"] != "x"]
        items = _decorate(request, open_rows)
        if project:
            items = [item for item in items if item["row"]["project"] == project]
        parents = [item for item in items if not item["row"]["parent_id"]]
        kids: dict[int, list] = {}
        for item in items:
            parent_id = item["row"]["parent_id"]
            if parent_id:
                kids.setdefault(parent_id, []).append(item)
        next_lines = suggest_next_steps(engine_board, focus=_focus(request) or None)
        return templates.TemplateResponse(
            request,
            "board.html",
            {
                "items": parents,
                "kids": kids,
                "next_lines": next_lines,
                "projects": PROJECTS,
                "focus": _focus(request),
                "filter": project,
            },
        )

    @application.post("/tasks")
    def add_task(
        request: Request,
        title: str = Form(...),
        project: str = Form(...),
        due: str = Form(""),
        note: str = Form(""),
        blocker: str = Form(""),
        later: str = Form(""),
        parent_id: str = Form(""),
    ):
        redirect = _guard(request)
        if redirect:
            return redirect
        engine_task = Task(
            status=" ",
            title=title.strip(),
            project=normalize_project(project),
            due=parse_due(due, date.today()) if due else None,
            note=note,
            later=bool(later),
            blocker=bool(blocker),
            indent=2 if parent_id else 0,
        )
        scored = score_priority(engine_task, focus=_focus(request) or None)
        db.insert_task(
            _conn(request),
            title=title,
            project=project,
            priority=scored.code,
            due=due or None,
            note=note,
            part=None,
            parent_id=int(parent_id) if parent_id else None,
            later=bool(later),
            blocker=bool(blocker),
            status="~" if parent_id == "" and should_decompose(engine_task) else " ",
        )
        return RedirectResponse("/", status_code=303)

    @application.post("/tasks/{task_id}/done")
    def done_task(
        request: Request,
        task_id: int,
        decision: str = Form(""),
        outcome: str = Form(""),
        lesson: str = Form(""),
    ):
        redirect = _guard(request)
        if redirect:
            return redirect
        row = db.get_task(_conn(request), task_id)
        if not row:
            return RedirectResponse("/", status_code=303)
        db.update_task(_conn(request), task_id, status="x", done_at=db.now_iso())
        db.add_memory(
            _conn(request),
            project=row["project"] or "другое",
            task=row["title"],
            decision=decision.strip() or "закрыто с доски",
            outcome=outcome.strip() or "готово",
            lesson=lesson.strip(),
        )
        return RedirectResponse("/", status_code=303)

    @application.post("/tasks/{task_id}/start")
    def start_task(request: Request, task_id: int):
        redirect = _guard(request)
        if redirect:
            return redirect
        db.update_task(_conn(request), task_id, status="~")
        return RedirectResponse("/", status_code=303)

    @application.post("/focus")
    def set_focus(request: Request, focus: str = Form("")):
        redirect = _guard(request)
        if redirect:
            return redirect
        db.set_setting(_conn(request), "focus", focus)
        return RedirectResponse("/", status_code=303)

    @application.get("/memory", response_class=HTMLResponse)
    def memory_page(request: Request):
        redirect = _guard(request)
        if redirect:
            return redirect
        return templates.TemplateResponse(
            request,
            "memory.html",
            {"entries": db.list_memory(_conn(request))},
        )

    @application.get("/manifest.webmanifest")
    def manifest():
        return Response(
            (HERE / "static" / "manifest.webmanifest").read_text(encoding="utf-8"),
            media_type="application/manifest+json",
        )

    @application.get("/health")
    def health():
        return {"ok": True}


app = create_app()
