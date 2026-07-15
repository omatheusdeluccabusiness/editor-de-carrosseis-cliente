from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts import novo_carrossel
from scripts import roteiro_to_instagram


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COPY = "adicione aqui a sua copy"


def roteiro_blocks(markdown: str) -> list[str]:
    match = re.search(
        r"## Roteiro\s*\n+(.*?)(?=\n## Caption Instagram)",
        markdown,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("bloco ## Roteiro não encontrado")
    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", match.group(1).strip())
        if paragraph.strip()
    ]


class DefaultCopyTest(unittest.TestCase):
    def test_tweet_placeholder_has_ten_identical_slides(self) -> None:
        markdown = novo_carrossel.tweet_placeholder("Título", "2026-07-15")
        self.assertEqual(roteiro_blocks(markdown), [DEFAULT_COPY] * 10)

    def test_stories_placeholder_has_seventeen_identical_slides(self) -> None:
        markdown = novo_carrossel.stories_placeholder("Título", "2026-07-15")
        self.assertEqual(roteiro_blocks(markdown), [DEFAULT_COPY] * 17)

    def test_parser_preserves_short_default_copy_as_individual_slides(self) -> None:
        roteiro = "\n\n".join([DEFAULT_COPY] * 10)

        slides = roteiro_to_instagram._fatiar_roteiro_em_slides(
            roteiro,
            total_slides=10,
        )

        self.assertEqual(len(slides), 10)
        self.assertEqual(
            ["\n\n".join(slide["paragraphs"]) for slide in slides],
            [DEFAULT_COPY] * 10,
        )

    def test_add_slide_buttons_use_default_copy(self) -> None:
        expected_by_template = {
            "tweet_editor.html": "text: 'adicione aqui a sua copy'",
            "stories_editor.html": "html: 'adicione aqui a sua copy'",
        }
        for filename, expected in expected_by_template.items():
            with self.subTest(template=filename):
                template = (PROJECT_ROOT / "templates" / filename).read_text(
                    encoding="utf-8"
                )
                self.assertIn(expected, template)

    def test_existing_drafts_use_default_copy_on_every_slide(self) -> None:
        expected_counts = {
            "novo-carrossel-20260715-1753.md": 17,
            "novo-tweet-20260715-1753.md": 10,
            "teste-stories-17.md": 17,
            "teste-tweet-10.md": 10,
            "validacao-editor-final.md": 10,
        }
        drafts_dir = PROJECT_ROOT / "content" / "rascunhos"
        for filename, count in expected_counts.items():
            with self.subTest(draft=filename):
                markdown = (drafts_dir / filename).read_text(encoding="utf-8")
                self.assertEqual(roteiro_blocks(markdown), [DEFAULT_COPY] * count)


if __name__ == "__main__":
    unittest.main()
