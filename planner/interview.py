"""Ask at most 3 leading questions, then form a staged task."""

from __future__ import annotations

import json
from pathlib import Path

from planner.engine import PROJECTS, normalize_project
from planner.ingest import (
    detect_project,
    formulate_title,
    fuzzy_project,
    ingest_thesis,
    normalize_typos,
    parse_ru_due,
)
from planner.server import db

CONTEXT_PATH = Path(__file__).resolve().parent / "CONTEXT.md"


def load_context() -> str:
    if CONTEXT_PATH.exists():
        return CONTEXT_PATH.read_text(encoding="utf-8")
    return ""


def questions_for(raw: str) -> list[str]:
    blob = normalize_typos(raw.lower())
    ctx = load_context().lower()
    if any(w in blob for w in ("таблиц", "упаков")) or (
        "реализов" in blob and "упаков" in ctx
    ):
        return [
            "Это таблица учёта упаковки Restoris (наличие / расход / остатки)?",
            "Где вести: Google Sheets или иначе?",
            "Кто обновляет и на каком этапе (например Доставка)?",
        ]
    if any(w in blob for w in ("webhook", "хук", "доставк")):
        return [
            "Это webhook «Доставка» после Отказа?",
            "Свой контур или n8n Railway?",
        ]
    project = fuzzy_project(raw)
    if "рассыл" in blob and project == "визасмарт":
        return [
            "База получателей уже есть?",
            "Срок? Если да — дата или «до конца недели».",
        ]
    if "рассыл" in blob:
        return [
            "Это VisaSmart?",
            "Срок? Если да — дата.",
        ]
    if project in PROJECTS:
        return [
            "Какой один проверяемый результат будет «готово»?",
            "Срок есть? Если да — дата.",
        ]
    return [
        "Проект: restoris, визасмарт или мобилог?",
        "Какой один проверяемый результат будет «готово»?",
        "Срок есть? Если да — дата.",
    ]


def active_draft(conn) -> dict | None:
    row = conn.execute("SELECT * FROM drafts WHERE id = 1").fetchone()
    if not row or row["status"] != "ask":
        return None
    return {
        "raw": row["raw"],
        "answers": json.loads(row["answers"] or "[]"),
        "questions": json.loads(row["questions"] or "[]"),
        "step": int(row["step"]),
    }


def start_draft(conn, raw: str) -> str:
    questions = questions_for(raw)
    conn.execute(
        """
        INSERT INTO drafts(id, raw, answers, step, questions, status)
        VALUES(1, ?, '[]', 0, ?, 'ask')
        ON CONFLICT(id) DO UPDATE SET raw=excluded.raw, answers='[]', step=0,
            questions=excluded.questions, status='ask'
        """,
        (raw, json.dumps(questions, ensure_ascii=False)),
    )
    conn.commit()
    return questions[0]


def add_answer(conn, text: str):
    draft = active_draft(conn)
    if not draft:
        return None
    draft["answers"].append(text.strip())
    draft["step"] += 1
    conn.execute(
        "UPDATE drafts SET answers = ?, step = ? WHERE id = 1",
        (json.dumps(draft["answers"], ensure_ascii=False), draft["step"]),
    )
    conn.commit()
    return draft


def _title_source(raw: str, qa: list[tuple[str, str]]) -> str:
    # Keep the original thesis when it already names the work.
    # Do not replace «рассылка визмарт» with the «готово» answer.
    words = raw.split()
    only_project = bool(fuzzy_project(raw)) and len(words) <= 1
    if only_project:
        for question, answer in qa:
            if "готово" in question.lower() or "результат" in question.lower():
                return answer
    return raw


def finish_draft(conn, draft: dict):
    qa = list(zip(draft["questions"], draft["answers"]))
    note = " | ".join(f"{q} → {a}" for q, a in qa)
    # Never scan the questions: they list every project name (restoris, …).
    answers_blob = " ".join(answer for _q, answer in qa)
    project = None
    for _q, answer in qa:
        named = fuzzy_project(answer)
        if named:
            project = named
            break
    if project is None:
        project = fuzzy_project(draft["raw"]) or fuzzy_project(answers_blob)
    if project is None:
        project = detect_project(f"{draft['raw']} {answers_blob}", focus="")
    title = formulate_title(_title_source(draft["raw"], qa))
    due = None
    for question, answer in qa:
        if "срок" in question.lower() or "дата" in question.lower():
            due = parse_ru_due(answer)
    result = ingest_thesis(
        conn,
        draft["raw"],
        focus=project,
        title=title,
        project=project,
        due=due,
        note=note,
    )
    conn.execute("UPDATE drafts SET status = 'done' WHERE id = 1")
    conn.commit()
    return result


def cancel_draft(conn) -> None:
    conn.execute("UPDATE drafts SET status = '' WHERE id = 1")
    conn.commit()
