from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "tweet": (ROOT / "templates" / "tweet_editor.html").read_text(encoding="utf-8"),
    "stories": (ROOT / "templates" / "stories_editor.html").read_text(encoding="utf-8"),
}


class EditorUndoContractTest(unittest.TestCase):
    def test_both_production_editors_expose_the_same_undo_contract(self) -> None:
        required = (
            "const UNDO_LIMIT = 50;",
            "function createUndoController(options)",
            "function recordEditorMutation(reason)",
            "function undoEditorAction()",
            "function armEditorUndo()",
            "sessionStorage",
            "undoStack.shift()",
            "(e.metaKey || e.ctrlKey)",
            "e.key.toLowerCase() !== 'z'",
            "if (!undoEditorAction()) return;",
            "e.preventDefault()",
            "setUndoFeedback('Ação desfeita')",
        )
        for editor, html in TEMPLATES.items():
            with self.subTest(editor=editor):
                for marker in required:
                    self.assertIn(marker, html)

    def test_tweet_snapshot_covers_all_local_editor_surfaces(self) -> None:
        html = TEMPLATES["tweet"]
        required = (
            "function captureTweetSnapshot()",
            "slides: snapshotSlides",
            "profile: snapshotProfile",
            "theme: currentTheme",
            "ratio: currentRatio",
            "caption: captionEl ? captionEl.value : ''",
            "function restoreTweetSnapshot(snapshot)",
            "slidesState.length !== snapshot.slides.length",
            "safeStorageSet(STORAGE_KEY, JSON.stringify(slidesState))",
            "safeStorageSet(PROFILE_STORAGE_KEY, JSON.stringify(profileState))",
            "safeStorageSet('matheusao-carrossel-theme', currentTheme)",
            "safeStorageSet('matheusao-tweet-ratio', currentRatio)",
            "location.reload()",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_tweet_persistence_paths_record_mutations(self) -> None:
        html = TEMPLATES["tweet"]
        required = (
            "recordEditorMutation('slides')",
            "recordEditorMutation('profile')",
            "recordEditorMutation('theme')",
            "recordEditorMutation('ratio')",
            "recordEditorMutation('caption')",
        )
        for marker in required:
            self.assertIn(marker, html)
        self.assertNotIn("? Sem desfazer.", html)

    def test_stories_snapshot_covers_document_theme_and_caption(self) -> None:
        html = TEMPLATES["stories"]
        required = (
            "function captureStoriesSnapshot()",
            "document: snapshotDoc",
            "theme: isLightTheme() ? 'light' : 'dark'",
            "caption: captionEl ? captionEl.value : ''",
            "function restoreStoriesSnapshot(snapshot)",
            "doc.slides.length !== snapshot.document.slides.length",
            "safeSet(DOC_KEY, doc)",
            "applyStoriesTheme(snapshot.theme)",
            "renderAll()",
            "buildSlideRail()",
            "location.reload()",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_stories_persistence_paths_record_mutations(self) -> None:
        html = TEMPLATES["stories"]
        required = (
            "recordEditorMutation('document')",
            "recordEditorMutation('theme')",
            "recordEditorMutation('caption')",
        )
        for marker in required:
            self.assertIn(marker, html)
        self.assertNotIn("? Sem desfazer.", html)

if __name__ == "__main__":
    unittest.main()
