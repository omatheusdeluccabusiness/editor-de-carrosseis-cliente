from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.hub_sessions import create_hub_session
from scripts.novo_carrossel import stories_placeholder, tweet_placeholder


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATOR = PROJECT_ROOT / "scripts" / "roteiro_to_instagram.py"
PLACEHOLDERS = {
    "tweet": tweet_placeholder,
    "stories": stories_placeholder,
}


def generate_direct_editor(template_id: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        title = f"direct-{template_id}"
        md_path = root / f"{title}.md"
        md_path.write_text(
            PLACEHOLDERS[template_id](title, date.today().isoformat()),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["CARROSSEL_EDITOR_DIR"] = str(root)
        subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                str(md_path),
                "--editor",
                "--template",
                template_id,
                "--no-launch",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return (root / f"{title}.html").read_text(encoding="utf-8")


class HubEditorModeTest(unittest.TestCase):
    def test_hub_session_enables_safe_return_and_hides_instagram(self) -> None:
        for template_id in PLACEHOLDERS:
            with self.subTest(template=template_id), tempfile.TemporaryDirectory() as tmp:
                session = create_hub_session(template_id, Path(tmp))
                html = session.path.read_text(encoding="utf-8")

                self.assertIn("const HUB_SESSION = true;", html)
                self.assertIn('id="btn-back-hub"', html)
                self.assertIn("publishButton.hidden = true", html)
                self.assertIn("Descartar esta criação e voltar aos modelos?", html)
                self.assertIn('id="btn-download-all"', html)
                self.assertIn('id="btn-send-tg"', html)

    def test_direct_generation_keeps_existing_publish_flow(self) -> None:
        for template_id in PLACEHOLDERS:
            with self.subTest(template=template_id):
                html = generate_direct_editor(template_id)

                self.assertIn("const HUB_SESSION = false;", html)
                self.assertIn('id="btn-publish-ig"', html)
                self.assertIn('id="btn-download-all"', html)
                self.assertIn('id="btn-send-tg"', html)


if __name__ == "__main__":
    unittest.main()
