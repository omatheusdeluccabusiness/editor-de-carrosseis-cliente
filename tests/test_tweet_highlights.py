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

    def test_marker_never_changes_copy_metrics_and_canvas_matches_its_band(self) -> None:
        self.assertIn("padding: 0;", self.html)
        self.assertIn("margin: 0;", self.html)
        self.assertIn("background-size: 100% 1.04em;", self.html)
        self.assertIn("background-position: 0 0.02em;", self.html)
        canvas_top = re.search(r"const top = y \+ fontSize \* ([0-9.]+);", self.html)
        canvas_height = re.search(r"const height = fontSize \* ([0-9.]+);", self.html)

        self.assertIsNotNone(canvas_top)
        self.assertIsNotNone(canvas_height)
        self.assertAlmostEqual(float(canvas_top.group(1)), 0.02)
        self.assertAlmostEqual(float(canvas_height.group(1)), 1.04)
        self.assertIn("ctx.fillRect(x, top, width, height);", self.html)

    def test_dark_highlights_use_luminous_markers_and_dark_text(self) -> None:
        required = (
            "body.theme-dark .tweet-render mark[data-highlight] { color: #0F1419; }",
            "yellow: 'rgba(255, 214, 10, 0.94)'",
            "pink: 'rgba(255, 100, 190, 0.92)'",
            "green: 'rgba(80, 220, 120, 0.90)'",
            "blue: 'rgba(64, 200, 255, 0.90)'",
            "ctx.fillStyle = dark && seg.highlight ? '#0F1419' : fg;",
        )
        for marker in required:
            self.assertIn(marker, self.html)

    def test_highlight_application_clears_native_selection_and_records_undo(self) -> None:
        required = (
            "recordEditorMutation('highlight');",
            "selection.removeAllRanges();",
            "caretRange.collapse(true);",
            "hideHighlightMenu();",
            "bodyEl.focus({ preventScroll: true });",
        )
        for marker in required:
            self.assertIn(marker, self.html)

    def test_export_segments_preserve_graphemes(self) -> None:
        required = (
            "new Intl.Segmenter(undefined, { granularity: 'grapheme' })",
            "function getTextGraphemes(text)",
            "range.setStart(node, grapheme.start);",
            "range.setEnd(node, grapheme.end);",
            "PUSH_CHAR(grapheme.text, isBold, highlightColor, top);",
        )
        for marker in required:
            self.assertIn(marker, self.html)


if __name__ == "__main__":
    unittest.main()
