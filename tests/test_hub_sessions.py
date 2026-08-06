from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.hub_sessions import cleanup_hub_sessions, create_hub_session
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
