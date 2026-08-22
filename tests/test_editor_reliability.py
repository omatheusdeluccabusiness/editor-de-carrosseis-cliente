from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORIES = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(encoding="utf-8")
TWEET = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(encoding="utf-8")


class StoriesLayoutReliabilityTest(unittest.TestCase):
    def test_auto_fit_preserves_the_text_column_width(self) -> None:
        self.assertIn("function applySpacingToNode(node, block, contentFit = 1)", STORIES)
        self.assertIn("node.style.fontSize = (eff.fontSize * contentFit) + 'px';", STORIES)
        self.assertIn("node.style.lineHeight = (eff.lineHeight * contentFit) + 'px';", STORIES)
        self.assertIn("bz.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;", STORIES)
        self.assertNotIn("scale(${scale * contentFit})", STORIES)

    def test_every_layout_mutation_invalidates_the_fit(self) -> None:
        # Os sliders de tipografia agrupam o encaixe ao fim do arraste para
        # manter a interação fluida, mas ainda encaminham cada mutação ao fit.
        self.assertGreaterEqual(STORIES.count("scheduleSlideContentFit(ctx.sIdx);"), 3)
        self.assertIn("queueTextLayoutCommit(ctx.sIdx);", STORIES)
        self.assertIn("refreshSlideContentFit(stageIndex);", STORIES)
        self.assertIn("renderSlide(stageIndex);", STORIES)
        self.assertIn("document.fonts.addEventListener('loadingdone'", STORIES)

    def test_font_size_restores_proportional_line_height_without_drag_jank(self) -> None:
        self.assertIn(
            "Alterar o tamanho volta a usar o ritmo proporcional da variante.",
            STORIES,
        )
        self.assertIn("delete ctx.block.lineHeight;", STORIES)
        self.assertIn("lhInput.value = next.lineHeight;", STORIES)
        self.assertIn(
            "size * (baseStyle.lineHeight / baseStyle.size)",
            STORIES,
        )
        self.assertIn("function queueTextLayoutCommit(stageIndex)", STORIES)
        self.assertIn("queueTextLayoutCommit(ctx.sIdx);", STORIES)

    def test_live_slider_preview_keeps_the_current_content_fit(self) -> None:
        self.assertIn("function applyLiveSpacingToNode(node, block)", STORIES)
        self.assertIn("getContentFitScale(bodyZone)", STORIES)
        self.assertGreaterEqual(STORIES.count("applyLiveSpacingToNode(blockEl, ctx.block);"), 3)

    def test_export_recomputes_layout_and_rejects_unreadable_overflow(self) -> None:
        self.assertIn("const contentFit = getFallbackContentFitScale", STORIES)
        self.assertIn("refreshSlideContentFit(stageIndex);", STORIES)
        self.assertIn("body-zone.content-overflow", STORIES)
        self.assertNotIn("getPreviewContentFitScale", STORIES)

    def test_image_commits_are_ordered_and_rich_paste_is_sanitized(self) -> None:
        self.assertIn("const inlineImageCommitRevisions = new Map();", STORIES)
        self.assertIn("inlineImageCommitRevisions.get(stageIndex) !== revision", STORIES)
        self.assertIn("function sanitizeBlockHtml(html)", STORIES)
        self.assertIn("clipboard.getData('text/plain')", STORIES)


class TweetReliabilityTest(unittest.TestCase):
    def test_images_are_normalized_and_stale_async_commits_are_discarded(self) -> None:
        self.assertIn("function normalizeSlideImage(dataURL)", TWEET)
        self.assertIn("canvas.toDataURL('image/webp', 0.88)", TWEET)
        self.assertIn("const imageCommitRevisions = new Map();", TWEET)
        self.assertIn("imageCommitRevisions.get(i) !== revision", TWEET)

    def test_paste_is_handled_once_and_storage_failure_is_visible(self) -> None:
        self.assertIn("if (e.defaultPrevented) return;", TWEET)
        self.assertGreaterEqual(TWEET.count("e.stopPropagation();"), 2)
        self.assertIn("const persisted = safeStorageSet", TWEET)
        self.assertIn("não foi possível salvar · exporte antes de fechar", TWEET)

    def test_tweet_overflow_is_fitted_or_blocked_before_delivery(self) -> None:
        self.assertIn("bodyEl.dataset.contentFitScale = String(contentFit);", TWEET)
        self.assertIn("card.classList.toggle('content-overflow'", TWEET)
        self.assertIn("card.classList.contains('content-overflow')", TWEET)


if __name__ == "__main__":
    unittest.main()
