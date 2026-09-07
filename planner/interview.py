"""Ask at most 3 leading questions, then form a staged task."""

from __future__ import annotations

import json
from pathlib import Path

from planner.ingest import formulate_title, ingest_thesis, normalize_typos
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


def finish_draft(conn, draft: dict):
    qa = []
    for q, a in zip(draft["questions"], draft["answers"]):
        qa.append(f"{q} → {a}")
    note = " | ".join(qa)
    title = formulate_title(draft["raw"])
    enriched = f"{title}. {note}"
    result = ingest_thesis(conn, enriched, focus=db.get_setting(conn, "focus") or "ресторис")
    conn.execute("UPDATE drafts SET status = 'done' WHERE id = 1")
    conn.commit()
    return result


def cancel_draft(conn) -> None:
    conn.execute("UPDATE drafts SET status = '' WHERE id = 1")
    conn.commit()
