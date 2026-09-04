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

    def test_board_requires_login(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    def test_wrong_password(self):
        response = self._login("nope")
        self.assertEqual(response.status_code, 401)

    def test_add_and_complete_writes_memory(self):
        self.assertEqual(self._login().status_code, 303)
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


if __name__ == "__main__":
    unittest.main()
