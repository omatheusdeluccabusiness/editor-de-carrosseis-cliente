from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TWEET_TEMPLATE = PROJECT_ROOT / "templates" / "tweet_editor.html"


class TweetHighlightsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = TWEET_TEMPLATE.read_text(encoding="utf-8")

    def test_contextual_palette_is_accessible(self) -> None:
        required = (
            'id="tweet-highlight-menu"',
            'role="toolbar"',
            'aria-label="Cores do marca-texto"',
            'data-highlight-color="yellow"',
            'data-highlight-color="pink"',
            'data-highlight-color="green"',
            'data-highlight-color="blue"',
            'data-highlight-action="clear"',
            'aria-label="Remover realce"',
        )
        for marker in required:
            self.assertIn(marker, self.html)

    def test_highlights_use_semantic_theme_maps(self) -> None:
        required = (
            "const HIGHLIGHT_COLORS = ['yellow', 'pink', 'green', 'blue']",
            "const HIGHLIGHT_THEME_COLORS = {",
            "function normalizeHighlightColor(value)",
            "body.theme-dark .tweet-render mark[data-highlight]",
            "--marker-yellow",
            "--marker-pink",
            "--marker-green",
            "--marker-blue",
        )
        for marker in required:
            self.assertIn(marker, self.html)

    def test_serialization_contract_is_limited(self) -> None:
        required = (
            "function parseRichTextMarkdown(text)",
            "function serializeRichTextDOM(html)",
            "[hl=",
            "[/hl]",
            "data-highlight",
            "normalizeHighlightColor(node.dataset.highlight)",
        )
        for marker in required:
            self.assertIn(marker, self.html)


if __name__ == "__main__":
    unittest.main()
