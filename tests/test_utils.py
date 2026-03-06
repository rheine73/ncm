import unittest

from ncm_monitor.utils import build_ncm_pattern, normalize_ncm


class UtilsTest(unittest.TestCase):
    def test_normalize_ncm(self):
        self.assertEqual(normalize_ncm("87.12.00.10"), "87120010")
        self.assertEqual(normalize_ncm("8712-00-10"), "87120010")

    def test_pattern_ncm(self):
        p = build_ncm_pattern("87120010")
        self.assertIsNotNone(p.search("NCM 87120010"))
        self.assertIsNotNone(p.search("NCM 87.12.00.10"))
        self.assertIsNone(p.search("NCM 871200100"))


if __name__ == "__main__":
    unittest.main()

