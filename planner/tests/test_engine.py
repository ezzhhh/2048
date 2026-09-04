import tempfile
import unittest
from datetime import date
from pathlib import Path

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


TODAY = date(2026, 9, 4)


class ParseAndScoreTests(unittest.TestCase):
    def test_overdue_blocker_is_p0(self):
        task = parse_task_line(
            "- [~] Добавить этап Отказ | проект: restoris | приоритет: P2 | срок: 04.09 | блокер для Доставка",
            today=TODAY,
        )
        self.assertIsNotNone(task)
        scored = score_priority(task, today=TODAY, focus="ресторис")
        self.assertEqual(scored.code, "P0")
        self.assertIn("срок сегодня", scored.why)
        self.assertIn("блокер", scored.why)

    def test_later_without_date_is_p3(self):
        task = parse_task_line(
            "- [ ] Оценить UIS | проект: restoris | позже",
            today=TODAY,
        )
        scored = score_priority(task, today=TODAY)
        self.assertEqual(scored.code, "P3")

    def test_deploy_without_date_is_at_least_p1(self):
        task = parse_task_line(
            "- [ ] Задеплоить статус оплаты | проект: restoris | в коде уже есть",
            today=TODAY,
        )
        scored = score_priority(task, today=TODAY)
        self.assertEqual(scored.code, "P1")

    def test_iso_due_today_is_p0(self):
        task = parse_task_line(
            "- [ ] Добавить этап Отказ | проект: restoris | срок: 2026-09-04 | блокер",
            today=TODAY,
        )
        scored = score_priority(task, today=TODAY)
        self.assertEqual(scored.code, "P0")

    def test_due_within_three_days(self):
        task = parse_task_line(
            "- [ ] Собрать таблицу упаковки | проект: restoris | срок: 07.09",
            today=TODAY,
        )
        scored = score_priority(task, today=TODAY)
        self.assertIn(scored.code, {"P1", "P2"})
        self.assertIn("срок ≤3 дней", scored.why)


class LintAndDecomposeTests(unittest.TestCase):
    def test_empty_verb_is_error(self):
        task = parse_task_line("- [ ] разобраться | проект: restoris", today=TODAY)
        issues = lint_formulation(task)
        self.assertTrue(any(issue.level == "error" for issue in issues))

    def test_missing_project_is_error(self):
        task = parse_task_line("- [ ] Добавить этап Отказ", today=TODAY)
        issues = lint_formulation(task)
        self.assertTrue(any("проект" in issue.message for issue in issues))

    def test_good_line_has_no_errors(self):
        task = parse_task_line(
            "- [ ] Добавить этап Отказ | проект: restoris | приоритет: P0",
            today=TODAY,
        )
        issues = lint_formulation(task)
        self.assertFalse(any(issue.level == "error" for issue in issues))

    def test_fork_needs_breakdown(self):
        task = parse_task_line(
            "- [ ] Решить канал webhook Доставка: n8n или свой | проект: restoris",
            today=TODAY,
        )
        self.assertTrue(should_decompose(task))

    def test_later_does_not_need_breakdown(self):
        task = parse_task_line(
            "- [ ] Оценить UIS | проект: restoris | позже",
            today=TODAY,
        )
        self.assertFalse(should_decompose(task))


class BoardAndMemoryTests(unittest.TestCase):
    BOARD = """
## Restoris
- [~] Добавить этап Отказ | проект: restoris | срок: 03.09 | блокер
  - [ ] Зафиксировать справочник причин | часть: 1/2
- [ ] Задеплоить статус оплаты | проект: restoris
- [ ] Оценить UIS | проект: restoris | позже
"""

    def test_next_step_picks_p0(self):
        board = parse_board(self.BOARD, today=TODAY)
        lines = suggest_next_steps(board, focus="ресторис", today=TODAY)
        self.assertTrue(lines[0].startswith("1. P0"))
        self.assertIn("Отказ", lines[0])

    def test_children_are_not_top_level_next(self):
        board = parse_board(self.BOARD, today=TODAY)
        top = [task.title for task in board.tasks if not task.child]
        self.assertNotIn("Зафиксировать справочник причин", top)

    def test_memory_log_appends(self):
        entry = format_log_entry(
            "ресторис",
            "канал доставки",
            "свой webhook",
            "выбрали свой",
            lesson="сначала развилка",
            day=TODAY,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TASK_LOG.md"
            append_task_log(path, entry)
            append_task_log(path, entry)
            text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count("канал доставки"), 2)
        self.assertIn("сначала развилка", text)


if __name__ == "__main__":
    unittest.main()
