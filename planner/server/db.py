"""SQLite store on the server disk. No git."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sqlite3

from planner.engine import Task, normalize_project, parse_due


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT ' ',
    title TEXT NOT NULL,
    project TEXT,
    priority TEXT,
    due TEXT,
    note TEXT NOT NULL DEFAULT '',
    part TEXT,
    parent_id INTEGER,
    later INTEGER NOT NULL DEFAULT 0,
    blocker INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    done_at TEXT
);
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    project TEXT NOT NULL,
    task TEXT NOT NULL,
    decision TEXT NOT NULL,
    outcome TEXT NOT NULL,
    lesson TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def row_to_task(row: sqlite3.Row) -> Task:
    today = date.today()
    due = parse_due(row["due"], today) if row["due"] else None
    return Task(
        status=row["status"],
        title=row["title"],
        project=row["project"],
        declared_priority=row["priority"],
        due=due,
        note=row["note"] or "",
        part=row["part"],
        raw="",
        indent=2 if row["parent_id"] else 0,
        later=bool(row["later"]),
        blocker=bool(row["blocker"]),
    )


def list_tasks(conn: sqlite3.Connection, include_done: bool = False) -> list[sqlite3.Row]:
    sql = "SELECT * FROM tasks"
    if not include_done:
        sql += " WHERE status != 'x'"
    sql += " ORDER BY parent_id IS NOT NULL, id"
    return list(conn.execute(sql).fetchall())


def get_task(conn: sqlite3.Connection, task_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def children_of(conn: sqlite3.Connection, parent_id: int) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM tasks WHERE parent_id = ? ORDER BY id", (parent_id,)
        ).fetchall()
    )


def insert_task(
    conn: sqlite3.Connection,
    *,
    title: str,
    project: str | None,
    priority: str | None,
    due: str | None,
    note: str,
    part: str | None,
    parent_id: int | None,
    later: bool,
    blocker: bool,
    status: str = " ",
) -> int:
    stamp = now_iso()
    cur = conn.execute(
        """
        INSERT INTO tasks(status, title, project, priority, due, note, part, parent_id, later, blocker, created_at, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            status,
            title.strip(),
            normalize_project(project),
            priority,
            due or None,
            note.strip(),
            part,
            parent_id,
            int(later),
            int(blocker),
            stamp,
            stamp,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_task(conn: sqlite3.Connection, task_id: int, **fields: object) -> None:
    if not fields:
        return
    fields = {key: value for key, value in fields.items() if key in {
        "status", "title", "project", "priority", "due", "note", "part",
        "parent_id", "later", "blocker", "done_at",
    }}
    if "project" in fields:
        fields["project"] = normalize_project(fields["project"] if isinstance(fields["project"], str) else None)
    if "later" in fields:
        fields["later"] = int(bool(fields["later"]))
    if "blocker" in fields:
        fields["blocker"] = int(bool(fields["blocker"]))
    fields["updated_at"] = now_iso()
    assignments = ", ".join(f"{key} = ?" for key in fields)
    conn.execute(
        f"UPDATE tasks SET {assignments} WHERE id = ?",
        (*fields.values(), task_id),
    )
    conn.commit()


def add_memory(
    conn: sqlite3.Connection,
    *,
    project: str,
    task: str,
    decision: str,
    outcome: str,
    lesson: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO memory(day, project, task, decision, outcome, lesson, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        """,
        (
            date.today().isoformat(),
            project,
            task,
            decision,
            outcome,
            lesson,
            now_iso(),
        ),
    )
    conn.commit()


def list_memory(conn: sqlite3.Connection, limit: int = 100) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM memory ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    )
