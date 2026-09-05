import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["PLANER_USER"] = "me"
        os.environ["PLANER_PASSWORD"] = "secret-pass"
        os.environ["PLANER_SECRET"] = "1234567890abcdef"
        os.environ["PLANER_DATA"] = str(Path(self.tmp.name) / "t.sqlite")
        from planner.server.app import create_app

        self.client = TestClient(create_app())

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def _login(self, password: str = "secret-pass"):
        return self.client.post(
            "/login",
            data={"user": "me", "password": password},
            follow_redirects=False,
        )

    def _setup(self, import_from: str = "none", password: str = ""):
        return self.client.post(
            "/setup",
            data={"password": password, "focus": "ресторис", "import_from": import_from},
            follow_redirects=False,
        )

    def test_board_requires_login(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    def test_wrong_password(self):
        response = self._login("nope")
        self.assertEqual(response.status_code, 401)

    def test_login_opens_setup_first(self):
        response = self._login()
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/setup")

    def test_setup_imports_example_and_sets_password(self):
        self.assertEqual(self._login().status_code, 303)
        done = self._setup(import_from="example", password="new-secret")
        self.assertEqual(done.status_code, 303)
        board = self.client.get("/")
        self.assertEqual(board.status_code, 200)
        self.assertIn("Отказ", board.text)
        self.client.post("/logout")
        bad = self._login("secret-pass")
        self.assertEqual(bad.status_code, 401)
        ok = self._login("new-secret")
        self.assertEqual(ok.status_code, 303)
        self.assertEqual(ok.headers["location"], "/")

    def test_add_and_complete_writes_memory(self):
        self.assertEqual(self._login().status_code, 303)
        self.assertEqual(self._setup().status_code, 303)
        added = self.client.post(
            "/tasks",
            data={
                "title": "Добавить этап Отказ",
                "project": "ресторис",
                "due": "04.09",
                "note": "блокер",
                "blocker": "1",
            },
            follow_redirects=False,
        )
        self.assertEqual(added.status_code, 303)
        board = self.client.get("/")
        self.assertEqual(board.status_code, 200)
        self.assertIn("Добавить этап Отказ", board.text)
        self.assertIn("P0", board.text)

        done = self.client.post(
            "/tasks/1/done",
            data={"decision": "сделали справочник", "outcome": "готово", "lesson": "сначала причины"},
            follow_redirects=False,
        )
        self.assertEqual(done.status_code, 303)
        memory = self.client.get("/memory")
        self.assertIn("сделали справочник", memory.text)
        self.assertIn("сначала причины", memory.text)


    def test_import_markdown_keeps_stages(self):
        from planner.server.db import connect, import_markdown, list_tasks

        conn = connect(Path(self.tmp.name) / "imp.sqlite")
        n = import_markdown(
            conn,
            "- [~] Добавить этап Отказ | проект: restoris | срок: 04.09 | блокер\n"
            "  - [ ] Зафиксировать справочник | часть: 1/2\n",
        )
        self.assertEqual(n, 2)
        rows = list_tasks(conn, include_done=True)
        roots = [row for row in rows if not row["parent_id"]]
        kids = [row for row in rows if row["parent_id"]]
        self.assertEqual(len(roots), 1)
        self.assertEqual(len(kids), 1)
        self.assertEqual(kids[0]["parent_id"], roots[0]["id"])
        conn.close()


if __name__ == "__main__":
    unittest.main()
