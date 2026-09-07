import tempfile
import unittest
from pathlib import Path

from planner.capture import handle_message
from planner.server.db import connect


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self.tmp.name) / "t.sqlite")
        self.conn.execute("INSERT INTO settings(key, value) VALUES('focus', 'ресторис')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_one_message_lands_on_board_without_questions(self):
        reply = handle_message(self.conn, "рассылка визмарт")
        self.assertIn("на доске", reply)
        self.assertNotIn("?", reply)
        self.assertIn("визасмарт", reply)
        self.assertIn("фокус остаётся ресторис", reply)
        focus = self.conn.execute(
            "SELECT value FROM settings WHERE key = 'focus'"
        ).fetchone()["value"]
        self.assertEqual(focus, "ресторис")
        row = self.conn.execute(
            "SELECT project, title FROM tasks WHERE parent_id IS NULL ORDER BY id DESC"
        ).fetchone()
        self.assertEqual(row["project"], "визасмарт")
        self.assertEqual(row["title"], "Реализовать рассылку")

    def test_unknown_task_does_not_enter_focus(self):
        reply = handle_message(self.conn, "позвонить")
        self.assertIn("другое", reply)
        row = self.conn.execute(
            "SELECT project FROM tasks WHERE parent_id IS NULL"
        ).fetchone()
        self.assertEqual(row["project"], "другое")

    def test_project_word_patches_last_other_task(self):
        handle_message(self.conn, "рассылка")
        reply = handle_message(self.conn, "визмарт")
        self.assertIn("визасмарт", reply)
        row = self.conn.execute(
            "SELECT project, title FROM tasks WHERE parent_id IS NULL"
        ).fetchone()
        self.assertEqual(row["project"], "визасмарт")
        self.assertEqual(row["title"], "Реализовать рассылку")
        n = self.conn.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE parent_id IS NULL"
        ).fetchone()["n"]
        self.assertEqual(n, 1)

    def test_due_word_patches_last(self):
        handle_message(self.conn, "рассылка визмарт")
        reply = handle_message(self.conn, "до конца недели")
        self.assertIn("срок", reply)
        row = self.conn.execute(
            "SELECT due FROM tasks WHERE parent_id IS NULL"
        ).fetchone()
        self.assertTrue(row["due"])

    def test_list_keeps_focus_and_shows_off_focus(self):
        handle_message(self.conn, "рассылка визмарт")
        listing = handle_message(self.conn, "список")
        self.assertIn("фокус: ресторис", listing)
        self.assertIn("вне фокуса", listing)
        self.assertIn("визасмарт", listing)

    def test_undo_removes_last_capture(self):
        handle_message(self.conn, "рассылка визмарт")
        reply = handle_message(self.conn, "отмена")
        self.assertIn("убрал", reply)
        open_n = self.conn.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE status != 'x' AND parent_id IS NULL"
        ).fetchone()["n"]
        self.assertEqual(open_n, 0)


if __name__ == "__main__":
    unittest.main()
