from __future__ import annotations

import unittest
from pathlib import Path

from scripts import roteiro_to_instagram
from scripts.template_catalog import TEMPLATE_CATALOG, get_template, public_template_catalog


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ActiveTemplatesTest(unittest.TestCase):
    def test_official_templates_are_executable(self) -> None:
        self.assertEqual(
            set(roteiro_to_instagram.EDITOR_TEMPLATES),
            {"tweet", "stories", "stories-fundo", "notes"},
        )
        self.assertEqual(
            roteiro_to_instagram.TEMPLATE_SLIDES_BY_NAME,
            {"tweet": 10, "stories": 10, "stories-fundo": 10, "notes": 10},
        )
        self.assertFalse((PROJECT_ROOT / "templates" / "ostentacao_editor.html").exists())

    def test_generator_source_has_no_legacy_runtime_identifier(self) -> None:
        source = (PROJECT_ROOT / "scripts" / "roteiro_to_instagram.py").read_text(encoding="utf-8")
        self.assertNotIn("ostentacao", source.lower())


class TemplateCatalogTest(unittest.TestCase):
    def test_public_catalog_contains_official_templates(self) -> None:
        items = public_template_catalog()
        self.assertEqual([item["id"] for item in items], ["tweet", "stories", "stories-fundo", "notes"])
        self.assertEqual([item["initial_slides"] for item in items], [10, 10, 10, 10])
        self.assertEqual([item["aspect_ratio"] for item in items], ["4:5", "4:5", "4:5", "4:5"])

    def test_stories_catalog_keeps_4_5_default_and_offers_matching_3_4_export(self) -> None:
        hub = (PROJECT_ROOT / "templates" / "hub.html").read_text(encoding="utf-8")
        tweet = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(encoding="utf-8")
        stories = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(encoding="utf-8")
        notes = (PROJECT_ROOT / "templates" / "notes_editor.html").read_text(encoding="utf-8")

        self.assertEqual(get_template("stories").aspect_ratio, "4:5")
        self.assertRegex(
            hub,
            r"\.preview-sheet--stories\s*\{[^}]*aspect-ratio:\s*4\s*/\s*5;",
        )
        self.assertIn("const SLIDE_W = 1080;", stories)
        self.assertIn("let SLIDE_H = 1350;", stories)
        self.assertIn("const STORIES_RATIO_HEIGHTS = { '4:5': 1350, '3:4': 1440 };", stories)
        self.assertIn('data-stories-ratio="3:4"', stories)
        self.assertIn("const dpr = 2;", stories)
        self.assertIn("const W = 1080;", tweet)
        self.assertEqual(get_template("notes").aspect_ratio, "4:5")
        self.assertIn("Bloco de Notas", notes)
        self.assertIn("preview-sheet--notes", hub)
        self.assertIn("'4:5': 1350", tweet)

    def test_background_stories_keeps_photo_and_cartela_in_preview_and_png(self) -> None:
        background_stories = (PROJECT_ROOT / "templates" / "stories_background_editor.html").read_text(
            encoding="utf-8"
        )
        hub = (PROJECT_ROOT / "templates" / "hub.html").read_text(encoding="utf-8")
        self.assertEqual(get_template("stories-fundo").name, "Stories C/ Fundo")
        for marker in (
            "await drawPhoto(ctx, slideData.image, SLIDE_W, SLIDE_H);",
            "function drawLegibilityFilter(ctx, w, h, fade)",
            "function getEditorialCard(block)",
            "data-card=\"light\"",
            "data-card=\"dark\"",
            "commitFullBleedImage",
            "typography: 'advercase'",
        ):
            self.assertIn(marker, background_stories)
        self.assertIn("preview-sheet--stories-fundo", hub)

    def test_background_stories_supports_equal_vertical_photo_split(self) -> None:
        background_stories = (PROJECT_ROOT / "templates" / "stories_background_editor.html").read_text(
            encoding="utf-8"
        )
        for marker in (
            'data-image-composer-mode="stack"',
            "Uma sobre a outra",
            "function commitFullBleedComposition",
            "kind: 'composition'",
            "mode === 'stack'",
            "drawPhotoInFrame(ctx, first, imageData.photos.first, 0, 0, w, halfHeight);",
            "drawPhotoInFrame(ctx, second, imageData.photos.second, 0, halfHeight, w, halfHeight);",
            "Cada foto ocupa metade vertical do canvas",
            "persistImageTransform(i, imageTarget);",
            "photoLayer.addEventListener('dblclick'",
            "document.body.classList.add('space-held')",
            "function getPhotoAtPointer(e)",
            "e.stopImmediatePropagation();",
        ):
            self.assertIn(marker, background_stories)

    def test_unknown_template_is_rejected(self) -> None:
        with self.assertRaisesRegex(KeyError, "Template desconhecido"):
            get_template("inexistente")

    def test_template_files_exist(self) -> None:
        for definition in TEMPLATE_CATALOG.values():
            with self.subTest(template=definition.id):
                self.assertTrue(definition.template_path.is_file())


if __name__ == "__main__":
    unittest.main()
