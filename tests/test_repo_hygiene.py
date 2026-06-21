import unittest
from pathlib import Path

_ROOT = Path(__file__).parent.parent


class RepoHygieneTests(unittest.TestCase):
    def test_dead_chat_store_module_is_removed(self) -> None:
        self.assertFalse((_ROOT / "digikey_scraper/chat_store.py").exists())

    def test_gitignore_ignores_generated_build_outputs(self) -> None:
        text = (_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("build/", text)
        self.assertIn("dist/", text)

    def test_windows_workflow_runs_pytest_with_safe_env(self) -> None:
        text = (_ROOT / ".github/workflows/windows.yml").read_text(encoding="utf-8")
        self.assertIn("PYTEST_DISABLE_PLUGIN_AUTOLOAD", text)
        self.assertIn("QT_QPA_PLATFORM", text)
        self.assertIn("python -m pytest -q", text)

    def test_readme_documents_safe_full_test_command(self) -> None:
        text = (_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen", text)
        self.assertIn("python -m pytest -q", text)


if __name__ == "__main__":
    unittest.main()
