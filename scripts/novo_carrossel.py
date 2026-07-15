#!/usr/bin/env python3
"""Create a blank carousel draft and generate/open the local editor."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = PROJECT_ROOT / "content" / "rascunhos"
GENERATOR = PROJECT_ROOT / "scripts" / "roteiro_to_instagram.py"
DEFAULT_SLIDE_COPY = "adicione aqui a sua copy"


def default_roteiro(total_slides: int) -> str:
    return "\n\n".join([DEFAULT_SLIDE_COPY] * total_slides)


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:60] or "carrossel"


def unique_path(base: Path) -> Path:
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    for i in range(2, 100):
        candidate = base.with_name(f"{stem}-{i}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"muitos arquivos com o mesmo nome: {base}")


def tweet_placeholder(title: str, date: str) -> str:
    roteiro = default_roteiro(10)
    return f"""---
status: rascunho
tipo: carrossel-tweet
plataforma: Instagram
tema: a preencher
date: {date}
tags:
  - carrossel-tweet
  - manual
---

# {title}

## Roteiro

{roteiro}

## Caption Instagram

Caption curta resumindo a tese. Reescreve aqui.

@omatheusdelucca
"""


def stories_placeholder(title: str, date: str) -> str:
    roteiro = default_roteiro(17)
    return f"""---
status: rascunho
tipo: carrossel
plataforma: Instagram
tema: a preencher
date: {date}
tags:
  - carrossel
  - manual
---

# {title}

## Roteiro

{roteiro}

## Caption Instagram

Caption curta resumindo a tese. Reescreve aqui.

@omatheusdelucca
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria e abre um carrossel em branco.")
    parser.add_argument("template", choices=["tweet", "stories"], nargs="?", default="stories")
    parser.add_argument("title", nargs="*", help="titulo opcional")
    parser.add_argument("--no-launch", action="store_true", help="gera HTML sem abrir browser")
    args = parser.parse_args()

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H:%M")
    stamp = now.strftime("%Y%m%d-%H%M")
    title = " ".join(args.title).strip()
    if not title:
        title = f"Tweet novo {date} {hour}" if args.template == "tweet" else f"Carrossel novo {date} {hour}"

    default_slug = f"novo-tweet-{stamp}" if args.template == "tweet" and not args.title else slugify(title)
    if args.template == "stories" and not args.title:
        default_slug = f"novo-carrossel-{stamp}"

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = unique_path(CONTENT_DIR / f"{default_slug}.md")
    body = tweet_placeholder(title, date) if args.template == "tweet" else stories_placeholder(title, date)
    md_path.write_text(body, encoding="utf-8")

    cmd = [sys.executable, str(GENERATOR), str(md_path), "--editor", "--template", args.template]
    if args.no_launch:
        cmd.append("--no-launch")
    subprocess.run(cmd, check=True)
    print(f"\nrascunho: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
