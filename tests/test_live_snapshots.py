import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ncm_monitor.live_snapshots import compare_and_save_live_snapshot


class LiveSnapshotsTest(unittest.TestCase):
    def test_compare_and_save_live_snapshot(self):
        with TemporaryDirectory() as tmp:
            snapshots_dir = Path(tmp) / "snapshots"
            ncm = "65061000"

            first_events = [
                {
                    "data_publicacao": "01/02/2026",
                    "tipo_alteracao": "ALTERACAO",
                    "titulo": "Ato 1",
                    "url": "https://exemplo/ato-1",
                }
            ]
            first = compare_and_save_live_snapshot(snapshots_dir, ncm, first_events)
            self.assertTrue(first.first_snapshot)
            self.assertEqual(first.current_count, 1)
            self.assertEqual(len(first.new_events), 1)
            self.assertEqual(len(first.removed_events), 0)
            self.assertTrue(first.latest_path.exists())
            self.assertTrue(first.archive_path.exists())

            second_events = [
                {
                    "data_publicacao": "01/02/2026",
                    "tipo_alteracao": "ALTERACAO",
                    "titulo": "Ato 1",
                    "url": "https://exemplo/ato-1",
                },
                {
                    "data_publicacao": "02/02/2026",
                    "tipo_alteracao": "INCLUSAO",
                    "titulo": "Ato 2",
                    "url": "https://exemplo/ato-2",
                },
            ]
            second = compare_and_save_live_snapshot(snapshots_dir, ncm, second_events)
            self.assertFalse(second.first_snapshot)
            self.assertEqual(second.previous_count, 1)
            self.assertEqual(second.current_count, 2)
            self.assertEqual(len(second.new_events), 1)
            self.assertEqual(second.new_events[0]["url"], "https://exemplo/ato-2")
            self.assertEqual(len(second.removed_events), 0)

            third_events = [
                {
                    "data_publicacao": "02/02/2026",
                    "tipo_alteracao": "INCLUSAO",
                    "titulo": "Ato 2",
                    "url": "https://exemplo/ato-2",
                }
            ]
            third = compare_and_save_live_snapshot(snapshots_dir, ncm, third_events)
            self.assertFalse(third.first_snapshot)
            self.assertEqual(third.previous_count, 2)
            self.assertEqual(third.current_count, 1)
            self.assertEqual(len(third.new_events), 0)
            self.assertEqual(len(third.removed_events), 1)
            self.assertEqual(third.removed_events[0]["url"], "https://exemplo/ato-1")


if __name__ == "__main__":
    unittest.main()
