from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import tempfile
import uuid

try:
    from scripts.novo_carrossel import stories_placeholder, tweet_placeholder
    from scripts.roteiro_to_instagram import generate_editor_from_markdown
    from scripts.template_catalog import get_template
except ImportError:
    from novo_carrossel import stories_placeholder, tweet_placeholder
    from roteiro_to_instagram import generate_editor_from_markdown
    from template_catalog import get_template


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
    return _generate_hub_session(definition.id, session_id, editor_dir)


def refresh_hub_session(session_id: str, editor_dir: Path) -> HubSession:
    """Regenera uma sessão do Hub sem mudar sua chave local de documento.

    O id integra o nome do markdown temporário e, portanto, o DOC_KEY do editor.
    Manter esse id permite atualizar o HTML após uma evolução do template sem
    descartar copy, imagens ou preferências já salvas no navegador.
    """
    match = re.fullmatch(r"hub-(tweet|stories)-[0-9a-f]{12}", session_id)
    if not match:
        raise ValueError("Identificador de sessão inválido.")
    return _generate_hub_session(match.group(1), session_id, editor_dir)


def hub_session_needs_refresh(path: Path, template_id: str) -> bool:
    """Informa se o HTML de uma sessão foi gerado antes de seu template."""
    if not path.is_file():
        return False
    definition = get_template(template_id)
    return path.stat().st_mtime < definition.template_path.stat().st_mtime


def _generate_hub_session(template_id: str, session_id: str, editor_dir: Path) -> HubSession:
    definition = get_template(template_id)
    placeholder = tweet_placeholder if definition.id == "tweet" else stories_placeholder
    markdown = placeholder(session_id, date.today().isoformat())
    editor_dir.mkdir(parents=True, exist_ok=True)
    path = editor_dir / f"{session_id}.html"

    with tempfile.TemporaryDirectory(prefix="carrossel-hub-") as tmp:
        md_path = Path(tmp) / f"{session_id}.md"
        md_path.write_text(markdown, encoding="utf-8")
        try:
            generated_path = generate_editor_from_markdown(
                md_path,
                definition.id,
                editor_dir,
                hub_session=True,
            )
        except Exception:
            path.unlink(missing_ok=True)
            raise

    if generated_path != path or not path.is_file():
        raise RuntimeError("O editor temporário não foi gerado.")
    return HubSession(session_id, path, f"/{path.name}")
