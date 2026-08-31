from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path


PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


@dataclass(frozen=True)
class TemplateDefinition:
    id: str
    name: str
    description: str
    aspect_ratio: str
    initial_slides: int
    template_path: Path
    preview_kind: str
    active: bool

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "aspect_ratio": self.aspect_ratio,
            "initial_slides": self.initial_slides,
            "preview_kind": self.preview_kind,
        }


TEMPLATE_CATALOG = {
    "tweet": TemplateDefinition(
        "tweet", "Modelo Tweet", "Post em formato de conversa.", "4:5", 10,
        PROJECT_ROOT / "templates" / "tweet_editor.html", "tweet", True,
    ),
    "stories": TemplateDefinition(
        "stories", "Stories", "Narrativa vertical em tela cheia.", "4:5", 10,
        PROJECT_ROOT / "templates" / "stories_editor.html", "stories", True,
    ),
    "stories-fundo": TemplateDefinition(
        "stories-fundo", "Stories C/ Fundo", "Foto full-bleed com cartelas editoriais.", "4:5", 10,
        PROJECT_ROOT / "templates" / "stories_background_editor.html", "stories-fundo", True,
    ),
    "notes": TemplateDefinition(
        "notes", "Bloco de Notas", "Texto editorial com estética de nota.", "4:5", 10,
        PROJECT_ROOT / "templates" / "notes_editor.html", "notes", True,
    ),
}


def get_template(template_id: str) -> TemplateDefinition:
    try:
        definition = TEMPLATE_CATALOG[template_id]
    except KeyError as exc:
        raise KeyError(f"Template desconhecido: {template_id}") from exc
    if not definition.active:
        raise KeyError(f"Template indisponível: {template_id}")
    return definition


def public_template_catalog() -> list[dict]:
    return [
        definition.public_dict()
        for definition in TEMPLATE_CATALOG.values()
        if definition.active
    ]
