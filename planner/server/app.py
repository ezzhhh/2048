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


def _board_url(project: str = "") -> str:
    if project:
        return f"/?project={project}"
    return "/"


def _columns(parents, focus: str):
    by: dict[str, list] = {name: [] for name in PROJECTS}
    for item in parents:
        name = item["row"]["project"] or "другое"
        if name not in by:
            name = "другое"
        by[name].append(item)
    order = list(PROJECTS)
    if focus in order:
        order = [focus] + [name for name in PROJECTS if name != focus]
    columns = []
    for name in order:
        columns.append(
            {
                "project": name,
                "tasks": by[name],
                "count": len(by[name]),
                "focused": name == focus,
            }
        )
    return columns


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
        stored = db.get_setting(_conn(request), "password_hash")
        try:
            ok = auth.check_password(user.strip(), password, stored)
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
        if not db.get_setting(_conn(request), "setup_done"):
            return RedirectResponse("/setup", status_code=303)
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
        if not db.get_setting(_conn(request), "setup_done"):
            return RedirectResponse("/setup", status_code=303)
        rows, engine_board = _board(request)
        open_rows = [row for row in rows if row["status"] != "x"]
        items = _decorate(request, open_rows)
        parents = [item for item in items if not item["row"]["parent_id"]]
        kids: dict[int, list] = {}
        for item in items:
            parent_id = item["row"]["parent_id"]
            if parent_id:
                kids.setdefault(parent_id, []).append(item)
        focus = _focus(request)
        columns = _columns(parents, focus)
        visible = columns
        if project:
            visible = [col for col in columns if col["project"] == project]
        elif any(col["count"] for col in columns):
            visible = [col for col in columns if col["count"] or col["focused"]]
        next_lines = suggest_next_steps(engine_board, focus=focus or None)
        return templates.TemplateResponse(
            request,
            "board.html",
            {
                "columns": visible,
                "all_columns": columns,
                "kids": kids,
                "next_lines": next_lines,
                "projects": PROJECTS,
                "focus": focus,
                "filter": project,
                "open_count": len(parents),
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
        return_project: str = Form(""),
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
        return RedirectResponse(_board_url(return_project), status_code=303)

    @application.post("/tasks/{task_id}/done")
    def done_task(
        request: Request,
        task_id: int,
        decision: str = Form(""),
        outcome: str = Form(""),
        lesson: str = Form(""),
        return_project: str = Form(""),
    ):
        redirect = _guard(request)
        if redirect:
            return redirect
        row = db.get_task(_conn(request), task_id)
        if not row:
            return RedirectResponse(_board_url(return_project), status_code=303)
        db.update_task(_conn(request), task_id, status="x", done_at=db.now_iso())
        db.add_memory(
            _conn(request),
            project=row["project"] or "другое",
            task=row["title"],
            decision=decision.strip() or "закрыто с доски",
            outcome=outcome.strip() or "готово",
            lesson=lesson.strip(),
        )
        return RedirectResponse(_board_url(return_project), status_code=303)

    @application.post("/tasks/{task_id}/start")
    def start_task(request: Request, task_id: int, return_project: str = Form("")):
        redirect = _guard(request)
        if redirect:
            return redirect
        db.update_task(_conn(request), task_id, status="~")
        return RedirectResponse(_board_url(return_project), status_code=303)

    @application.post("/focus")
    def set_focus(
        request: Request,
        focus: str = Form(""),
        return_project: str = Form(""),
    ):
        redirect = _guard(request)
        if redirect:
            return redirect
        db.set_setting(_conn(request), "focus", focus)
        return RedirectResponse(_board_url(return_project), status_code=303)

    def _import_source(kind: str) -> tuple[str, str]:
        root = HERE.parent
        if kind == "example":
            path = root / "fixtures" / "backlog.example.md"
        elif kind == "live":
            path = root / "ПЛАНЕР.md"
        else:
            return "", ""
        if not path.exists():
            return "", ""
        return path.read_text(encoding="utf-8"), path.name

    @application.get("/setup", response_class=HTMLResponse)
    def setup_page(request: Request, error: str = ""):
        redirect = _guard(request)
        if redirect:
            return redirect
        live = (HERE.parent / "ПЛАНЕР.md").exists()
        return templates.TemplateResponse(
            request,
            "setup.html",
            {
                "error": error,
                "has_live": live,
                "projects": PROJECTS,
                "focus": _focus(request),
                "task_count": db.task_count(_conn(request)),
            },
        )

    @application.post("/setup")
    def setup_submit(
        request: Request,
        password: str = Form(""),
        focus: str = Form(""),
        import_from: str = Form("none"),
    ):
        redirect = _guard(request)
        if redirect:
            return redirect
        if password:
            if len(password) < 8:
                return templates.TemplateResponse(
                    request,
                    "setup.html",
                    {
                        "error": "Пароль не короче 8 символов.",
                        "has_live": (HERE.parent / "ПЛАНЕР.md").exists(),
                        "projects": PROJECTS,
                        "focus": focus,
                        "task_count": db.task_count(_conn(request)),
                    },
                    status_code=400,
                )
            db.set_setting(_conn(request), "password_hash", auth.hash_password(password))
        db.set_setting(_conn(request), "focus", focus)
        if import_from in {"example", "live"}:
            text, _name = _import_source(import_from)
            if text:
                db.import_markdown(_conn(request), text)
        db.set_setting(_conn(request), "setup_done", "1")
        db.add_memory(
            _conn(request),
            project="другое",
            task="Первая настройка планера",
            decision=f"импорт={import_from}; фокус={focus or 'нет'}",
            outcome="мастер закрыт",
            lesson="настройка с телефона без git",
        )
        return RedirectResponse("/", status_code=303)

    @application.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request, message: str = "", error: str = ""):
        redirect = _guard(request)
        if redirect:
            return redirect
        return templates.TemplateResponse(
            request,
            "settings.html",
            {
                "message": message,
                "error": error,
                "projects": PROJECTS,
                "focus": _focus(request),
                "has_hash": bool(db.get_setting(_conn(request), "password_hash")),
            },
        )

    @application.post("/settings/password")
    def settings_password(
        request: Request,
        current: str = Form(...),
        new_password: str = Form(...),
    ):
        redirect = _guard(request)
        if redirect:
            return redirect
        stored = db.get_setting(_conn(request), "password_hash")
        if not auth.check_password(auth.env_user(), current, stored):
            return templates.TemplateResponse(
                request,
                "settings.html",
                {
                    "error": "Текущий пароль неверный.",
                    "message": "",
                    "projects": PROJECTS,
                    "focus": _focus(request),
                    "has_hash": bool(stored),
                },
                status_code=401,
            )
        if len(new_password) < 8:
            return templates.TemplateResponse(
                request,
                "settings.html",
                {
                    "error": "Новый пароль не короче 8 символов.",
                    "message": "",
                    "projects": PROJECTS,
                    "focus": _focus(request),
                    "has_hash": bool(stored),
                },
                status_code=400,
            )
        db.set_setting(_conn(request), "password_hash", auth.hash_password(new_password))
        return RedirectResponse("/settings?message=Пароль+обновлён", status_code=303)

    @application.post("/settings/import")
    def settings_import(request: Request, import_from: str = Form(...)):
        redirect = _guard(request)
        if redirect:
            return redirect
        text, name = _import_source(import_from)
        if not text:
            return RedirectResponse("/settings?error=Файл+не+найден", status_code=303)
        n = db.import_markdown(_conn(request), text)
        db.add_memory(
            _conn(request),
            project="другое",
            task=f"Импорт {name}",
            decision=import_from,
            outcome=f"добавлено {n}",
            lesson="",
        )
        return RedirectResponse("/?imported=1", status_code=303)

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
