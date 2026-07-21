from __future__ import annotations

import re
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

    def test_selection_controller_has_bounded_range_and_commands(self) -> None:
        required = (
            "function getTweetBodyForRange(range)",
            "function showHighlightMenu(range)",
            "function hideHighlightMenu()",
            "function applyHighlightToSavedRange(color)",
            "function clearHighlightFromSavedRange()",
            "document.addEventListener('selectionchange'",
            "e.key === 'Escape'",
            "range.cloneRange()",
            "function extractRichTextUnits(bodyEl)",
            "function getBoundaryOffset(bodyEl, container, offset)",
            "function renderRichTextUnits(units)",
        )
        for marker in required:
            self.assertIn(marker, self.html)

    def test_commands_resync_slide_state(self) -> None:
        required = (
            "function syncHighlightedBody(bodyEl)",
            "slidesState[index].text = htmlToMarkdown(bodyEl.innerHTML)",
            "saveState()",
            "applyLayout(index)",
        )
        for marker in required:
            self.assertIn(marker, self.html)

    def test_dom_segments_carry_highlight_identity(self) -> None:
        required = (
            "{ text: ch, bold: isBold, highlight: highlightColor }",
            "const newHighlight = tag === 'MARK'",
            "walk(child, newBold, newHighlight)",
        )
        for marker in required:
            self.assertIn(marker, self.html)

    def test_canvas_draws_theme_marker_before_text(self) -> None:
        required = (
            "function drawMarkerStroke(ctx, x, y, width, fontSize, color)",
            "HIGHLIGHT_THEME_COLORS[dark ? 'dark' : 'light']",
            "drawMarkerStroke(ctx, x, y, segmentWidth, fontSize, markerColor)",
        )
        for marker in required:
            self.assertIn(marker, self.html)
        self.assertLess(
            self.html.index("drawMarkerStroke(ctx, x, y, segmentWidth"),
            self.html.index("ctx.fillText(seg.text, x, y)"),
        )

    def test_canvas_marker_uses_the_same_vertical_band_as_preview(self) -> None:
        preview = re.search(
            r'mark\[data-highlight="yellow"\].*?transparent\s+(\d+)%,\s*'
            r'var\(--marker-yellow\)\s+\d+%,\s*'
            r'var\(--marker-yellow\)\s+(\d+)%',
            self.html,
        )
        canvas_top = re.search(r"const top = y \+ fontSize \* ([0-9.]+);", self.html)
        canvas_bottom = re.search(r"const bottom = y \+ fontSize \* ([0-9.]+);", self.html)

        self.assertIsNotNone(preview)
        self.assertIsNotNone(canvas_top)
        self.assertIsNotNone(canvas_bottom)
        self.assertAlmostEqual(float(canvas_top.group(1)), int(preview.group(1)) / 100)
        self.assertAlmostEqual(float(canvas_bottom.group(1)), int(preview.group(2)) / 100)


if __name__ == "__main__":
    unittest.main()
