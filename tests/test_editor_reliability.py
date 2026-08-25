from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORIES = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(encoding="utf-8")
TWEET = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(encoding="utf-8")


class StoriesLayoutReliabilityTest(unittest.TestCase):
    def test_slide_rail_supports_drag_reordering(self) -> None:
        required = (
            'item.draggable = true;',
            'function moveStoriesSlide(fromIndex, targetIndex, placeAfter)',
            "item.addEventListener('dragstart'",
            "control.addEventListener('drop'",
            "event.clientY > rect.top + rect.height / 2",
            "location.reload();",
        )
        for marker in required:
            self.assertIn(marker, STORIES)

    def test_new_slide_is_appended_after_the_cta(self) -> None:
        self.assertIn("const isCTA = slideEl.classList.contains('cta-final');", STORIES)
        self.assertIn("function getSlideLabel(slide, index)", STORIES)
        self.assertIn("const insertAt = doc.slides.length;", STORIES)
        self.assertIn("doc.slides.push(newSlide);", STORIES)
        self.assertIn("d.version = 12;", STORIES)
        self.assertIn("rebuildDOMFromDoc();", STORIES)

    def test_text_size_is_never_silently_auto_fitted(self) -> None:
        self.assertIn("function applySpacingToNode(node, block, contentFit = 1)", STORIES)
        self.assertIn("node.style.fontSize = (eff.fontSize * contentFit) + 'px';", STORIES)
        self.assertIn("node.style.lineHeight = (eff.lineHeight * contentFit) + 'px';", STORIES)
        self.assertIn("applySpacingToNode(node, block, 1);", STORIES)
        self.assertIn("const overflow = hasSlideCanvasOverflow(bodyZone, items);", STORIES)
        self.assertIn("function hasSlideCanvasOverflow(bodyZone, items)", STORIES)
        self.assertIn("const canvasBounds = slideEl.getBoundingClientRect();", STORIES)
        self.assertIn("bounds.bottom > canvasBounds.bottom + tolerance", STORIES)
        self.assertIn("return 1;", STORIES)

    def test_every_layout_mutation_rechecks_overflow_without_rescaling_text(self) -> None:
        # Os sliders agrupam a persistência e verificam excesso ao fim do
        # arraste, mas nunca substituem o valor escolhido por um auto-fit.
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

    def test_live_slider_preview_uses_the_exact_selected_size(self) -> None:
        self.assertIn("function applyLiveSpacingToNode(node, block)", STORIES)
        self.assertIn("applySpacingToNode(node, block, 1);", STORIES)
        self.assertIn("O slider precisa representar exatamente o valor escolhido.", STORIES)
        self.assertGreaterEqual(STORIES.count("applyLiveSpacingToNode(blockEl, ctx.block);"), 3)

    def test_export_recomputes_layout_and_rejects_unreadable_overflow(self) -> None:
        self.assertIn("const contentFit = getFallbackContentFitScale", STORIES)
        self.assertIn("refreshSlideContentFit(stageIndex);", STORIES)
        self.assertIn("body-zone.content-overflow", STORIES)
        self.assertNotIn("getPreviewContentFitScale", STORIES)

    def test_stories_png_export_captures_the_full_document_in_one_archive(self) -> None:
        self.assertIn("const total = doc.slides.length;", STORIES)
        self.assertIn("localApiFetch('/api/export/pngs'", STORIES)
        self.assertIn("carrossel-pngs.zip", STORIES)

    def test_stories_ratio_controls_update_preview_and_canvas_export_together(self) -> None:
        required = (
            "const STORIES_RATIO_HEIGHTS = { '4:5': 1350, '3:4': 1440 };",
            'data-stories-ratio="3:4"',
            'function applyStoriesRatio(options = {})',
            "document.documentElement.style.setProperty('--stories-h', height + 'px');",
            "canvas.height = SLIDE_H * dpr;",
            "d.ratio = normalizeStoriesRatio(d.ratio);",
        )
        for marker in required:
            self.assertIn(marker, STORIES)

    def test_image_commits_are_ordered_and_rich_paste_is_sanitized(self) -> None:
        self.assertIn("const inlineImageCommitRevisions = new Map();", STORIES)
        self.assertIn("inlineImageCommitRevisions.get(targetSlide) !== revision", STORIES)
        self.assertIn("const currentIndex = doc.slides.indexOf(targetSlide);", STORIES)
        self.assertIn("function sanitizeBlockHtml(html)", STORIES)
        self.assertIn("clipboard.getData('text/plain')", STORIES)


class TweetReliabilityTest(unittest.TestCase):
    def test_tweet_slide_rail_supports_drag_reordering_without_image_mixup(self) -> None:
        required = (
            'item.draggable = true;',
            'function moveTweetSlide(fromIndex, targetIndex, placeAfter)',
            'slideImageCache.clear();',
            'imageCommitRevisions.clear();',
            "item.addEventListener('drop'",
        )
        for marker in required:
            self.assertIn(marker, TWEET)

    def test_new_tweet_slide_is_appended_without_reload(self) -> None:
        self.assertIn("function normalizeTweetSlides(slides)", TWEET)
        self.assertIn("const insertAt = slidesState.length;", TWEET)
        self.assertIn("slidesState.push({", TWEET)
        self.assertIn("refreshTweetAfterStructureChange(insertAt);", TWEET)

    def test_images_are_normalized_and_stale_async_commits_are_discarded(self) -> None:
        self.assertIn("function normalizeSlideImage(dataURL)", TWEET)
        self.assertIn("canvas.toDataURL('image/webp', 0.88)", TWEET)
        self.assertIn("const imageCommitRevisions = new Map();", TWEET)
        self.assertIn("imageCommitRevisions.get(revisionKey) !== revision", TWEET)
        self.assertIn("const targetIndex = targetSlide ? slidesState.indexOf(targetSlide) : i;", TWEET)

    def test_paste_is_handled_once_and_storage_failure_is_visible(self) -> None:
        self.assertIn("if (e.defaultPrevented) return;", TWEET)
        self.assertGreaterEqual(TWEET.count("e.stopPropagation();"), 2)
        self.assertIn("const persisted = safeStorageSet", TWEET)
        self.assertIn("não foi possível salvar · exporte antes de fechar", TWEET)

    def test_tweet_overflow_is_fitted_or_blocked_before_delivery(self) -> None:
        self.assertIn("bodyEl.dataset.contentFitScale = String(contentFit);", TWEET)
        self.assertIn("card.classList.toggle('content-overflow'", TWEET)
        self.assertIn("card.classList.contains('content-overflow')", TWEET)

    def test_tweet_png_export_captures_the_full_document_in_one_archive(self) -> None:
        self.assertIn("const total = slidesState.length;", TWEET)
        self.assertIn("localApiFetch('/api/export/pngs'", TWEET)
        self.assertIn("carrossel-pngs.zip", TWEET)


if __name__ == "__main__":
    unittest.main()
