from __future__ import annotations

import unittest
from pathlib import Path

from scripts import roteiro_to_instagram


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ActiveTemplatesTest(unittest.TestCase):
    def test_only_tweet_and_stories_are_executable(self) -> None:
        self.assertEqual(set(roteiro_to_instagram.EDITOR_TEMPLATES), {"tweet", "stories"})
        self.assertEqual(roteiro_to_instagram.TEMPLATE_SLIDES_BY_NAME, {"tweet": 10, "stories": 10})
        self.assertFalse((PROJECT_ROOT / "templates" / "ostentacao_editor.html").exists())

    def test_generator_source_has_no_legacy_runtime_identifier(self) -> None:
        source = (PROJECT_ROOT / "scripts" / "roteiro_to_instagram.py").read_text(encoding="utf-8")
        self.assertNotIn("ostentacao", source.lower())


if __name__ == "__main__":
    unittest.main()
