import tempfile
import unittest
from pathlib import Path

from ncm_monitor.db import Database
from ncm_monitor.structural import run_structural_monitor


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class StructuralTest(unittest.TestCase):
    def test_detects_structural_changes(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            db = Database(base / "db.sqlite")
            db.init_schema()
            snapshots = base / "snapshots"
            tabela = base / "tabela.csv"
            monitoradas = base / "ncms.csv"

            _write(monitoradas, "NCM\n87120010\n87120090\n")
            _write(tabela, "NCM,DESCRICAO\n87.12.00.10,Desc A\n87.12.00.90,Desc B\n")
            first = run_structural_monitor(db, tabela, monitoradas, snapshots)
            self.assertTrue(first.first_snapshot)

            _write(tabela, "NCM,DESCRICAO\n87.12.00.10,Desc A2\n")
            second = run_structural_monitor(db, tabela, monitoradas, snapshots)
            self.assertEqual(second.alterados, 1)
            self.assertEqual(second.removidos, 1)


if __name__ == "__main__":
    unittest.main()

