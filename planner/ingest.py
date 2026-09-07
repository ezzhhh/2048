"""Turn a short thesis into a formulated task + stages, using board context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

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

TYPOS = (
    ("талиц", "таблиц"),
    ("талицу", "таблицу"),
    ("таллиц", "таблиц"),
)


def normalize_typos(text: str) -> str:
    out = text
    for bad, good in TYPOS:
        out = out.replace(bad, good)
    return out


STAGE_PACKS = (
    (
        ("таблиц", "талиц", "учёт", "остатк", "упаков"),
        (
            "Какие поля: наличие, расход, остатки — или другие?",
            "Где живёт таблица: Sheets, amo, своя?",
            "Кто обновляет и в какой момент сделки?",
            "Проверить на одной реальной отгрузке",
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
    (
        ("рассыл", "unisender", "письм"),
        (
            "Собрать базу получателей",
            "Собрать текст и шаблон",
            "Прогнать тестовую отправку",
            "Запустить рассылку и проверить доходимость",
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
    blob = normalize_typos(text.lower())
    for hints, project in PROJECT_HINTS:
        if any(hint in blob for hint in hints):
            return project
    if any(word in blob for word in ("таблиц", "упаков", "воронк")):
        return normalize_project(focus) or "ресторис"
    return normalize_project(focus) or "другое"


WEEKDAYS = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "среду": 2,
    "четверг": 3,
    "пятница": 4,
    "пятницу": 4,
    "суббота": 5,
    "субботу": 5,
    "воскресенье": 6,
}


def parse_ru_due(text: str, today: date | None = None) -> date | None:
    today = today or date.today()
    blob = text.lower()
    if "завтра" in blob:
        return today + timedelta(days=1)
    for name, weekday in WEEKDAYS.items():
        if name in blob:
            delta = (weekday - today.weekday()) % 7
            if delta == 0:
                delta = 7
            return today + timedelta(days=delta)
    from planner.engine import parse_due

    return parse_due(text, today)


def formulate_title(raw: str) -> str:
    text = " ".join(normalize_typos(raw.strip()).split())
    if not text:
        return ""
    first, *rest = text.split(None, 1)
    tail = rest[0] if rest else ""
    low = first.lower()
    if low.startswith("реализован"):
        return ("Реализовать " + tail).strip() or "Реализовать"
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
            "Собрать вводные и критерий готово",
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


def ingest_thesis(
    conn,
    raw: str,
    focus: str = "",
    today: date | None = None,
    *,
    title: str | None = None,
    project: str | None = None,
    due: date | None = None,
    note: str | None = None,
) -> IngestResult:
    today = today or date.today()
    title = title or formulate_title(raw)
    project = project or detect_project(
        raw, focus=focus or db.get_setting(conn, "focus")
    )
    reused = _match_existing(conn, title, project)
    note = note or f"из чата: {raw.strip()}"
    task = Task(status="~", title=title, project=project, note=note, due=due)
    scored = score_priority(task, today=today, focus=project)
    stages = suggest_stages(title, project, note)
    due_s = due.isoformat() if due else None
    parent_id = db.insert_task(
        conn,
        title=title,
        project=project,
        priority=scored.code,
        due=due_s,
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
