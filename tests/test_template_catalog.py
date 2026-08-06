from __future__ import annotations

import unittest
from pathlib import Path

from scripts import roteiro_to_instagram
from scripts.template_catalog import TEMPLATE_CATALOG, get_template, public_template_catalog


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ActiveTemplatesTest(unittest.TestCase):
    def test_only_tweet_and_stories_are_executable(self) -> None:
        self.assertEqual(set(roteiro_to_instagram.EDITOR_TEMPLATES), {"tweet", "stories"})
        self.assertEqual(roteiro_to_instagram.TEMPLATE_SLIDES_BY_NAME, {"tweet": 10, "stories": 10})
        self.assertFalse((PROJECT_ROOT / "templates" / "ostentacao_editor.html").exists())

    def test_generator_source_has_no_legacy_runtime_identifier(self) -> None:
        source = (PROJECT_ROOT / "scripts" / "roteiro_to_instagram.py").read_text(encoding="utf-8")
        self.assertNotIn("ostentacao", source.lower())


class TemplateCatalogTest(unittest.TestCase):
    def test_public_catalog_contains_only_official_templates(self) -> None:
        items = public_template_catalog()
        self.assertEqual([item["id"] for item in items], ["tweet", "stories"])
        self.assertEqual([item["initial_slides"] for item in items], [10, 10])

    def test_unknown_template_is_rejected(self) -> None:
        with self.assertRaisesRegex(KeyError, "Template desconhecido"):
            get_template("inexistente")

    def test_template_files_exist(self) -> None:
        for definition in TEMPLATE_CATALOG.values():
            with self.subTest(template=definition.id):
                self.assertTrue(definition.template_path.is_file())


if __name__ == "__main__":
    unittest.main()
