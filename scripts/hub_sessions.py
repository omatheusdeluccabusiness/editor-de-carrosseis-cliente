from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

try:
    from scripts.novo_carrossel import stories_placeholder, tweet_placeholder
    from scripts.template_catalog import get_template
except ImportError:
    from novo_carrossel import stories_placeholder, tweet_placeholder
    from template_catalog import get_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATOR = PROJECT_ROOT / "scripts" / "roteiro_to_instagram.py"


@dataclass(frozen=True)
class HubSession:
    id: str
    path: Path
    url: str


def cleanup_hub_sessions(editor_dir: Path) -> list[Path]:
    removed = []
    for path in sorted(editor_dir.glob("hub-*.html")):
        path.unlink()
        removed.append(path)
    return removed


def create_hub_session(template_id: str, editor_dir: Path) -> HubSession:
    definition = get_template(template_id)
    session_id = f"hub-{definition.id}-{uuid.uuid4().hex[:12]}"
    placeholder = tweet_placeholder if definition.id == "tweet" else stories_placeholder
    markdown = placeholder(session_id, date.today().isoformat())
    editor_dir.mkdir(parents=True, exist_ok=True)
    path = editor_dir / f"{session_id}.html"

    with tempfile.TemporaryDirectory(prefix="carrossel-hub-") as tmp:
        md_path = Path(tmp) / f"{session_id}.md"
        md_path.write_text(markdown, encoding="utf-8")
        env = os.environ.copy()
        env["CARROSSEL_EDITOR_DIR"] = str(editor_dir)
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    str(md_path),
                    "--editor",
                    "--template",
                    definition.id,
                    "--no-launch",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
        except Exception:
            path.unlink(missing_ok=True)
            raise

    if not path.is_file():
        raise RuntimeError("O editor temporário não foi gerado.")
    return HubSession(session_id, path, f"/{path.name}")
