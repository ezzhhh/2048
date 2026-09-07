"""Private Telegram inbox: one user, same SQLite board. No public commands."""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

from planner.ingest import format_result, ingest_thesis
from planner.engine import suggest_next_steps, Board
from planner.server import db
from planner.server.db import row_to_task

API = "https://api.telegram.org"


def _data_path() -> Path:
    return Path(os.environ.get("PLANER_DATA", Path(__file__).resolve().parent / "data" / "planer.sqlite"))


def _token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    return token


def _allowed() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def _send(token: str, chat_id: int, text: str) -> None:
    httpx.post(
        f"{API}/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    ).raise_for_status()


def _handle(conn, text: str) -> str:
    raw = text.strip()
    low = raw.lower()
    if low in {"список", "/список", "/list", "list"}:
        rows = [row for row in db.list_tasks(conn) if not row["parent_id"] and row["status"] != "x"]
        board = Board(tasks=[row_to_task(row) for row in db.list_tasks(conn, include_done=True)])
        nxt = "\n".join(suggest_next_steps(board, focus=db.get_setting(conn, "focus") or None))
        lines = [nxt, ""]
        for row in rows[:12]:
            lines.append(f"{row['priority'] or '?'} · {row['title']}")
        return "\n".join(lines).strip() or "Открытых задач нет."
    if low.startswith("фокус"):
        project = raw.split(None, 1)[1] if " " in raw else ""
        db.set_setting(conn, "focus", project)
        return f"фокус: {project or 'все'}"
    if low.startswith("готово"):
        needle = raw.split(None, 1)[1].lower() if " " in raw else ""
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
    result = ingest_thesis(conn, raw, focus=db.get_setting(conn, "focus"))
    return format_result(result)


def run() -> None:
    token = _token()
    allowed = _allowed()
    conn = db.connect(_data_path())
    offset = 0
    while True:
        try:
            response = httpx.get(
                f"{API}/bot{token}/getUpdates",
                params={"timeout": 25, "offset": offset},
                timeout=35,
            )
            response.raise_for_status()
            for update in response.json().get("result", []):
                offset = int(update["update_id"]) + 1
                message = update.get("message") or update.get("edited_message") or {}
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                text = (message.get("text") or "").strip()
                if not chat_id or not text:
                    continue
                if not allowed:
                    db.set_setting(conn, "telegram_chat_id", str(chat_id))
                    os.environ["TELEGRAM_CHAT_ID"] = str(chat_id)
                    allowed = str(chat_id)
                if str(chat_id) != str(allowed):
                    continue
                if text in {"/start", "старт"}:
                    _send(token, chat_id, "Пишите задачу обычным сообщением.\nсписок · готово … · фокус ресторис")
                    continue
                _send(token, chat_id, _handle(conn, text))
        except Exception as exc:  # noqa: BLE001 — keep polling
            time.sleep(3)
            print(f"tg loop: {exc}", flush=True)


if __name__ == "__main__":
    run()
