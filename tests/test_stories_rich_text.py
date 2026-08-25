from __future__ import annotations

import unittest
from pathlib import Path


HTML = (Path(__file__).resolve().parent.parent / "templates" / "stories_editor.html").read_text(
    encoding="utf-8"
)


class StoriesRichTextContractTest(unittest.TestCase):
    def test_coloring_a_selection_keeps_its_existing_inline_formatting(self) -> None:
        """Red/yellow color must wrap the selected DOM, never replace it with plain text."""
        self.assertIn("function applyHotToSavedSelection(yellow)", HTML)
        self.assertIn("const contents = range.extractContents();", HTML)
        self.assertIn("marker.appendChild(contents);", HTML)
        self.assertNotIn("const safeText = text.replace", HTML)

    def test_canvas_parser_recognizes_semantic_and_inline_style_formatting(self) -> None:
        """Native contenteditable output must retain bold and italic in PNG exports."""
        self.assertIn("function nodeHasInlineStyle(node, property, predicate)", HTML)
        self.assertIn("nodeHasInlineStyle(node, 'fontStyle'", HTML)
        self.assertIn("nodeHasInlineStyle(node, 'fontWeight'", HTML)

    def test_selection_menu_exposes_reliable_bold_and_italic_actions(self) -> None:
        """Formatting selected text must not depend on browser-specific shortcuts."""
        self.assertIn('data-action="format-bold"', HTML)
        self.assertIn('data-action="format-italic"', HTML)
        self.assertIn("function applyInlineFormat(command)", HTML)

    def test_hot_text_uses_the_requested_red_and_yellow_in_dom_and_png(self) -> None:
        self.assertIn(".hot { color: #d70611;", HTML)
        self.assertIn(".hot.yellow { color: #f8ce07;", HTML)
        self.assertIn("word.hotYellow ? '#f8ce07' : '#d70611'", HTML)

    def test_recoloring_reuses_existing_hot_marker_and_canvas_reads_inner_color(self) -> None:
        self.assertIn("function selectedRangeMatchesHotMarker(range)", HTML)
        self.assertIn("marker.className = yellow ? 'hot yellow' : 'hot';", HTML)
        self.assertIn("hotYellow: node.classList.contains('yellow')", HTML)
        self.assertNotIn("ctx.hotYellow || node.classList.contains('yellow')", HTML)

    def test_hot_markers_do_not_change_text_metrics_or_stay_nested(self) -> None:
        required = (
            "function normalizeHotMarker(marker)",
            "marker.querySelectorAll('.hot')",
            "normalizeHotMarker(marker);",
            "font-size: inherit;",
            "letter-spacing: inherit;",
            "word-spacing: inherit;",
            "white-space: inherit;",
            "vertical-align: baseline;",
        )
        for marker in required:
            self.assertIn(marker, HTML)

    def test_canvas_uses_one_layout_for_measurement_and_drawing_at_export_resolution(self) -> None:
        required = (
            "function buildBlockLayouts(ctx, blocks, zoneW, isCapa, contentFit = 1, textColor = null)",
            "const blockLayouts = buildBlockLayouts(ctx, blocks, zoneW, isCapa, contentFit, textColor);",
            "function drawBlockAt(layout, cursorY)",
            "layout.height",
            "const dpr = 2;",
            "canvas.width = SLIDE_W * dpr;",
            "canvas.height = SLIDE_H * dpr;",
            "ctx.imageSmoothingQuality = 'high';",
        )
        for marker in required:
            self.assertIn(marker, HTML)
        self.assertNotIn("CAPA_HDISPLAY_OVERRIDE", HTML)
        self.assertNotIn("CAPA_LEDE_OVERRIDE", HTML)

    def test_canvas_preserves_the_preview_line_breaks(self) -> None:
        """Canvas export has to honor the browser composition seen in preview."""
        required = (
            "function wrapTokensWithNativeLayout(tokens, maxW, style)",
            "const nativeLines = wrapTokensWithNativeLayout(tokens, maxW, style);",
            "font-kerning:auto",
            "font-variant-ligatures:normal",
            "const top = span.getBoundingClientRect().top;",
        )
        for marker in required:
            self.assertIn(marker, HTML)

    def test_added_blocks_are_fitted_in_preview_and_png(self) -> None:
        """A new block must never make the shared text/image stack overflow the slide."""
        required = (
            "function fitBodyZoneContent(bodyZone)",
            "function refreshSlideContentFit(stageIndex)",
            "refreshSlideContentFit(ctx.sIdx);",
            "function getFallbackContentFitScale(ctx, slideData, zoneW, zoneH, isCapa, gap)",
            "const contentFit = getFallbackContentFitScale(ctx, slideData, zoneW, zoneH, !!isCapa, gap);",
            "ctx.scale(bz.scale, bz.scale);",
            "function hasSlideCanvasOverflow(bodyZone, items)",
            "node.style.fontSize = (eff.fontSize * contentFit) + 'px';",
            "bodyZone.style.setProperty('--content-fit-gap'",
        )
        for marker in required:
            self.assertIn(marker, HTML)
        self.assertNotIn("getPreviewContentFitScale", HTML)
        self.assertNotIn("ctx.scale(bz.scale * contentFit", HTML)


if __name__ == "__main__":
    unittest.main()
