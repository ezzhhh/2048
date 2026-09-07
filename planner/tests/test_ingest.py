import tempfile
import unittest
from pathlib import Path

from planner.ingest import detect_project, formulate_title, ingest_thesis, suggest_stages
from planner.server.db import connect


class IngestTests(unittest.TestCase):
    def test_formulate_adds_verb(self):
        self.assertEqual(formulate_title("реализовать таблицу"), "Реализовать таблицу")
        self.assertTrue(formulate_title("таблица упаковки").startswith("Сделать"))

    def test_table_goes_to_restoris_with_stages(self):
        self.assertEqual(detect_project("реализовать таблицу упаковки"), "ресторис")
        stages = suggest_stages("Реализовать таблицу учёта", "ресторис")
        self.assertGreaterEqual(len(stages), 3)
        self.assertTrue(any("остат" in stage for stage in stages))

    def test_ingest_writes_parent_and_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "t.sqlite")
            result = ingest_thesis(conn, "реализовать таблицу", focus="ресторис")
            self.assertEqual(result.priority[0], "P")
            self.assertEqual(result.project, "ресторис")
            self.assertTrue(result.stages)
            kids = conn.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE parent_id = ?",
                (result.parent_id,),
            ).fetchone()["n"]
            self.assertEqual(kids, len(result.stages))


if __name__ == "__main__":
    unittest.main()
