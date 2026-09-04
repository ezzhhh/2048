"""CLI: list / next / score / lint / log — deterministic helper for the agent."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from planner.engine import (
    append_task_log,
    format_log_entry,
    lint_formulation,
    parse_board,
    parse_task_line,
    score_priority,
    should_decompose,
    suggest_next_steps,
)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def cmd_list(args: argparse.Namespace) -> int:
    board = parse_board(_read(args.board))
    focus = args.focus
    rows = []
    for task in board.tasks:
        if not task.open or task.child:
            continue
        scored = score_priority(task, focus=focus)
        rows.append((scored, task))
    rows.sort(key=lambda item: (item[0].code, -item[0].score))
    for scored, task in rows:
        project = task.project or "?"
        print(f"{scored.code}\t{project}\t{task.title}\t{scored.why}")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    board = parse_board(_read(args.board))
    for line in suggest_next_steps(board, focus=args.focus):
        print(line)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    line = args.line
    task = parse_task_line(line)
    if task is None:
        print("не строка задачи", file=sys.stderr)
        return 2
    if args.blocker:
        task.blocker = True
    scored = score_priority(task, focus=args.focus)
    print(f"{scored.code} · {scored.why} · score={scored.score}")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    task = parse_task_line(args.line)
    if task is None:
        print("не строка задачи", file=sys.stderr)
        return 2
    issues = list(lint_formulation(task))
    if should_decompose(task) or args.decompose:
        from planner.engine import LintIssue

        issues.append(LintIssue("warn", "нужна декомпозиция"))
    for issue in issues:
        print(f"{issue.level}: {issue.message}")
    return 1 if any(issue.level == "error" for issue in issues) else 0


def cmd_log(args: argparse.Namespace) -> int:
    entry = format_log_entry(
        project=args.project,
        task=args.task,
        decision=args.decision,
        outcome=args.outcome,
        lesson=args.lesson or "",
        day=date.today(),
    )
    path = Path(args.path)
    append_task_log(path, entry)
    print(entry.rstrip())
    print(f"записано: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Планировщик: приоритет, lint, память")
    sub = parser.add_subparsers(dest="cmd", required=True)

    common_board = argparse.ArgumentParser(add_help=False)
    common_board.add_argument("--board", default="planner/ПЛАНЕР.md")
    common_board.add_argument("--focus")

    listing = sub.add_parser("list", parents=[common_board])
    listing.set_defaults(func=cmd_list)

    nxt = sub.add_parser("next", parents=[common_board])
    nxt.set_defaults(func=cmd_next)

    score = sub.add_parser("score")
    score.add_argument("line")
    score.add_argument("--focus")
    score.add_argument("--blocker", action="store_true")
    score.set_defaults(func=cmd_score)

    lint = sub.add_parser("lint")
    lint.add_argument("line")
    lint.add_argument("--decompose", action="store_true")
    lint.set_defaults(func=cmd_lint)

    log = sub.add_parser("log")
    log.add_argument("--project", required=True)
    log.add_argument("--task", required=True)
    log.add_argument("--decision", required=True)
    log.add_argument("--outcome", required=True)
    log.add_argument("--lesson", default="")
    log.add_argument("--path", default="planner/memory/TASK_LOG.md")
    log.set_defaults(func=cmd_log)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
