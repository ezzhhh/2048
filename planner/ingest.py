"""Turn a short thesis into a formulated task + stages, using board context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from planner.engine import (
    ACTION_VERBS,
    EMPTY_VERBS,
    PROJECTS,
    Task,
    normalize_project,
    score_priority,
    should_decompose,
)
from planner.server import db

PROJECT_HINTS = (
    (("ресторис", "restoris", "упаков", "unisender", "воронк", "webhook", "mesto.top"), "ресторис"),
    (("визасмарт", "visasmart", "golden", "виза"), "визасмарт"),
    (("мобилог", "mobilog", "перевоз"), "мобилог"),
    (("место", "mesto"), "место"),
    (("личное", "дом", "семья"), "личное"),
)

STAGE_PACKS = (
    (
        ("таблиц", "учёт", "остатк"),
        (
            "Зафиксировать поля: наличие / расход / остатки",
            "Выбрать носитель таблицы",
            "Назначить кто обновляет и когда",
            "Проверить на одном примере",
        ),
    ),
    (
        ("webhook", "хук"),
        (
            "Решить канал: свой или готовый сервис",
            "Собрать события и поля",
            "Реализовать",
            "Прогнать e2e",
        ),
    ),
    (
        ("воронк", "этап", "отказ"),
        (
            "Зафиксировать справочник / поля",
            "Добавить в воронку",
            "Поставить задачи менеджеру",
            "Проверить на тестовой сделке",
        ),
    ),
)


@dataclass
class IngestResult:
    title: str
    project: str
    priority: str
    why: str
    stages: list[str] = field(default_factory=list)
    parent_id: int = 0
    reused: str = ""


def detect_project(text: str, focus: str = "") -> str:
    blob = text.lower()
    for hints, project in PROJECT_HINTS:
        if any(hint in blob for hint in hints):
            return project
    return normalize_project(focus) or "другое"


def formulate_title(raw: str) -> str:
    text = " ".join(raw.strip().split())
    if not text:
        return ""
    first, *rest = text.split(None, 1)
    tail = rest[0] if rest else ""
    low = first.lower()
    if low in EMPTY_VERBS and len(tail.split()) < 2:
        return f"Сделать {text}"
    if low in ACTION_VERBS or first[:1].isupper():
        return first[:1].upper() + first[1:] + ((" " + tail) if tail else "")
    return f"Сделать {text}"


def suggest_stages(title: str, project: str, note: str = "") -> list[str]:
    blob = f"{title} {note} {project}".lower()
    for hints, stages in STAGE_PACKS:
        if any(hint in blob for hint in hints):
            return list(stages)
    task = Task(status=" ", title=title, project=project, note=note)
    if should_decompose(task) or len(title.split()) <= 3:
        return [
            "Уточнить, как выглядит готово",
            "Сделать основную работу",
            "Проверить результат",
        ]
    return []


def _match_existing(conn, title: str, project: str) -> str:
    words = {w for w in title.lower().split() if len(w) > 3}
    if not words:
        return ""
    for row in db.list_tasks(conn, include_done=False):
        if row["parent_id"]:
            continue
        other = set(str(row["title"]).lower().split())
        if len(words & other) >= 1 and (not project or row["project"] == project):
            return str(row["title"])
    return ""


def ingest_thesis(conn, raw: str, focus: str = "", today: date | None = None) -> IngestResult:
    today = today or date.today()
    title = formulate_title(raw)
    project = detect_project(raw, focus=focus or db.get_setting(conn, "focus"))
    reused = _match_existing(conn, title, project)
    note = f"из чата: {raw.strip()}"
    task = Task(status="~", title=title, project=project, note=note)
    scored = score_priority(task, today=today, focus=focus or None)
    stages = suggest_stages(title, project, note)
    parent_id = db.insert_task(
        conn,
        title=title,
        project=project,
        priority=scored.code,
        due=None,
        note=note,
        part=None,
        parent_id=None,
        later=False,
        blocker=False,
        status="~" if stages else " ",
    )
    for index, stage in enumerate(stages, start=1):
        db.insert_task(
            conn,
            title=stage,
            project=project,
            priority=scored.code,
            due=None,
            note="",
            part=f"{index}/{len(stages)}",
            parent_id=parent_id,
            later=False,
            blocker=False,
            status=" ",
        )
    db.set_setting(conn, "last_task_id", str(parent_id))
    db.set_setting(conn, "last_project", project)
    db.add_memory(
        conn,
        project=project,
        task=title,
        decision=f"тезис: {raw.strip()}",
        outcome=f"{scored.code}; этапов {len(stages)}",
        lesson="tg/чат: короткие тезисы",
    )
    return IngestResult(
        title=title,
        project=project,
        priority=scored.code,
        why=scored.why,
        stages=stages,
        parent_id=parent_id,
        reused=reused,
    )


def format_result(result: IngestResult) -> str:
    lines = [
        f"{result.priority} · {result.title}",
        f"проект: {result.project} · {result.why}",
    ]
    if result.reused:
        lines.append(f"похоже на уже стоящее: {result.reused}")
    if result.stages:
        lines.append("этапы:")
        for index, stage in enumerate(result.stages, start=1):
            lines.append(f"{index}. {stage}")
    return "\n".join(lines)
