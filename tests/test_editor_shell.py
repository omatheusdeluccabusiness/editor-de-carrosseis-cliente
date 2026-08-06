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

    def test_tweet_profile_avatar_is_cropped_and_compressed(self) -> None:
        html = (PROJECT_ROOT / "templates" / "tweet_editor.html").read_text(
            encoding="utf-8"
        )
        required = (
            "function normalizeAvatarFile(file)",
            "URL.createObjectURL(file)",
            "Math.min(img.naturalWidth, img.naturalHeight)",
            "canvas.width = 512",
            "canvas.height = 512",
            "canvas.toDataURL('image/jpeg', 0.88)",
            "URL.revokeObjectURL(objectUrl)",
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

    def test_stories_canvas_isolates_transformed_slide_paint(self) -> None:
        html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("contain: paint;", html)


if __name__ == "__main__":
    unittest.main()
