from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import re

from scripts.hub_sessions import (
    cleanup_hub_sessions,
    create_hub_session,
    refresh_hub_session,
)
from scripts.novo_carrossel import CONTENT_DIR


class HubSessionsTest(unittest.TestCase):
    def test_creates_unique_html_without_project_draft(self) -> None:
        before = set(CONTENT_DIR.glob("*.md"))
        with tempfile.TemporaryDirectory() as tmp:
            first = create_hub_session("tweet", Path(tmp))
            second = create_hub_session("tweet", Path(tmp))

            self.assertNotEqual(first.id, second.id)
            self.assertTrue(first.path.is_file())
            self.assertEqual(first.url, f"/{first.path.name}")
            self.assertEqual(list(Path(tmp).glob("*.md")), [])
        self.assertEqual(set(CONTENT_DIR.glob("*.md")), before)

    def test_generated_stories_session_has_ten_slides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = create_hub_session("stories", Path(tmp))
            html = session.path.read_text(encoding="utf-8")

        self.assertIn("10 slides", html)

    def test_generated_background_stories_session_uses_editorial_background_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = create_hub_session("stories-fundo", Path(tmp))
            html = session.path.read_text(encoding="utf-8")

        self.assertIn("Stories C/ Fundo", html)
        self.assertIn("commitFullBleedImage", html)
        self.assertIn("data-card=\"light\"", html)

    def test_generated_notes_session_uses_notes_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = create_hub_session("notes", Path(tmp))
            html = session.path.read_text(encoding="utf-8")

        self.assertIn("Bloco de Notas", html)
        self.assertIn("notes-editor", html)

    def test_refresh_keeps_hub_document_key_and_replaces_template_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = create_hub_session("stories", root)
            before = session.path.read_text(encoding="utf-8")
            doc_key = re.search(r"const DOC_KEY = '([^']+)'", before).group(1)
            # Representa um HTML aberto antes de uma atualização de template.
            session.path.write_text("versão antiga", encoding="utf-8")

            refreshed = refresh_hub_session(session.id, root)
            after = refreshed.path.read_text(encoding="utf-8")

        self.assertEqual(refreshed.id, session.id)
        self.assertIn(f"const DOC_KEY = '{doc_key}'", after)
        self.assertIn("Modelo Stories", after)

    def test_cleanup_removes_only_hub_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub = root / "hub-tweet-deadbeef.html"
            manual = root / "meu-rascunho.html"
            hub.write_text("hub", encoding="utf-8")
            manual.write_text("manual", encoding="utf-8")

            removed = cleanup_hub_sessions(root)

            self.assertEqual(removed, [hub])
            self.assertTrue(manual.exists())


if __name__ == "__main__":
    unittest.main()
