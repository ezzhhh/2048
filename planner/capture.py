"""Fast Telegram inbox: write first, correct in one word, never steal focus."""

from __future__ import annotations

from datetime import date

from planner.engine import (
    ACTION_VERBS,
    Board,
    normalize_project,
    score_priority,
    suggest_next_steps,
)
from planner.ingest import (
    detect_project,
    format_result,
    formulate_title,
    fuzzy_project,
    ingest_thesis,
    normalize_typos,
    parse_ru_due,
)
from planner.interview import cancel_draft
from planner.server import db
from planner.server.db import row_to_task

WORK_HINTS = (
    "рассыл",
    "таблиц",
    "талиц",
    "упаков",
    "воронк",
    "webhook",
    "хук",
    "доставк",
    "звон",
    "напис",
    "сделать",
    "реализов",
    "запуст",
    "настро",
    "прогна",
    "собрать",
    "добав",
)


def current_focus(conn) -> str:
    return normalize_project(db.get_setting(conn, "focus")) or "ресторис"


def _last_capture_id(conn) -> int | None:
    raw = db.get_setting(conn, "last_capture_id")
    if not raw.isdigit():
        return None
    return int(raw)


def _set_last_capture(conn, task_id: int) -> None:
    db.set_setting(conn, "last_capture_id", str(task_id))
    db.set_setting(conn, "last_task_id", str(task_id))


def _inbox_project(conn) -> str:
    return normalize_project(db.get_setting(conn, "inbox_project")) or ""


def _clear_pending(conn) -> None:
    db.set_setting(conn, "inbox_project", "")
    cancel_draft(conn)


def project_only(text: str) -> str | None:
    blob = normalize_typos(text.lower())
    blob = blob.replace("проект", " ").replace(":", " ")
    blob = " ".join(blob.split())
    if not blob or len(blob.split()) > 2:
        return None
    if any(hint in blob for hint in WORK_HINTS):
        return None
    if any(blob.startswith(verb) or f" {verb} " in f" {blob} " for verb in ACTION_VERBS):
        return None
    return fuzzy_project(blob)


def due_only(text: str, today: date | None = None) -> date | None:
    due = parse_ru_due(text, today=today)
    if due is None:
        return None
    blob = normalize_typos(text.lower())
    if any(hint in blob for hint in WORK_HINTS):
        return None
    if fuzzy_project(blob) and len(blob.split()) > 3:
        return None
    return due


def _rescore(conn, task_id: int) -> str:
    row = db.get_task(conn, task_id)
    if not row:
        return ""
    scored = score_priority(row_to_task(row), focus=current_focus(conn))
    db.update_task(conn, task_id, priority=scored.code)
    return scored.code


def _patch_project(conn, task_id: int, project: str) -> str:
    row = db.get_task(conn, task_id)
    if not row or row["status"] == "x":
        return "нечего уточнять"
    db.update_task(conn, task_id, project=project)
    for child in db.children_of(conn, task_id):
        db.update_task(conn, child["id"], project=project)
    priority = _rescore(conn, task_id)
    title = row["title"]
    focus = current_focus(conn)
    extra = f" · фокус остаётся {focus}" if project != focus else " · в фокусе"
    return f"обновил · {priority} · {title}\nпроект: {project}{extra}"


def _patch_due(conn, task_id: int, due: date) -> str:
    row = db.get_task(conn, task_id)
    if not row or row["status"] == "x":
        return "нечего уточнять"
    db.update_task(conn, task_id, due=due.isoformat())
    priority = _rescore(conn, task_id)
    return f"срок {due.isoformat()} · {priority} · {row['title']}"


def undo_last(conn) -> str:
    task_id = _last_capture_id(conn)
    _clear_pending(conn)
    if not task_id:
        return "нечего отменять"
    row = db.get_task(conn, task_id)
    if not row or row["status"] == "x":
        return "нечего отменять"
    stamp = db.now_iso()
    db.update_task(conn, task_id, status="x", done_at=stamp)
    for child in db.children_of(conn, task_id):
        db.update_task(conn, child["id"], status="x", done_at=stamp)
    db.set_setting(conn, "last_capture_id", "")
    return f"убрал: {row['title']}"


