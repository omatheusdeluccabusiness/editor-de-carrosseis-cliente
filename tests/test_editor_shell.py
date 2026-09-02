from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = (
    PROJECT_ROOT / "templates" / "tweet_editor.html",
    PROJECT_ROOT / "templates" / "stories_editor.html",
)


class EditorShellTest(unittest.TestCase):
    def test_templates_have_a_persistent_interface_theme(self) -> None:
        required = (
            "carrossel-editor-ui-theme-v1",
            'data-ui-theme',
            'id="btn-ui-theme"',
            "function applyUiTheme()",
            "function toggleUiTheme()",
            'html[data-ui-theme="dark"]',
        )
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                for marker in required:
                    self.assertIn(marker, html)

    def test_templates_have_production_workspace_structure(self) -> None:
        required = (
            'class="app-header"',
            'class="production-rail"',
            'id="slide-rail-list"',
            'class="editor-stage"',
            'class="inspector-panel"',
            'class="inspector-section"',
        )
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                for marker in required:
                    self.assertIn(marker, html)

    def test_templates_can_export_the_selected_slide_as_a_single_png(self) -> None:
        tweet = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        stories = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        for html in (tweet, stories):
            self.assertIn('id="btn-download-current"', html)
            self.assertIn("Baixar slide atual", html)
        for marker in (
            "function downloadCurrentTweetSlide()",
            "downloadCurrentTweetSlide",
            "Baixar este slide",
        ):
            self.assertIn(marker, tweet)
        for marker in (
            "function downloadCurrentSlidePNG()",
            "function getActiveStoriesSlideIndex()",
            "captureSlideAsBlob(index)",
            "downloadCurrentSlidePNG",
        ):
            self.assertIn(marker, stories)

    def test_templates_offer_single_or_side_by_side_image_composition(self) -> None:
        tweet = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        stories = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        for html in (tweet, stories):
            for marker in (
                'data-image-composer-mode="single"',
                'data-image-composer-mode="split"',
                "Duas fotos lado a lado",
                "Trocar lados",
                "ou cole aqui",
                "document.addEventListener('paste', event => {",
                "canvas.width = 1600; canvas.height = 900;",
                "imageSmoothingQuality = 'high'",
            ):
                self.assertIn(marker, html)
        for marker in (
            "function openTweetImageComposer",
            "function composeSplitImage",
            "commitTweetImageDataURL(index, dataURL, targetSlide);",
            "const committed = await commitTweetImageDataURL",
            "openTweetImageComposer(i, blob);",
        ):
            self.assertIn(marker, tweet)
        for marker in (
            "function openStoriesImageComposer",
            "function composeStoriesSplitImage",
            "commitInlineImage(stageIndex, dataURL);",
            "const committed = await commitInlineImage",
            "openStoriesImageComposer(activeStageIndex, blob);",
        ):
            self.assertIn(marker, stories)

    def test_templates_use_native_visual_tokens_and_type_roles(self) -> None:
        required = (
            "#F2F2F4",
            "#FFFFFF",
            "#F7F7F8",
            "#1D1D1F",
            "#6E6E73",
            "#D2D2D7",
            "#007AFF",
            "#FF3B30",
            '"SF Pro Text"',
            '"SF Pro Display"',
            "-apple-system",
        )
        rejected = (
            "Barlow Condensed",
            "Source Sans 3",
            "IBM Plex Mono",
            "#F2B705",
        )
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                for marker in required:
                    self.assertIn(marker, html)
                for marker in rejected:
                    self.assertNotIn(marker, html)

    def test_templates_have_native_shell_details(self) -> None:
        required = (
            "font-variant-numeric: tabular-nums",
            "border-left: 3px solid var(--ui-blue)",
            "transition: background-color 150ms ease",
            "{{HUB_SESSION}}",
            'id="btn-back-hub"',
            "function returnToHub()",
        )
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                for marker in required:
                    self.assertIn(marker, html)

    def test_shell_avoids_backdrop_filter_compositor_artifacts(self) -> None:
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                self.assertNotIn("backdrop-filter:", html)

    def test_hidden_shell_buttons_are_removed_from_layout(self) -> None:
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                self.assertIn(".shell-button[hidden] { display: none; }", html)

    def test_shell_uses_quiet_creation_language(self) -> None:
        required = (
            '<span class="rail-heading">Slides</span>',
            '<span class="stage-kicker">Pré-visualização</span>',
            'id="btn-add-slide" class="shell-button"',
        )
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                for marker in required:
                    self.assertIn(marker, html)
                self.assertNotIn(">Roteiro<", html)

    def test_templates_include_responsive_and_accessible_states(self) -> None:
        required = (
            ":focus-visible",
            "prefers-reduced-motion: reduce",
            "max-width: 1100px",
            "max-width: 760px",
            'aria-label="Navegação dos slides"',
        )
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                for marker in required:
                    self.assertIn(marker, html)

    def test_stories_exposes_only_the_two_supported_typefaces(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            'id="stories-typography"',
            'aria-label="Tipografia do carrossel"',
            '<option value="sans">Sem serifa</option>',
            '<option value="advercase">Advercase</option>',
            "font-family: 'Advercase'",
            "src: url('/assets/fonts/Advercase-Regular.otf')",
            "src: url('/assets/fonts/Advercase-Bold.otf')",
            "advercase: {",
            "function getStoriesTypeface()",
            "getStoriesTypeface().canvasFamily",
            "document.documentElement.style.setProperty('--stories-content-font'",
            "function setStoriesTypography(nextTypography, options = {})",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_stories_sans_uses_a_moderate_inline_bold_weight(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            "inlineBoldWeight: 600",
            "inlineBoldWeight: 700",
            "function getStoriesInlineBoldWeight()",
            "font-weight: var(--stories-inline-bold-weight, 700);",
            "getStoriesInlineBoldWeight());",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_stories_uses_the_font_size_slider_as_its_only_size_control(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('data-size-preset=', html)
        self.assertNotIn('SIZE_PRESETS', html)
        self.assertNotIn('setBlockSizePreset', html)
        self.assertIn('id="tb-font-size"', html)

    def test_stories_toolbar_uses_explicit_slider_labels(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        for label in (
            "Entrelinhas",
            "Espaço entre letras",
            "Tamanho do texto",
            "Escurecer foto",
            "Espaço entre blocos",
        ):
            self.assertIn(f'<span class="tb-slider-label">{label}</span>', html)

    def test_stories_typefaces_use_their_editorial_default_spacing(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("const ADVERCASE_DEFAULT_LETTER_SPACING = 0.015;", html)
        self.assertIn("const SANS_DEFAULT_BLOCK_CONFIG = Object.freeze({", html)
        self.assertIn("fontSize: 62,", html)
        self.assertIn("lineHeight: 59,", html)
        self.assertIn("letterSpacing: -0.035,", html)
        self.assertIn("function getTypefaceDefaultLetterSpacing", html)
        self.assertIn("getTypefaceDefaultLetterSpacing(base.letterSpacing)", html)
        self.assertIn("getTypefaceDefaultLetterSpacing(baseSpacing.letterSpacing)", html)

    def test_notes_sans_typeface_uses_the_shared_default_block_config(self) -> None:
        html = (PROJECT_ROOT / "templates" / "notes_editor.html").read_text(
            encoding="utf-8"
        )
        for marker in (
            "const SANS_DEFAULT_BLOCK_CONFIG = Object.freeze({",
            "fontSize: 62,",
            "lineHeight: 59,",
            "letterSpacing: -0.035,",
            "return { ...SANS_DEFAULT_BLOCK_CONFIG };",
            "getTypefaceDefaultLetterSpacing(baseSpacing.letterSpacing)",
        ):
            self.assertIn(marker, html)

    def test_stories_alignment_overrides_the_cover_default_in_preview(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            ".slide.capa [data-block-id].align-left { text-align: left; }",
            ".slide.capa [data-block-id].align-center { text-align: center; }",
            ".slide.capa [data-block-id].align-right { text-align: right; }",
            "function setBlockAlign(blockEl, align)",
            "function resolveBlockAlign(block, isCapa)",
        )
        for marker in required:
            self.assertIn(marker, html)
        for removed_option in (
            '<option value="serif">Serifada</option>',
            '<option value="horsham">Horsham Serial</option>',
            '<option value="garamond-modern">Garamond Modern</option>',
        ):
            self.assertNotIn(removed_option, html)

    def test_stories_offers_global_and_individual_slide_backgrounds(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            'id="global-background-palette"',
            'data-background-color="#000000"',
            'data-background-color="#ffffff"',
            'data-background-color="#cc0001"',
            "function setGlobalBackgroundColor(color)",
            "function setSlideBackgroundColor(index, color)",
            "function getSlideTextColor(slideData)",
            "applySlideBackground(slideEl, slideData);",
            "getSlideBackgroundColor(slideData)",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_templates_build_and_sync_the_slide_rail(self) -> None:
        required = (
            "function buildSlideRail()",
            "function setRailActive(index)",
            "data-rail-index",
            "scrollIntoView",
        )
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                for marker in required:
                    self.assertIn(marker, html)

    def test_html_ids_are_unique_inside_each_template(self) -> None:
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            ids = [
                value
                for value in re.findall(r'\bid="([^"]+)"', html)
                if "$" not in value
            ]
            duplicates = sorted({value for value in ids if ids.count(value) > 1})
            with self.subTest(template=template_path.name):
                self.assertEqual(duplicates, [])

    def test_templates_do_not_expose_numeric_telegram_chat_ids(self) -> None:
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(template=template_path.name):
                self.assertIsNone(
                    re.search(r'id="tg-chat" placeholder="\d{6,}"', html)
                )

    def test_tweet_canvas_scales_with_the_mobile_shell(self) -> None:
        html = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            "function updateTweetPreviewScale()",
            "Math.min(0.5, wrap.clientWidth / W)",
            "render.style.transform = 'scale(' + scale + ')'",
            "window.addEventListener('resize', updateTweetPreviewScale)",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_tweet_header_shows_only_the_model_name(self) -> None:
        html = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        identity = re.search(
            r'<div class="app-identity">(.*?)</div>\s*<div class="app-actions">',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(identity)
        identity_html = identity.group(1)
        self.assertIn("<h1>Modelo Tweet</h1>", identity_html)
        self.assertNotIn("doc-meta", identity_html)
        self.assertNotIn("{{TITLE}}", identity_html)

    def test_stories_header_shows_only_the_model_name(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        identity = re.search(
            r'<div class="app-identity">(.*?)</div>\s*<div class="app-actions">',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(identity)
        identity_html = identity.group(1)
        self.assertIn("<h1>Modelo Stories</h1>", identity_html)
        self.assertNotIn("{{TITLE}}", identity_html)

    def test_stories_inline_copy_and_image_share_one_ordered_flow(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        # Preview and PNG must keep one gap between visual items and support
        # moving a text block through the inline image.
        self.assertIn("function getInlineImagePosition(inlineImage, blockCount)", html)
        self.assertIn("items.splice(getInlineImagePosition(inlineImage, blockLayouts.length), 0, { type: 'image' });", html)
        self.assertIn("function commitVisualItems(slideData, items)", html)
        self.assertIn("slideData.inlineImage.position = imageIndex;", html)
        self.assertIn("const inlineImagePosition = getInlineImagePosition(slideData.inlineImage, slideData.blocks.length);", html)
        self.assertNotIn("margin-bottom: var(--block-gap, 36px);", html)
        self.assertNotIn("margin-top: auto;", html)

    def test_pasted_stories_image_renders_without_a_theme_toggle(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        commit_image = re.search(
            r"async function commitInlineImage\(stageIndex, dataURL\) \{(.*?)\n  \}",
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(commit_image)
        self.assertIn("const currentIndex = doc.slides.indexOf(targetSlide);", commit_image.group(1))
        self.assertIn("renderSlide(currentIndex);", commit_image.group(1))

    def test_both_templates_offer_a_confirmed_carousel_restart(self) -> None:
        confirmation = (
            "Você quer reiniciar esse template e começar outro do zero? "
            "Se sim, certifique-se de ter exportado os slides antes"
        )
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            with self.subTest(editor=template_path.name):
                self.assertIn('id="btn-restart-carousel"', html)
                self.assertIn("Reiniciar carrossel", html)
                self.assertIn(confirmation, html)
                self.assertIn("function restartCarousel()", html)

    def test_carousel_restart_is_a_visible_header_action_not_maintenance(self) -> None:
        for template_path in TEMPLATES:
            html = template_path.read_text(encoding="utf-8")
            header = re.search(r"<header class=\"app-header\">(.*?)</header>", html, re.DOTALL)
            maintenance = re.search(
                r'<details class="maintenance">(.*?)</details>', html, re.DOTALL
            )
            with self.subTest(editor=template_path.name):
                self.assertIsNotNone(header)
                self.assertIsNotNone(maintenance)
                self.assertIn('id="btn-restart-carousel"', header.group(1))
                self.assertNotIn('id="btn-restart-carousel"', maintenance.group(1))

    def test_restart_contract_resets_content_but_preserves_user_profile(self) -> None:
        tweet = TEMPLATES[0].read_text(encoding="utf-8")
        stories = TEMPLATES[1].read_text(encoding="utf-8")
        self.assertIn("function createBlankTweetSlides()", tweet)
        self.assertIn("text: 'adicione aqui a sua copy'", tweet)
        self.assertIn("imageDataURL: null", tweet)
        self.assertNotIn("profileState =", tweet[tweet.index("function restartCarousel()"):])
        self.assertIn("function createBlankStoriesDocument()", stories)
        self.assertIn("inlineImage: null", stories)
        self.assertIn("image: null", stories)

    def test_tweet_inspector_exposes_profile_controls(self) -> None:
        html = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            '<span class="inspector-title">Perfil</span>',
            'id="profile-avatar-preview"',
            'id="profile-avatar-input"',
            'accept="image/*"',
            'for="profile-name"',
            'id="profile-name"',
            'for="profile-handle"',
            'id="profile-handle"',
        )
        for marker in required:
            self.assertIn(marker, html)
        self.assertLess(html.index(">Perfil<"), html.index(">Documento<"))

    def test_tweet_profile_is_persistent_and_shared_by_preview_and_export(self) -> None:
        html = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            "const PROFILE_STORAGE_KEY = 'tweet-editor-profile-v1'",
            "function normalizeHandle(value)",
            "function loadProfileState()",
            "function saveProfileState()",
            "function syncProfileDOM()",
            "safeStorageGet(PROFILE_STORAGE_KEY)",
            "safeStorageSet(PROFILE_STORAGE_KEY",
            "name: profileState.name",
            "handle: profileState.handle",
            "escapeHtml(profileState.name)",
            "escapeHtml('@' + profileState.handle)",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_tweet_profile_avatar_supports_persistent_manual_cropping(self) -> None:
        html = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            "function normalizeAvatarFile(file)",
            "const hasKnownImageExtension",
            "const reader = new FileReader()",
            "reader.readAsDataURL(file)",
            "const maxSide = 1600",
            "canvas.toDataURL('image/jpeg', 0.88)",
            "function normalizeAvatarCrop(value)",
            "avatarCrop: { scale: 1, x: 0, y: 0 }",
            "id=\"avatar-crop-modal\"",
            "function openAvatarCropper(dataUrl",
            "function wireAvatarCropper()",
            "pointerdown",
            "pendingAvatarCrop = { ...pendingAvatarCrop, ...normalizeAvatarCrop(pendingAvatarCrop) };",
            "profileState.avatarCrop = normalizeAvatarCrop(crop)",
            "const crop = normalizeAvatarCrop(profileState.avatarCrop)",
            "profileState.avatar = dataUrl",
            "setSendStatus('Não foi possível carregar esta foto.', 'error')",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_tweet_handle_uses_only_the_container_focus_ring(self) -> None:
        html = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        override = (
            ".profile-handle-field .profile-input:focus,\n"
            "  .profile-handle-field .profile-input:focus-visible {\n"
            "    background: transparent; box-shadow: none; outline: none;\n"
            "  }"
        )
        self.assertIn(override, html)
        self.assertGreater(
            html.index(override),
            html.index(":where(button, textarea, input, summary):focus-visible"),
        )

    def test_stories_toolbar_stays_hidden_until_a_block_is_selected(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("#block-toolbar.empty { display: none; }", html)

    def test_stories_toolbar_uses_the_inspector_instead_of_covering_the_canvas(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="block-toolbar-dock"', html)
        self.assertIn('toolbarDock.append(blockToolbar);', html)
        self.assertIn("#block-toolbar {\n    position: relative;", html)
        self.assertIn('<aside class="inspector-panel" aria-label="Propriedades do carrossel">\n    <div id="block-toolbar-dock"', html)
        self.assertNotIn("#block-toolbar { top: 76px;", html)
        self.assertIn("block: 'center', inline: 'nearest'", html)

    def test_stories_inline_images_keep_their_source_ratio_and_offer_manual_resize(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            "function getInlineImageLayout(zoneW, zoneH, inlineImage)",
            "aspectRatio",
            "inlineImage.size",
            "--inline-aspect",
            "--inline-width",
            "className = 'inline-photo-controls'",
            "input.type = 'range'",
            "input.setAttribute('aria-label', 'Redimensionar imagem')",
            "requestAnimationFrame(() =>",
            "resizeInput.onchange = () => commitResize();",
            "className = 'inline-photo-media'",
            "const scale = getInlineImageSize(inlineImage) / 100;",
            "const width = fittedWidth * scale;",
            "node.style.removeProperty('--inline-scale');",
            "refreshSlideContentFit(stageIndex);",
            "await drawInlinePhoto(ctx, inlineImage, zoneX + inlineLayout.x, cursorY, inlineLayout.width, inlineLayout.height, inlineLayout.scale);",
            "object-fit: contain",
            "await loadImage(dataURL)",
            "function normalizeInlineImageDataURL(dataURL, image)",
            "canvas.toDataURL('image/jpeg', 0.9)",
            "dataURL: normalized.dataURL",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_tweet_has_a_global_font_size_control_for_every_slide(self) -> None:
        html = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            'id="tweet-global-font-size"',
            'Tamanho do texto',
            'Aplica o mesmo tamanho a todos os slides deste carrossel.',
            "const TWEET_FONT_SIZE_STORAGE_KEY",
            "if (raw === null) return 42;",
            "function setGlobalTweetFontSize(value, options = {})",
            "slidesState.forEach((slide) => { slide.fontSize = size; });",
            "function setSlideTweetFontSize(index, value, options = {})",
            "document.getElementById('slide-font-size-value-' + index)",
            "if (output) output.value = size + ' px';",
            "Tamanho da copy",
            "data-slide-font-size",
            "const TWEET_COPY_LINE_HEIGHT = 1.10;",
            "line-height: var(--tweet-copy-line-height);",
            "const lineHeight = fontSize * TWEET_COPY_LINE_HEIGHT;",
            "function setupGlobalTweetFontSizeControl()",
            "setupGlobalTweetFontSizeControl();",
            "fontSize: currentTweetFontSize",
        )
        for marker in required:
            self.assertIn(marker, html)
        self.assertNotIn("transform: scale(var(--inline-scale, 1));", html)
        self.assertNotIn(".slide.capa .inline-photo { aspect-ratio: 4 / 3; }", html)
        self.assertNotIn("else safeSet(DOC_KEY, doc);", html)

    def test_tweet_uses_arial_in_preview_and_png_export(self) -> None:
        html = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("font-family: Arial, sans-serif;", html)
        self.assertIn("font-weight: 400;", html)
        self.assertIn("ctx.font = `400 ${fontSize}px ${fontFamily}`;", html)
        self.assertIn("${seg.bold ? '700 ' : '400 '}${fontSize}px ${fontFamily}", html)
        self.assertIn("const fontFamily = 'Arial, sans-serif';", html)
        self.assertIn("margin-top: 8px;", html)
        self.assertIn("ctx.fillText('@' + handle, nameX, startY + 62);", html)
        self.assertNotIn('"Helvetica Neue", Helvetica, Arial, sans-serif', html)

    def test_stories_canvas_isolates_transformed_slide_paint(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("contain: paint;", html)

    def test_stories_background_clips_each_composition_photo_in_its_own_frame(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_background_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            ".photo-frame { position: absolute; overflow: hidden;",
            "composition-frame-first",
            "composition-frame-second",
            "function getCompositionPhotoImg(photo, slot)",
            "frame.appendChild(img);",
            "function clearCompositionPhotoImages(photo)",
            "photo.querySelectorAll('.photo-frame.composition-frame').forEach(frame => frame.remove());",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_stories_background_photo_tone_is_shared_by_preview_and_export(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_background_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            'data-photo-tone="color"',
            'data-photo-tone="grayscale"',
            "function getPhotoTone(slide)",
            "function applyPhotoToneToSlide(slideEl, tone)",
            "filter: grayscale(var(--photo-grayscale, 0));",
            "applyPhotoToneToSlide(slideEl, getPhotoTone(slideData));",
            "ctx.filter = 'grayscale(1)'",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_stories_background_halo_and_grain_effect_is_shared_by_preview_and_export(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_background_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            'data-photo-effect="clean"',
            'data-photo-effect="halo-grain"',
            "Borrado radial",
            "function getPhotoEffect(slide)",
            "function applyPhotoEffectToSlide(slideEl, effect)",
            "has-halo-grain",
            "photo-radial-effect",
            "function schedulePhotoEffectPreview(stageIndex)",
            "function drawFilmGrain(ctx, w, h, seedValue)",
            "async function drawHaloGrainEffect(ctx, imageData, w, h, tone, seedValue",
            "function renderRadialBlurWithWebGL(source, w, h, options)",
            "const int SAMPLE_COUNT = 36;",
            "float edgeMask = smoothstep(innerRadius, innerRadius + 0.24, distanceFromFocus);",
            "float angularSweep = mix(0.025, 0.92, u_strength) * edgeMask;",
            "vec2 rotatedMetric = vec2(metric.x * cosine - metric.y * sine, metric.x * sine + metric.y * cosine);",
            'id="tb-photo-effect-strength"',
            'id="tb-photo-effect-radius"',
            'data-action="photo-effect-focus"',
            "getPhotoEffect(slideData) === 'halo-grain'",
        )
        for marker in required:
            self.assertIn(marker, html)
        self.assertNotIn("float travel = progress * blurDistance;", html)
        self.assertNotIn("curvedDelta * (1.0 - travel)", html)

    def test_stories_background_supports_the_shared_sans_typography_preset(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_background_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            '<option value="sans">Sem serifa</option>',
            "const SANS_DEFAULT_BLOCK_CONFIG = Object.freeze({",
            "fontSize: 62,",
            "lineHeight: 59,",
            "letterSpacing: -0.035,",
            "if (!doc || doc.typography !== 'advercase') {",
            "return { ...SANS_DEFAULT_BLOCK_CONFIG };",
            "inlineBoldWeight: 600,",
            "function getStoriesInlineBoldWeight()",
            "const typography = STORIES_TYPEFACES[nextTypography] ? nextTypography : 'advercase';",
            "const baseSpacing = getVariantBaseSpacing(block.kind, block.variant);",
            "lineHeight = Math.round(size * (baseSpacing.lineHeight / baseSpacing.fontSize));",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_stories_background_rail_colors_remain_visible_without_a_photo(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_background_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            ".slide .photo { display: block !important; z-index: 0; background: transparent; }",
            ".photo:not(.has-background-image)::before { background: transparent; }",
            "function hasStoriesBackgroundImage(slideData)",
            "photo.classList.add('has-background-image');",
            "photo.classList.remove('has-background-image');",
            "if (hasStoriesBackgroundImage(slideData)) {\n      drawLegibilityFilter",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_stories_background_keeps_the_canvas_stable_while_editing_copy(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_background_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            "overflow-anchor: none;",
            "function preserveStageViewportPosition(stageIndex, operation)",
            "const topBefore = stage ? stage.getBoundingClientRect().top : null;",
            "window.scrollBy(0, delta);",
            "preserveStageViewportPosition(ctx.sIdx, () => {",
        )
        for marker in required:
            self.assertIn(marker, html)

    def test_stories_background_supports_individual_vertical_block_offsets(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_background_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            "transform: translateY(var(--block-offset-y, 0px));",
            "function getBlockVerticalOffset(block)",
            "function persistBlockVerticalOffset(blockEl)",
            "let blockDragging = false, blockDragStart = null, draggingBlock = null;",
            "targetBlock = e.target.closest",
            "applyBlockVerticalOffsetToNode(draggingBlock, offsetY);",
            "const blockY = cursorY + getBlockVerticalOffset(layout.block);",
        )
        for marker in required:
            self.assertIn(marker, html)


if __name__ == "__main__":
    unittest.main()
