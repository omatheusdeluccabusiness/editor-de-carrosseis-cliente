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


if __name__ == "__main__":
    unittest.main()