def format_list(conn) -> str:
    focus = current_focus(conn)
    rows = [row for row in db.list_tasks(conn) if row["status"] != "x"]
    board = Board(tasks=[row_to_task(row) for row in db.list_tasks(conn, include_done=True)])
    nxt = suggest_next_steps(board, focus=focus)
    parents = [row for row in rows if not row["parent_id"]]
    in_focus = [row for row in parents if normalize_project(row["project"]) == focus]
    off = [row for row in parents if normalize_project(row["project"]) != focus]
    lines = [f"фокус: {focus}", *nxt]
    if off:
        lines.append("")
        lines.append("вне фокуса:")
        for row in off[:5]:
            lines.append(f"{row['priority'] or '?'} · {row['title']} · {row['project']}")
    elif in_focus:
        extra = in_focus[1:4]
        if extra:
            lines.append("")
            for row in extra:
                lines.append(f"{row['priority'] or '?'} · {row['title']}")
    return "\n".join(lines).strip() or "Открытых задач нет."


def _capture(conn, raw: str) -> str:
    focus = current_focus(conn)
    pending = _inbox_project(conn)
    project = detect_project(raw, focus="")
    if project == "другое" and pending in {
        "место",
        "ресторис",
        "визасмарт",
        "мобилог",
        "личное",
    }:
        project = pending
    db.set_setting(conn, "inbox_project", "")
    cancel_draft(conn)
    due = parse_ru_due(raw)
    result = ingest_thesis(
        conn,
        raw,
        focus=focus,
        title=formulate_title(raw),
        project=project,
        due=due,
        note=f"из чата: {raw.strip()}",
    )
    _set_last_capture(conn, result.parent_id)
    return format_result(result, focus=focus)


def handle_message(conn, text: str) -> str:
    raw = text.strip()
    if raw.startswith("+"):
        raw = raw[1:].strip()
    low = raw.lower()
    if not raw:
        return "напиши задачу одним сообщением"
    if low in {"список", "/список", "/list", "list"}:
        return format_list(conn)
    if low.startswith("фокус"):
        rest = raw.split(None, 1)[1] if " " in raw else ""
        rest = rest.replace(":", " ").strip()
        project = fuzzy_project(rest) or normalize_project(rest) or rest
        db.set_setting(conn, "focus", project)
        return f"фокус: {project or 'все'}"
    if low.startswith("готово"):
        needle = raw.split(None, 1)[1].lower() if " " in raw else ""
        last_id = _last_capture_id(conn)
        if not needle and last_id:
            row = db.get_task(conn, last_id)
            if row and row["status"] != "x":
                db.update_task(conn, last_id, status="x", done_at=db.now_iso())
                for child in db.children_of(conn, last_id):
                    db.update_task(conn, child["id"], status="x", done_at=db.now_iso())
                return f"готово: {row['title']}"
        for row in db.list_tasks(conn):
            if needle and needle not in str(row["title"]).lower():
                continue
            db.update_task(conn, row["id"], status="x", done_at=db.now_iso())
            db.add_memory(
                conn,
                project=row["project"] or "другое",
                task=row["title"],
                decision="готово из telegram",
                outcome="закрыто",
            )
            return f"готово: {row['title']}"
        return "не нашёл задачу"
    if low in {"отмена", "/отмена"}:
        return undo_last(conn)
    if low in {"стоп", "/стоп"}:
        _clear_pending(conn)
        return "ок, жду следующую задачу. фокус не трогал"
    if low.startswith("срок"):
        rest = raw.split(None, 1)[1] if " " in raw else ""
        due = parse_ru_due(rest or raw)
        last_id = _last_capture_id(conn)
        if due and last_id:
            return _patch_due(conn, last_id, due)
        return "напиши срок: завтра / до конца недели / дата"

    named = project_only(raw)
    if named:
        last_id = _last_capture_id(conn)
        last = db.get_task(conn, last_id) if last_id else None
        if last and last["status"] != "x" and (last["project"] or "") in {"", "другое"}:
            return _patch_project(conn, last_id, named)
        db.set_setting(conn, "inbox_project", named)
        focus = current_focus(conn)
        extra = f"фокус остаётся {focus}" if named != focus else f"фокус: {focus}"
        return f"ок, следующую запишу в {named}. {extra}"

    due = due_only(raw)
    if due:
        last_id = _last_capture_id(conn)
        if last_id:
            return _patch_due(conn, last_id, due)
        return "сначала кинь задачу, потом срок"

    return _capture(conn, raw)
