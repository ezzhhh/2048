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

    def test_vismart_typo_skips_project_question(self):
        qs = questions_for("рассылка визмарт")
        self.assertEqual(len(qs), 2)
        self.assertTrue(any("срок" in q.lower() or "База" in q for q in qs))
        self.assertFalse(any("мобилог" in q.lower() for q in qs))

    def test_visasmart_mailing_keeps_project_and_real_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "t.sqlite")
            start_draft(conn, "визасмарт")
            add_answer(conn, "реализованна рассылка")
            draft = add_answer(conn, "нужно начать завтра и закончить в воскресенье")
            result = finish_draft(conn, draft)
            self.assertEqual(result.project, "визасмарт")
            self.assertIn("рассыл", result.title.lower())
            self.assertTrue(any("баз" in s.lower() or "шаблон" in s.lower() for s in result.stages))
            self.assertFalse(any("ресторис" in s.lower() for s in result.stages))

    def test_screenshot_vismart_not_restoris_generic_stages(self):
        """Exact Telegram thread: рассылка визмарт → визмарт → рассылка по базе → до конца недели."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "t.sqlite")
            conn.execute(
                "INSERT INTO settings(key, value) VALUES('focus', 'ресторис')"
            )
            conn.commit()
            result = finish_draft(
                conn,
                {
                    "raw": "рассылка визмарт",
                    "questions": [
                        "Проект: restoris, визасмарт или мобилог?",
                        "Какой один проверяемый результат будет «готово»?",
                        "Срок есть? Если да — дата.",
                    ],
                    "answers": ["визмарт", "рассылка по базе", "до конца недели"],
                    "step": 3,
                },
            )
            self.assertEqual(result.project, "визасмарт")
            self.assertEqual(result.title, "Реализовать рассылку")
            self.assertTrue(
                any("баз" in s.lower() or "шаблон" in s.lower() for s in result.stages)
            )
            self.assertFalse(any("вводн" in s.lower() for s in result.stages))

    def test_new_mailing_path_skips_project_and_stays_visasmart(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "t.sqlite")
            conn.execute(
                "INSERT INTO settings(key, value) VALUES('focus', 'ресторис')"
            )
            conn.commit()
            start_draft(conn, "рассылка визмарт")
            add_answer(conn, "да, база есть")
            draft = add_answer(conn, "до конца недели")
            result = finish_draft(conn, draft)
            self.assertEqual(result.project, "визасмарт")
            self.assertEqual(result.title, "Реализовать рассылку")
            self.assertTrue(any("баз" in s.lower() or "шаблон" in s.lower() for s in result.stages))


if __name__ == "__main__":
    unittest.main()
