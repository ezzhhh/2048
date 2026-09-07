"""Private Telegram inbox: one user, same SQLite board. No public commands."""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

from planner.capture import handle_message
from planner.server import db

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
    return handle_message(conn, text)


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
                    _send(
                        token,
                        chat_id,
                        "Пиши задачу одним сообщением — сразу на доску.\n"
                        "проект или срок можно дописать следующим словом.\n"
                        "список · готово · отмена · фокус ресторис",
                    )
                    continue
                _send(token, chat_id, _handle(conn, text))
        except Exception as exc:  # noqa: BLE001 — keep polling
            time.sleep(3)
            print(f"tg loop: {exc}", flush=True)


if __name__ == "__main__":
    run()
