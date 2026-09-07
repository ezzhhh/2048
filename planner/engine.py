"""Deterministic core of AGENT.md: parse, score, lint, decompose, next step."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
import re

PROJECTS = ("место", "ресторис", "визасмарт", "мобилог", "личное", "другое")
PROJECT_ALIASES = {
    "restoris": "ресторис",
    "mesto": "место",
    "место топ": "место",
    "visasmart": "визасмарт",
    "visa": "визасмарт",
    "mobilog": "мобилог",
    "personal": "личное",
    "other": "другое",
}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

ACTION_VERBS = (
    "добавить",
    "задеплоить",
    "решить",
    "собрать",
    "настроить",
    "подключить",
    "проверить",
    "зафиксировать",
    "поставить",
    "оценить",
    "включить",
    "закрыть",
    "написать",
    "сделать",
    "выкатить",
    "обновить",
    "удалить",
    "запустить",
    "прогнать",
    "выбрать",
    "разбить",
    "реализовать",
)

EMPTY_VERBS = ("разобраться", "подумать", "заняться", "посмотреть")
DEPLOY_HINTS = ("задеплоить", "выкатить")
FORK_HINTS = (" или ", " vs ", "свой", "n8n")
SYSTEM_HINTS = ("webhook", "воронк", "депло", "шаблон", "таблиц", "salesbot", "письм")

TASK_RE = re.compile(
    r"^(?P<indent>\s*)-\s*\[(?P<status>[ x~X])\]\s+(?P<body>.+?)\s*$"
)
FIELD_RE = re.compile(
    r"(проект|приоритет|срок|часть|заметка)\s*:\s*([^|]+)",
    re.IGNORECASE,
)


@dataclass
class Task:
    status: str
    title: str
    project: str | None = None
    declared_priority: str | None = None
    due: date | None = None
    note: str = ""
    part: str | None = None
    raw: str = ""
    indent: int = 0
    later: bool = False
    blocker: bool = False

    @property
    def open(self) -> bool:
        return self.status in {" ", "~"}

    @property
    def child(self) -> bool:
        return self.indent >= 2


@dataclass
class Score:
    code: str
    score: int
    why: str


@dataclass
class LintIssue:
    level: str
    message: str


@dataclass
class Board:
    tasks: list[Task] = field(default_factory=list)
    raw: str = ""


def normalize_project(value: str | None) -> str | None:
    if not value:
        return None
    key = " ".join(value.strip().lower().split())
    if key in PROJECTS:
        return key
    return PROJECT_ALIASES.get(key, key)


def parse_due(value: str, today: date) -> date | None:
    text = value.strip()
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None
    match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?", text)
    if not match:
        return None
    day, month, year = match.groups()
    year_n = today.year if year is None else int(year)
    if year_n < 100:
        year_n += 2000
    try:
        return date(year_n, int(month), int(day))
    except ValueError:
        return None


def parse_task_line(line: str, today: date | None = None) -> Task | None:
    today = today or date.today()
    match = TASK_RE.match(line.rstrip())
    if not match:
        return None
    body = match.group("body")
    parts = [part.strip() for part in body.split("|")]
    title = parts[0]
    fields: dict[str, str] = {}
    leftovers: list[str] = []
    for part in parts[1:]:
        found = list(FIELD_RE.finditer(part))
        if not found:
            leftovers.append(part)
            continue
        used = 0
        for item in found:
            fields[item.group(1).lower()] = item.group(2).strip()
            used += item.end()
        extra = part[used:].strip(" |")
        if extra:
            leftovers.append(extra)

    note = fields.get("заметка", "")
    if leftovers:
        note = (note + " " + " ".join(leftovers)).strip()

    due_raw = fields.get("срок")
    project = normalize_project(fields.get("проект"))

    status = match.group("status").lower()
    if status == "x":
        status = "x"

    return Task(
        status=status,
        title=title,
        project=project,
        declared_priority=(fields.get("приоритет") or "").upper() or None,
        due=parse_due(due_raw, today) if due_raw else None,
        note=note,
        part=fields.get("часть"),
        raw=line.rstrip(),
        indent=len(match.group("indent")),
        later="позже" in note.lower() or title.lower().endswith("позже"),
        blocker="блокер" in note.lower() or "блокер" in title.lower(),
    )


def parse_board(markdown: str, today: date | None = None) -> Board:
    today = today or date.today()
    tasks = []
    for line in markdown.splitlines():
        task = parse_task_line(line, today)
        if task:
            tasks.append(task)
    return Board(tasks=tasks, raw=markdown)


def _more_urgent(left: str, right: str) -> str:
    return left if PRIORITY_ORDER[left] <= PRIORITY_ORDER[right] else right


def score_priority(
    task: Task,
    today: date | None = None,
    focus: str | None = None,
    quick_win: bool | None = None,
) -> Score:
    today = today or date.today()
    if task.later and task.due is None:
        return Score("P3", 0, "парковка: позже без даты")

    score = 0
    reasons: list[str] = []

    if task.due:
        delta = (task.due - today).days
        if delta < 0:
            score += 3
            reasons.append("просрочено")
        elif delta == 0:
            score += 3
            reasons.append("срок сегодня")
        elif delta <= 3:
            score += 2
            reasons.append("срок ≤3 дней")
        elif task.due.isocalendar()[:2] == today.isocalendar()[:2]:
            score += 1
            reasons.append("срок на этой неделе")

    if task.blocker:
        score += 3
        reasons.append("блокер")

    focus_n = normalize_project(focus) if focus else None
    if focus_n and task.project == focus_n:
        score += 1
        reasons.append("в фокусе")

    title_l = task.title.lower()
    note_l = task.note.lower()
    if quick_win is None:
        quick_win = "в коде уже есть" in note_l or "quick win" in note_l
    if quick_win and score >= 3:
        score += 1
        reasons.append("quick win")

    if task.due is not None and task.due <= today:
        code = "P0"
    elif score >= 6:
        code = "P0"
    elif score >= 3 or task.blocker:
        code = "P1"
    elif score >= 1:
        code = "P2"
    else:
        code = "P2"

    if any(hint in title_l for hint in DEPLOY_HINTS):
        code = _more_urgent(code, "P1")
        if "деплой / выкладка" not in reasons:
            reasons.append("деплой / выкладка")

    declared = task.declared_priority
    if declared in PRIORITY_ORDER:
        code = _more_urgent(code, declared)
        if declared != code and "заявленный приоритет" not in reasons:
            reasons.append(f"заявленный {declared}")
        elif declared == code and f"заявленный {declared}" not in reasons and not reasons:
            reasons.append(f"заявленный {declared}")

    why = "; ".join(reasons) if reasons else "нет жёсткого срока и блокера"
    return Score(code, score, why)


def lint_formulation(task: Task) -> list[LintIssue]:
    issues: list[LintIssue] = []
    first = task.title.split(None, 1)[0].lower() if task.title else ""
    rest = task.title[len(task.title.split(None, 1)[0]) :].strip() if task.title else ""

    if first in EMPTY_VERBS and len(rest.split()) < 3:
        issues.append(
            LintIssue(
                "error",
                "пустой глагол без объекта и критерия готово",
            )
        )
    elif first not in ACTION_VERBS and first not in EMPTY_VERBS:
        issues.append(
            LintIssue("warn", f"строка не начинается с рабочего глагола ({first})")
        )

    if not task.project:
        issues.append(LintIssue("error", "нет поля проект"))
    elif task.project not in PROJECTS:
        issues.append(LintIssue("error", f"неизвестный проект: {task.project}"))

    if task.title.count(" и ") >= 2:
        issues.append(LintIssue("warn", "похоже на несколько результатов в одной строке"))

    return issues


def should_decompose(task: Task) -> bool:
    if task.later and task.due is None:
        return False
    blob = f"{task.title} {task.note}".lower()
    if any(hint in blob for hint in FORK_HINTS):
        return True
    systems = sum(1 for hint in SYSTEM_HINTS if hint in blob)
    if systems >= 2:
        return True
    if blob.startswith("оценить") and "критер" not in blob and "провер" not in blob:
        return True
    return False


def suggest_next_steps(
    board: Board,
    focus: str | None = None,
    today: date | None = None,
) -> list[str]:
    today = today or date.today()
    open_tasks = [task for task in board.tasks if task.open and not task.child]
    if not open_tasks:
        return ["Открытых задач нет."]

    scored = [
        (score_priority(task, today=today, focus=focus), task) for task in open_tasks
    ]
    scored.sort(key=lambda item: (PRIORITY_ORDER[item[0].code], -item[0].score))

    focus_n = normalize_project(focus) if focus else None
    if focus_n:
        focused = [item for item in scored if item[1].project == focus_n]
        if focused:
            scored = focused + [item for item in scored if item not in focused]

    main_score, main = scored[0]
    lines = [f"1. {main_score.code} · {main.title} — {main_score.why}"]

    follow = next(
        (item for item in scored[1:] if item[0].code in {"P0", "P1"}),
        scored[1] if len(scored) > 1 else None,
    )
    if follow:
        lines.append(f"2. {follow[0].code} · {follow[1].title} — {follow[0].why}")

    tails = [task for score, task in scored if "просрочено" in score.why]
    if tails:
        titles = ", ".join(task.title for task in tails[:3])
        lines.append(f"3. Хвосты: {titles}")
    return lines


def format_log_entry(
    project: str,
    task: str,
    decision: str,
    outcome: str,
    lesson: str = "",
    day: date | None = None,
) -> str:
    day = day or date.today()
    lines = [
        f"## {day.isoformat()} · проект: {project} · {task}",
        f"- Решение: {decision}",
        f"- Исход: {outcome}",
    ]
    if lesson:
        lines.append(f"- Урок: {lesson}")
    return "\n".join(lines) + "\n"


def append_task_log(path: Path, entry: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Лог задач и развилок\n\n"
    if not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + entry + "\n", encoding="utf-8")
