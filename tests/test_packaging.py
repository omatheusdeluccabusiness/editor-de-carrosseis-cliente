from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class PackagingTest(unittest.TestCase):
    def test_requirements_cover_all_third_party_imports(self) -> None:
        requirements = (PROJECT_ROOT / "requirements.txt").read_text(
            encoding="utf-8"
        ).lower()
        for dependency in ("cryptography", "pillow", "python-dotenv", "requests"):
            with self.subTest(dependency=dependency):
                self.assertIn(dependency, requirements)

    def test_active_docs_describe_the_hub_and_current_templates(self) -> None:
        agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        for text in (agents, readme):
            self.assertIn("Tweet", text)
            self.assertIn("Stories", text)
            self.assertIn("10 slides", text)
            self.assertNotIn("ostentacao", text.lower())
            self.assertNotIn("17 slides", text.lower())
        self.assertIn("HUB", readme)
        self.assertIn("http://localhost:8777", readme)

    def test_readme_documents_desktop_install_and_local_credentials(self) -> None:
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Aplicativo desktop", readme)
        self.assertIn("chave de recuperacao", readme)
        self.assertIn("Windows", readme)
        self.assertIn("macOS", readme)


if __name__ == "__main__":
    unittest.main()
