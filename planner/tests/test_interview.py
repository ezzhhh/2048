import tempfile
import unittest
from pathlib import Path

from planner.interview import add_answer, finish_draft, questions_for, start_draft
from planner.server.db import connect


class InterviewTests(unittest.TestCase):
    def test_table_asks_restoris_questions(self):
        qs = questions_for("реализовать таблицу")
        self.assertEqual(len(qs), 3)
        self.assertTrue(any("упаков" in q.lower() or "Restoris" in q for q in qs))

    def test_three_answers_create_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "t.sqlite")
            first = start_draft(conn, "реализовать таблицу")
            self.assertIn("?", first)
            add_answer(conn, "да")
            add_answer(conn, "sheets")
            draft = add_answer(conn, "на доставке")
            result = finish_draft(conn, draft)
            self.assertTrue(result.stages)
            self.assertEqual(result.project, "ресторис")


if __name__ == "__main__":
    unittest.main()
