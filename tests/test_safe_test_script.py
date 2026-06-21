import unittest
from pathlib import Path


class SafeTestScriptTests(unittest.TestCase):
    def test_safe_test_script_exists_with_required_flags(self) -> None:
        path = Path("scripts/test_category_safe.sh")
        self.assertTrue(path.exists(), "safe test script missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn("PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", text)
        self.assertIn("QT_QPA_PLATFORM=offscreen", text)
        self.assertIn(".venv/bin/python", text)
        self.assertIn("tests/test_category_search.py", text)


if __name__ == "__main__":
    unittest.main()
