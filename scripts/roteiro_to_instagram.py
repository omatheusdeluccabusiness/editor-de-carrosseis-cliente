#!/usr/bin/env python3
"""
roteiro_to_instagram.py — Pipeline completo: roteiro .md → 10 slides PNG → Instagram

Uso:
    # Validação visual (gera PNGs e mantém pra você revisar, sem publicar)
    python3 roteiro_to_instagram.py "caminho/do/roteiro.md" --dry-run

    # Publica direto
    python3 roteiro_to_instagram.py "caminho/do/roteiro.md"

    # Publica e mantém PNGs salvos pra reuso
    python3 roteiro_to_instagram.py "caminho/do/roteiro.md" --keep-images

Layout: 1080x1350 (4:5 Instagram), preto profundo + branco + dourado.
Fontes: Helvetica Neue (sistema macOS).
"""
import argparse
import hashlib
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import unicodedata
import webbrowser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONSTANTES VISUAIS
# ============================================================================

WIDTH, HEIGHT = 1080, 1350
MARGIN_X = 90
MARGIN_TOP = 130
MARGIN_BOTTOM = 130

BG_COLOR = (15, 15, 15)         # preto profundo
FG_COLOR = (245, 240, 232)      # branco creme
ACCENT_COLOR = (240, 198, 56)   # dourado
MUTED_COLOR = (140, 140, 140)   # cinza
DEFAULT_SLIDE_COPY = "adicione aqui a sua copy"

FONT_HELVETICA = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_TIMES_BOLD = "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
FONT_NEW_YORK = "/System/Library/Fonts/NewYorkItalic.ttf"

# Índices da Helvetica Neue:
HELV_REGULAR = 0
HELV_BOLD = 1
HELV_ITALIC = 2
HELV_BOLD_ITALIC = 3
HELV_CONDENSED_BOLD = 4
HELV_ULTRALIGHT = 5


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    """Carrega Helvetica Neue na variação pedida."""
    idx_map = {
        "regular": HELV_REGULAR,
        "bold": HELV_BOLD,
        "italic": HELV_ITALIC,
        "bold_italic": HELV_BOLD_ITALIC,
        "condensed_bold": HELV_CONDENSED_BOLD,
        "light": HELV_ULTRALIGHT,
    }
    return ImageFont.truetype(FONT_HELVETICA, size, index=idx_map[weight])


def serif_italic(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_NEW_YORK, size)


# ============================================================================
# PARSER DO MARKDOWN
# ============================================================================

def _fatiar_roteiro_em_slides(roteiro_text: str, capa_titulo: str = "", capa_subtitulo: str = "", total_slides: int = 10) -> list[dict]:
    """
    Fatia o roteiro em N slides (default 10):
      - Slide 1 = Capa = PRIMEIRO PARÁGRAFO do roteiro
      - Slides 2..N-1 = corpo do roteiro fatiado em (N-2) buckets
      - Slide N = CTA do roteiro (último(s) parágrafo(s))

    Regra dura: A CAPA É SEMPRE O COMEÇO DO ROTEIRO. Não usar texto separado
    de '## Carrossel-espelho' nem similar. O hook do roteiro É o conteúdo da capa.

    Args:
        capa_titulo, capa_subtitulo: ignorados (deprecated, mantidos por
        compatibilidade de assinatura). O primeiro parágrafo do roteiro
        sempre vira a capa.
    """
    # Quebra em parágrafos
    paragraphs = re.split(r"\n\s*\n", roteiro_text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if len(paragraphs) < 3:
        # roteiro muito curto, fallback simples
        return None

    # Junta parágrafos curtos isolados com vizinho (pré-processamento)
    paragraphs = _coalesce_short_paragraphs(paragraphs, min_chars=60)

    # Slide 1: capa = PRIMEIRO PARÁGRAFO do roteiro
    capa_paragrafo = paragraphs[0]
    slides = [{
        "num": 1,
        "kind": "capa",
        "paragraphs": [capa_paragrafo],
    }]

    # Slide 10: CTA — bloco final do roteiro (presume-se que roteiro termina no CTA)
    # Estratégia: pega SEMPRE o último parágrafo, e estende pra trás enquanto
    # houver gatilhos de CTA (palavras-chave operacionais ou frases de convocação).
    cta_paragraphs = []
    # body_paragraphs começa do parágrafo 2 (parágrafo 1 já foi pra capa)
    body_paragraphs = list(paragraphs[1:])

    CTA_TRIGGERS = (
        "se você", "se tu",
        "por último", "por ultimo",
        "comente", "comenta",
        "convite", "um convite",
        "você terá", "voce tera",
    )

    if body_paragraphs:
        # Sempre pega o último parágrafo (presume que roteiro termina no CTA)
        cta_paragraphs.insert(0, body_paragraphs.pop())
        # Estende pra trás enquanto for parte do bloco CTA, máximo 3 parágrafos
        while body_paragraphs and len(cta_paragraphs) < 3:
            last = body_paragraphs[-1]
            low = last.lower().strip()
            is_cta_part = any(low.startswith(t) for t in CTA_TRIGGERS)
            if is_cta_part:
                cta_paragraphs.insert(0, body_paragraphs.pop())
            else:
                break

    # NÃO descarta o primeiro parágrafo: o roteiro inteiro vai pros slides 2-10.
    # A capa (slide 1) é texto separado, vem de '## Carrossel-espelho' slide 1
    # ou fallback do título da peça. Roteiro pode ter hook próprio diferente
    # do texto da capa, e descartar perderia conteúdo (incidente 2026-05-06).

    # total_slides é o MÁXIMO, não fixo. Se o roteiro só tem N parágrafos de corpo,
    # gera N slides de corpo (em vez de criar buckets vazios renderizados como slides
    # em branco). Roteiros longos se consolidam até total_slides-2 buckets.
    max_body_slots = max(1, total_slides - 2)
    target_n = min(max_body_slots, max(1, len(body_paragraphs)))

    if not body_paragraphs:
        # roteiro sem corpo (só capa + CTA): nenhum slide de corpo
        target_n = 0
    else:
        buckets = _distribute_paragraphs(body_paragraphs, target_n)
        # filtra buckets vazios defensivamente (não deveriam existir, mas paranoia)
        buckets = [b for b in buckets if b]
        for i, bucket in enumerate(buckets):
            slides.append({
                "num": i + 2,
                "kind": "corpo",
                "paragraphs": bucket,
            })

    # Slide final: CTA — número = quantidade real de slides até aqui + 1
    if not cta_paragraphs:
        cta_paragraphs = [paragraphs[-1]] if paragraphs else [""]
    cta_num = len(slides) + 1
    slides.append({
        "num": cta_num,
        "kind": "cta",
        "paragraphs": cta_paragraphs,
    })

    return slides


def _distribute_paragraphs(paragraphs: list[str], n_buckets: int) -> list[list[str]]:
    """
    Distribui parágrafos em n_buckets, agrupando os curtos.
    Algoritmo: se total de parágrafos == n_buckets, mapeia 1:1.
    Se for maior, agrupa parágrafos consecutivos curtos.
    Se for menor, cada parágrafo vai num bucket (sobram buckets vazios — evitar com merge depois).
    """
    if len(paragraphs) <= n_buckets:
        # cada parágrafo num bucket próprio (até n_buckets); buckets sobrantes ficam vazios
        buckets = [[p] for p in paragraphs]
        while len(buckets) < n_buckets:
            buckets.append([])
        return buckets[:n_buckets]

    # caso comum: parágrafos > n_buckets. Agrupa curtos.
    total_chars = sum(len(p) for p in paragraphs)
    target_chars = total_chars / n_buckets

    buckets = [[]]
    current_chars = 0
    SHORT_THRESHOLD = 120  # parágrafo "curto"

    for p in paragraphs:
        plen = len(p)
        # se bucket atual já tem conteúdo e adicionar este parágrafo faria estourar, abre novo
        if current_chars > 0 and (current_chars + plen) > target_chars * 1.4 and len(buckets) < n_buckets:
            buckets.append([])
            current_chars = 0
        # se parágrafo é denso e bucket atual já tem coisa, prefere ir num slide só
        elif current_chars > 0 and plen > target_chars * 0.8 and len(buckets) < n_buckets:
            buckets.append([])
            current_chars = 0
        buckets[-1].append(p)
        current_chars += plen + 16  # +16 pra spacing entre parágrafos

    # Se sobrarem buckets a criar, divide o maior
    while len(buckets) < n_buckets:
        idx_biggest = max(range(len(buckets)), key=lambda i: sum(len(p) for p in buckets[i]))
        if len(buckets[idx_biggest]) <= 1:
            break  # não dá pra dividir mais
        half = len(buckets[idx_biggest]) // 2
        new_bucket = buckets[idx_biggest][half:]
        buckets[idx_biggest] = buckets[idx_biggest][:half]
        buckets.insert(idx_biggest + 1, new_bucket)

    # Se exceder n_buckets, junta os menores
    while len(buckets) > n_buckets:
        sizes = sorted(range(len(buckets)), key=lambda i: sum(len(p) for p in buckets[i]))
        smallest = sizes[0]
        # junta com vizinho menor
        if smallest + 1 < len(buckets):
            buckets[smallest].extend(buckets[smallest + 1])
            del buckets[smallest + 1]
        elif smallest > 0:
            buckets[smallest - 1].extend(buckets[smallest])
            del buckets[smallest]
        else:
            break

    return buckets[:n_buckets]


def _coalesce_short_paragraphs(paragraphs: list[str], min_chars: int = 60) -> list[str]:
    """
    Junta parágrafos curtos (< min_chars) com o parágrafo seguinte,
    pra evitar slides com frase isolada como "Agora, mudando de pato pra ganso."

    Roda ANTES do fatiamento. Mantém ordem original do roteiro.
    """
    if not paragraphs:
        return []
    if all(p.strip() == DEFAULT_SLIDE_COPY for p in paragraphs):
        return paragraphs
    result = []
    i = 0
    while i < len(paragraphs):
        p = paragraphs[i]
        # se p é curto e tem próximo, junta com o próximo no mesmo "parágrafo lógico"
        if len(p) < min_chars and i + 1 < len(paragraphs):
            joined = p + "\n\n" + paragraphs[i + 1]
            result.append(joined)
            i += 2
        else:
            result.append(p)
            i += 1
    return result


def parse_roteiro(md_path: Path) -> dict:
    """
    Extrai dos arquivos da Trilha:
      - título (do H1)
      - 10 slides (fatiados a partir da seção '## Roteiro' conforme regras da Trilha Carrossel)
      - caption (do bloco '## Caption Instagram')
      - capa título + subtítulo (extraídos do hook ou do '## Carrossel-espelho' slide 1 se existir)
    """
    text = md_path.read_text(encoding="utf-8")

    # extrai título da peça do H1
    title_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else md_path.stem

    # extrai bloco '## Roteiro' (texto fluido, sem subseções)
    # roteiro vai da linha "## Roteiro" até a próxima seção de mesmo nível
    roteiro_match = re.search(
        r"## Roteiro\s*\n+(.*?)(?=\n## )",
        text,
        re.DOTALL,
    )
    if not roteiro_match:
        raise ValueError(f"Bloco '## Roteiro' não encontrado em {md_path.name}")
    roteiro_text = roteiro_match.group(1).strip()
    # remove separadores de seção markdown ('---' em linha própria)
    roteiro_text = re.sub(r"\n\s*---\s*\n", "\n\n", roteiro_text)
    roteiro_text = re.sub(r"\n\s*---\s*$", "", roteiro_text).strip()

    # extrai capa: título + subtítulo
    # primeiro tenta do '## Carrossel-espelho' slide 1 (compatibilidade)
    capa_titulo = title  # fallback
    capa_subtitulo = ""
    capa_slide_match = re.search(
        r"### Slide 1\s*[—-][^\n]*\n(.*?)(?=\n### Slide )",
        text,
        re.DOTALL,
    )
    if capa_slide_match:
        capa_body = capa_slide_match.group(1).strip()
        tm = re.search(r"\*\*(.+?)\*\*", capa_body, re.DOTALL)
        if tm:
            capa_titulo = tm.group(1).strip()
        sm = re.search(r"(?<!\*)\*([^\*\n]+)\*(?!\*)", capa_body)
        if sm:
            capa_subtitulo = sm.group(1).strip()

    # fatia o roteiro no número de slides configurado (default 10)
    slides = _fatiar_roteiro_em_slides(roteiro_text, capa_titulo, capa_subtitulo, total_slides=TEMPLATE_TOTAL_SLIDES)
    if not slides:
        raise ValueError(f"Roteiro em {md_path.name} muito curto pra fatiar em {TEMPLATE_TOTAL_SLIDES} slides")

    # extrai caption
    caption_match = re.search(
        r"## Caption Instagram\s*\n+(.*?)(?=\n## |\Z)",
        text,
        re.DOTALL,
    )
    caption = caption_match.group(1).strip() if caption_match else ""

    return {
        "title": title,
        "slides": slides,
        "caption": caption,
        "_roteiro_raw": roteiro_text,  # uso interno: hash pra DOC_KEY
    }


# ============================================================================
# RENDERIZADOR DE SLIDES
# ============================================================================

def wrap_text(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Quebra texto em linhas que cabem em max_width."""
    paragraphs = text.split("\n")
    all_lines = []
    for para in paragraphs:
        if not para.strip():
            all_lines.append("")  # linha em branco preserva quebra de parágrafo
            continue
        words = para.split()
        if not words:
            all_lines.append("")
            continue
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            bbox = fnt.getbbox(test)
            if bbox[2] - bbox[0] <= max_width:
                line = test
            else:
                if line:
                    all_lines.append(line)
                line = word
        if line:
            all_lines.append(line)
    return all_lines


def measure_lines(lines: list[str], fnt: ImageFont.FreeTypeFont, line_spacing: float = 1.35) -> int:
    """Calcula altura total ocupada pelas linhas."""
    if not lines:
        return 0
    line_h = int(fnt.size * line_spacing)
    return line_h * len(lines)


def draw_lines_centered(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    fnt: ImageFont.FreeTypeFont,
    color: tuple,
    y_start: int,
    line_spacing: float = 1.35,
) -> int:
    """Desenha linhas centralizadas horizontalmente, retorna y final."""
    line_h = int(fnt.size * line_spacing)
    y = y_start
    for line in lines:
        if line == "":
            y += line_h // 2
            continue
        bbox = fnt.getbbox(line)
        line_w = bbox[2] - bbox[0]
        x = (WIDTH - line_w) // 2
        draw.text((x, y), line, font=fnt, fill=color)
        y += line_h
    return y


def fit_text_to_box(
    text: str,
    initial_size: int,
    weight: str,
    max_width: int,
    max_height: int,
    min_size: int = 28,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """
    Diminui o tamanho da fonte até o texto caber na caixa.
    Retorna (font_obj, lines_quebradas).
    """
    size = initial_size
    while size >= min_size:
        fnt = font(size, weight)
        lines = wrap_text(text, fnt, max_width)
        height = measure_lines(lines, fnt)
        if height <= max_height:
            return fnt, lines
        size -= 2
    # mínimo absoluto
    fnt = font(min_size, weight)
    lines = wrap_text(text, fnt, max_width)
    return fnt, lines


def render_capa(slide: dict, total: int) -> Image.Image:
    """Capa: título grande + subtítulo serif italic."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # extrai título e subtítulo do body da capa
    body = slide["body"]
    # padrão típico: "**TÍTULO**\n*subtítulo*"
    title_text = ""
    subtitle_text = ""

    # tenta extrair **TÍTULO**
    title_m = re.search(r"\*\*(.+?)\*\*", body, re.DOTALL)
    if title_m:
        title_text = title_m.group(1).strip()
    # tenta extrair *subtítulo* (não cercado por **)
    subtitle_m = re.search(r"(?<!\*)\*([^\*\n]+)\*(?!\*)", body)
    if subtitle_m:
        subtitle_text = subtitle_m.group(1).strip()

    # fallback: se não achar markup, usa as duas primeiras linhas
    if not title_text:
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        if lines:
            title_text = lines[0].replace("**", "").replace("*", "")
        if len(lines) > 1:
            subtitle_text = lines[1].replace("**", "").replace("*", "")

    title_text = title_text.upper()

    # marca decorativa no topo
    draw.line([(MARGIN_X, 110), (MARGIN_X + 80, 110)], fill=ACCENT_COLOR, width=4)

    # título centralizado verticalmente
    max_w = WIDTH - 2 * MARGIN_X
    max_h_title = HEIGHT - 380  # deixa espaço pro subtitle e footer
    title_fnt, title_lines = fit_text_to_box(
        title_text, initial_size=92, weight="condensed_bold",
        max_width=max_w, max_height=max_h_title, min_size=46,
    )
    title_h = measure_lines(title_lines, title_fnt, line_spacing=1.1)

    # área central do bloco título+subtítulo
    block_y_start = (HEIGHT - title_h - 100) // 2
    y = draw_lines_centered(draw, title_lines, title_fnt, FG_COLOR, block_y_start, line_spacing=1.1)

    # subtítulo (serif italic) abaixo
    if subtitle_text:
        sub_fnt = serif_italic(38)
        sub_lines = wrap_text(subtitle_text, sub_fnt, max_w)
        y += 30
        draw_lines_centered(draw, sub_lines, sub_fnt, ACCENT_COLOR, y, line_spacing=1.3)

    # número de slide no rodapé
    slide_label = f"01 / {total:02d}"
    label_fnt = font(22, "regular")
    bbox = label_fnt.getbbox(slide_label)
    label_w = bbox[2] - bbox[0]
    draw.text(((WIDTH - label_w) // 2, HEIGHT - 75), slide_label, font=label_fnt, fill=MUTED_COLOR)

    # marca @ no canto
    handle = "@omatheusdelucca"
    h_fnt = font(22, "regular")
    h_bbox = h_fnt.getbbox(handle)
    draw.text((MARGIN_X, HEIGHT - 75), handle, font=h_fnt, fill=MUTED_COLOR)

    return img


def render_slide_corpo(slide: dict, total: int, is_cta: bool = False) -> Image.Image:
    """Slide intermediário ou de fechamento."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # marca decorativa no topo
    draw.line([(MARGIN_X, 110), (MARGIN_X + 80, 110)], fill=ACCENT_COLOR, width=4)

    body = slide["body"]
    # processa o body em "blocos": cada bloco é separado por linha em branco
    # detecta se primeira linha é header em **bold**
    paragraphs = re.split(r"\n\s*\n", body)
    blocks = []  # cada bloco: {"type": "header"|"text"|"highlight", "text": ...}

    for i, p in enumerate(paragraphs):
        p = p.strip()
        if not p:
            continue
        # remove markdown e detecta tipo
        bold_match = re.match(r"^\*\*(.+?)\*\*\s*$", p, re.DOTALL)
        if bold_match:
            blocks.append({"type": "header", "text": bold_match.group(1).strip()})
        else:
            # remove ** inline
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", p)
            clean = re.sub(r"(?<!\*)\*([^\*\n]+)\*(?!\*)", r"\1", clean)
            blocks.append({"type": "text", "text": clean})

    # último bloco do CTA: destaca em accent color
    if is_cta and blocks:
        # encontra a última frase com aspas (geralmente o CTA)
        last_block = blocks[-1]
        if "perfil" in last_block["text"].lower() or "comenta" in last_block["text"].lower():
            last_block["type"] = "cta"

    # renderização: ajusta tamanhos
    max_w = WIDTH - 2 * MARGIN_X
    available_h = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM - 60  # 60 pro rodapé

    # tamanhos por tipo
    base_text_size = 52
    base_header_size = 44

    # se tem MUITO texto, reduz o base
    total_chars = sum(len(b["text"]) for b in blocks)
    if total_chars > 400:
        base_text_size = 44
        base_header_size = 38
    if total_chars > 700:
        base_text_size = 36
        base_header_size = 32

    # primeiro mede
    rendered_blocks = []
    total_h = 0
    block_gap = 36
    for i, b in enumerate(blocks):
        if b["type"] == "header":
            fnt, lines = fit_text_to_box(
                b["text"], base_header_size, "bold",
                max_w, available_h - total_h, min_size=28,
            )
        elif b["type"] == "cta":
            fnt, lines = fit_text_to_box(
                b["text"], base_text_size + 4, "bold",
                max_w, available_h - total_h, min_size=30,
            )
        else:
            fnt, lines = fit_text_to_box(
                b["text"], base_text_size, "regular",
                max_w, available_h - total_h, min_size=28,
            )
        h = measure_lines(lines, fnt, line_spacing=1.32)
        rendered_blocks.append({"type": b["type"], "fnt": fnt, "lines": lines, "h": h})
        total_h += h
        if i < len(blocks) - 1:
            total_h += block_gap

    # centraliza verticalmente
    y_start = MARGIN_TOP + max(0, (available_h - total_h) // 2)
    y = y_start

    for i, rb in enumerate(rendered_blocks):
        color = FG_COLOR
        if rb["type"] == "header":
            color = ACCENT_COLOR
        elif rb["type"] == "cta":
            color = ACCENT_COLOR
        y = draw_lines_centered(draw, rb["lines"], rb["fnt"], color, y, line_spacing=1.32)
        if i < len(rendered_blocks) - 1:
            y += block_gap

    # rodapé
    slide_label = f"{slide['num']:02d} / {total:02d}"
    label_fnt = font(22, "regular")
    bbox = label_fnt.getbbox(slide_label)
    label_w = bbox[2] - bbox[0]
    draw.text(((WIDTH - label_w) // 2, HEIGHT - 75), slide_label, font=label_fnt, fill=MUTED_COLOR)

    handle = "@omatheusdelucca"
    h_fnt = font(22, "regular")
    draw.text((MARGIN_X, HEIGHT - 75), handle, font=h_fnt, fill=MUTED_COLOR)

    return img


def render_slide(slide: dict, total: int) -> Image.Image:
    """Despacha pra renderizador correto."""
    if slide["num"] == 1:
        return render_capa(slide, total)
    is_cta = slide["num"] == total
    return render_slide_corpo(slide, total, is_cta=is_cta)


# ============================================================================
# PIPELINE
# ============================================================================

def render_all(parsed: dict, output_dir: Path) -> list[Path]:
    """Renderiza todos os slides em PNG."""
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(parsed["slides"])
    paths = []
    for slide in parsed["slides"]:
        img = render_slide(slide, total)
        out_path = output_dir / f"slide_{slide['num']:02d}.png"
        img.save(out_path, "PNG", optimize=True)
        paths.append(out_path)
        print(f"  ✓ slide {slide['num']:02d}/{total} → {out_path.name}")
    return paths


def publish(images: list[Path], caption: str, dry_run: bool = False) -> None:
    """Chama publish_instagram.py."""
    publisher = Path(__file__).parent / "publish_instagram.py"
    cmd = [sys.executable, str(publisher), "--images"] + [str(p) for p in images] + ["--caption", caption]
    if dry_run:
        cmd.append("--dry-run")
    print(f"\n→ Executando publisher...")
    subprocess.run(cmd, check=True)


# ============================================================================
# MODO EDITOR (HTML interativo)
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EDITOR_PORT = int(os.environ.get("CARROSSEL_EDITOR_PORT", "8777"))
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
EDITOR_TEMPLATES = {
    "ostentacao": TEMPLATE_DIR / "ostentacao_editor.html",
    "stories":    TEMPLATE_DIR / "stories_editor.html",
    "tweet":      TEMPLATE_DIR / "tweet_editor.html",
}
EDITOR_TEMPLATE = EDITOR_TEMPLATES["ostentacao"]  # default; sobrescrito por --template
TEMPLATE_TOTAL_SLIDES = 10  # default para todos os templates
TEMPLATE_SLIDES_BY_NAME = {"ostentacao": 10, "stories": 10, "tweet": 10}
EDITOR_DIR = Path(os.environ.get("CARROSSEL_EDITOR_DIR", "/tmp/carrossel-editor"))
SERVE_SCRIPT = Path(__file__).with_name("serve_carrossel.py")  # canônico unificado
SERVICE_SCRIPT = Path(__file__).with_name("carrossel_service.py")


def _md_inline_to_html(text: str) -> str:
    """Converte **bold** em <strong>, escapa HTML básico."""
    # escapa HTML
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # **bold** → <strong>
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # *italic* (sem **) → <em>
    text = re.sub(r"(?<!\*)\*([^\*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _bg_for_slide(num: int, total: int) -> str:
    """Mapeia número de slide pra background da paleta Direção C."""
    if num == 1:
        return "bg-01"  # vermelho fogo (capa)
    if num == total:
        return "bg-10"  # multicolor (CTA final)
    # alterna entre os bgs intermediários
    cycle = ["bg-03", "bg-04", "bg-05", "bg-06", "bg-07", "bg-08", "bg-09"]
    return cycle[(num - 2) % len(cycle)]


def _fade_for_slide(num: int, total: int) -> str:
    """Fade per-slide (intensidade do filtro de legibilidade)."""
    if num == 1:
        return "1.2"
    if num == total:
        return "1.3"
    return "1.2"


def _slide_label(num: int, total: int) -> str:
    """Label exibido acima do slide no editor."""
    if num == 1:
        return "Capa"
    if num == total:
        return "CTA final"
    return f"Slide {num}"


def _build_slide_html(slide: dict, total: int) -> str:
    """Gera o HTML de UM slide-wrap com bgs + body-zone + blocos.

    Estrutura nova de slide (vinda do fatiamento do roteiro):
      slide = { num, kind: "capa"|"corpo"|"cta", title?, subtitle?, paragraphs? }
    """
    num = slide["num"]
    kind = slide.get("kind", "corpo")
    bg = _bg_for_slide(num, total)
    label = _slide_label(num, total)
    is_capa = (kind == "capa")
    is_cta = (kind == "cta")

    blocks_html = []

    if is_capa:
        # Capa = primeiro parágrafo do roteiro (regra Matheus 2026-05-06)
        # Renderiza como body big destacado, sem uppercase artificial
        paragraphs = slide.get("paragraphs", [])
        if not paragraphs and (slide.get("title") or slide.get("subtitle")):
            # fallback compatibilidade: se vier título/subtítulo, renderiza como antes
            if slide.get("subtitle"):
                blocks_html.append(f'<div class="body lede">{_md_inline_to_html(slide["subtitle"])}</div>')
            if slide.get("title"):
                blocks_html.append(f'<div class="h-display smaller">{_md_inline_to_html(slide["title"])}</div>')
        else:
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                blocks_html.append(f'<div class="body big">{_md_inline_to_html(p)}</div>')
    else:
        # corpo ou CTA: cada parágrafo do roteiro = 1 bloco body big
        paragraphs = slide.get("paragraphs", [])
        for i, p in enumerate(paragraphs):
            p = p.strip()
            if not p:
                continue
            # parêntese íntimo coletivo (parágrafo entre parênteses) → body italic
            if p.startswith("(") and p.endswith(")"):
                blocks_html.append(f'<div class="body italic">{_md_inline_to_html(p)}</div>')
                continue
            # CTA (último parágrafo do slide 10 com "perfil"/"comenta") → destaca em smaller
            if is_cta:
                lt = p.lower()
                if 'comenta "perfil"' in lt or "comenta 'perfil'" in lt:
                    blocks_html.append(f'<div class="h-display smaller">{_md_inline_to_html(p)}</div>')
                    continue
            # parágrafo curto e contundente (frase-martelo): body lede em destaque
            if len(p) < 100 and ('.' in p or '!' in p) and i > 0:
                blocks_html.append(f'<div class="body lede">{_md_inline_to_html(p)}</div>')
                continue
            # padrão: body lede pros corpos (slides intermediários), body big pro CTA
            default_variant = "big" if is_cta else "lede"
            blocks_html.append(f'<div class="body {default_variant}">{_md_inline_to_html(p)}</div>')

    capa_class = " capa" if is_capa else ""
    cta_class = " cta-final" if is_cta else ""

    indent = "        "
    blocks_str = "\n".join(indent + b for b in blocks_html)

    handle = "@omatheusdelucca"
    num_label = f"{num:02d} / {total:02d}"

    return f'''  <!-- ===== SLIDE {num:02d} — {label} ===== -->
  <div class="slide-wrap">
    <div class="slide-label">{num:02d} — {label}</div>
    <div class="stage">
      <div class="slide {bg}{capa_class}{cta_class}" data-fade="1.0">
        <div class="photo"></div>
        <div class="body-zone">
{blocks_str}
        </div>
        <div class="footer-bar" style="display:flex;justify-content:space-between;">
          <div class="footer-tag">{handle}</div>
          <div class="footer-tag" style="text-align:right;">{num_label}</div>
        </div>
      </div>
    </div>
  </div>'''


def _generate_slides_html(parsed: dict) -> str:
    """Concatena HTML de todos os slides."""
    total = len(parsed["slides"])
    return "\n\n".join(_build_slide_html(s, total) for s in parsed["slides"])


SCHEMA_VERSION = "v5"  # v4: novo template stories (PT Serif, fontSize por bloco, .hot = só cor de texto sem pill nem underline)


def _make_doc_key(roteiro_md: Path, content_hash: str = "") -> str:
    """
    DOC_KEY estável por (arquivo .md + versão de conteúdo + schema).
    Inclui hash do roteiro_text pra invalidar localStorage automaticamente
    quando o .md muda. SCHEMA_VERSION invalida quando o gerador muda
    a estrutura interna dos blocks (ex: capa passa a ser 1 block em vez de 2).

    Comportamento:
      - Você edita o .md → hash muda → key nova → doc antigo fica órfão.
      - Eu mudo a estrutura do gerador → SCHEMA_VERSION bumped → key nova.
      - Você só edita visual no preview → mesmo hash + schema → edições visuais preservadas.
    """
    base = slugify(roteiro_md.stem)
    h = content_hash[:10] if content_hash else "v1"
    return f"matheusao-ostentacao-{base}-{SCHEMA_VERSION}-{h}"


def _hash_roteiro(roteiro_text: str) -> str:
    """Hash curto do roteiro pra usar no DOC_KEY."""
    return hashlib.sha256(roteiro_text.encode("utf-8")).hexdigest()


def extract_doc_for_editor(parsed: dict) -> dict:
    """
    Compatibilidade — não usada na arquitetura nova (Direção C fork).
    O template canônico monta seu próprio doc via buildDocFromDOM().
    """
    return {
        "title": parsed["title"],
        "slides": [{"num": s["num"]} for s in parsed["slides"]],
        "caption": parsed["caption"],
    }


def is_server_running(port: int = EDITOR_PORT) -> bool:
    """Checa se já tem servidor rodando na porta."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def start_server_background():
    """Inicia o servidor persistente em background."""
    print(f"   Garantindo servidor persistente em background...")

    if SERVICE_SCRIPT.exists():
        result = subprocess.run(
            [sys.executable, str(SERVICE_SCRIPT), "start"],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print("   " + result.stdout.strip().replace("\n", "\n   "))
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"Servidor persistente não subiu. {detail}")
        if is_server_running():
            print(f"   ✓ Servidor persistente rodando")
            return None

    print(f"   Iniciando servidor em background...")
    EDITOR_DIR.mkdir(parents=True, exist_ok=True)
    log_file = open(EDITOR_DIR / "server.log", "w")
    proc = subprocess.Popen(
        [sys.executable, str(SERVE_SCRIPT)],
        stdout=log_file, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    # espera até 5s servidor subir
    for _ in range(20):
        time.sleep(0.25)
        if is_server_running():
            print(f"   ✓ Servidor rodando (PID {proc.pid})")
            return proc
    raise RuntimeError(f"Servidor não respondeu em 5 segundos. Veja {EDITOR_DIR / 'server.log'}")


def slugify(text: str) -> str:
    """Slug ASCII-only (Python http.server quebra com acentos no path)."""
    # NFKD decompõe acentos, depois encode/decode ASCII descarta
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:50] or "carrossel"


def _generate_slides_json(parsed: dict) -> str:
    """
    Gera o array JS ORIGINAL_SLIDES = [{label, text}, ...] pro template tweet.
    O tweet usa array JS em vez de HTML pré-renderizado como o stories.
    """
    slides_data = []
    for slide in parsed["slides"]:
        num = slide.get("num", len(slides_data) + 1)
        kind = slide.get("kind", "corpo")
        text = "\n\n".join(slide.get("paragraphs", []))
        if kind == "capa":
            label = f"{num} — Capa"
        elif kind == "cta":
            label = f"{num} — CTA"
        else:
            label = f"{num} — Slide"
        slides_data.append({"label": label, "text": text})
    return json.dumps(slides_data, ensure_ascii=False)


def launch_editor(parsed: dict, roteiro_md: Path, no_launch: bool = False) -> str:
    """
    Gera HTML do editor pré-populado.
    Se no_launch=False (padrão), sobe servidor próprio e abre browser.
    Se no_launch=True, só gera HTML (assumindo que preview_start cuida do servidor).
    Retorna a URL final.
    """
    if not EDITOR_TEMPLATE.exists():
        print(f"ERRO: template não encontrado em {EDITOR_TEMPLATE}", file=sys.stderr)
        sys.exit(1)

    EDITOR_DIR.mkdir(exist_ok=True)

    template_html = EDITOR_TEMPLATE.read_text(encoding="utf-8")

    # Geração dos slides — formato depende do template ativo.
    # Stories e ostentacao usam HTML estruturado ({{SLIDES_HTML}}).
    # Tweet usa array JS ({{SLIDES_JSON}}).
    slides_html = _generate_slides_html(parsed)
    slides_json = _generate_slides_json(parsed)

    # Hash do conteúdo dos slides entra no DOC_KEY pra invalidar doc antigo
    # quando o roteiro ou o fatiamento mudam.
    hash_source = slides_json if "{{SLIDES_JSON}}" in template_html else slides_html
    content_hash = _hash_roteiro(hash_source)
    doc_key = _make_doc_key(roteiro_md, content_hash)
    n_slides = len(parsed["slides"])
    peca_path = str(roteiro_md.parent)

    # escapa caption pra inserção em <textarea> (HTML safe)
    caption_html = (parsed["caption"] or "")\
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # escapa title pra HTML
    title_html = (parsed["title"] or "")\
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    out_html = template_html
    out_html = out_html.replace("{{TITLE}}", title_html)
    out_html = out_html.replace("{{N_SLIDES}}", str(n_slides))
    out_html = out_html.replace("{{CAPTION}}", caption_html)
    out_html = out_html.replace("{{SLIDES_HTML}}", slides_html)
    out_html = out_html.replace("{{SLIDES_JSON}}", slides_json)
    out_html = out_html.replace("{{DOC_KEY}}", doc_key)
    out_html = out_html.replace("{{PECA_PATH}}", peca_path)

    slug = slugify(parsed["title"])
    out_path = EDITOR_DIR / f"{slug}.html"
    out_path.write_text(out_html, encoding="utf-8")
    print(f"\n📝 HTML do editor: {out_path}")

    url = f"http://localhost:{EDITOR_PORT}/{slug}.html"

    if no_launch:
        print(f"\n🌐 URL: {url}")
        print(f"   (servidor controlado externamente/persistente)")
        return url

    # garante servidor rodando
    if not is_server_running():
        start_server_background()
    else:
        print(f"   ✓ Servidor já estava rodando")

    print(f"\n🌐 Abrindo: {url}")
    webbrowser.open(url)
    print(f"\n💡 No editor, você pode:")
    print(f"   • Editar texto direto nos slides (clica e digita)")
    print(f"   • Editar caption acima dos slides")
    print(f"   • Resetar pro original (botão ↺)")
    print(f"   • Exportar PNGs (download)")
    print(f"   • Enviar pro Telegram")
    print(f"   • Publicar direto no @omatheusdelucca")
    print(f"\n   Edições salvam automaticamente no localStorage do navegador.")
    return url


def main():
    parser = argparse.ArgumentParser(description="Roteiro .md → carrossel publicado no Instagram")
    parser.add_argument("roteiro_md", help="Caminho do arquivo .md do roteiro")
    parser.add_argument("--editor", action="store_true",
                        help="Abre editor visual interativo no browser pra ajustar antes de publicar")
    parser.add_argument("--no-launch", action="store_true",
                        help="Em modo --editor, só gera o HTML (não sobe servidor nem abre browser). Use quando o servidor é gerenciado externamente (preview_start).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Gera PNGs e mantém pra revisão, NÃO publica")
    parser.add_argument("--keep-images", action="store_true",
                        help="Salva PNGs em pasta permanente ao lado do .md")
    parser.add_argument("--output-dir", help="Pasta customizada pros PNGs")
    parser.add_argument("--no-publish", action="store_true",
                        help="Só gera PNGs, sem chamar publisher")
    parser.add_argument("--template", choices=list(EDITOR_TEMPLATES.keys()), default="ostentacao",
                        help="Template visual a usar (ostentacao=Direção C atual, stories=PT Serif sobre preto, clone do Bundas)")
    args = parser.parse_args()

    # Sobrescreve EDITOR_TEMPLATE e TEMPLATE_TOTAL_SLIDES com base no flag
    global EDITOR_TEMPLATE, TEMPLATE_TOTAL_SLIDES
    EDITOR_TEMPLATE = EDITOR_TEMPLATES[args.template]
    TEMPLATE_TOTAL_SLIDES = TEMPLATE_SLIDES_BY_NAME[args.template]
    print(f"   Template: {args.template} ({TEMPLATE_TOTAL_SLIDES} slides)")

    md_path = Path(args.roteiro_md).expanduser().resolve()
    if not md_path.exists():
        print(f"ERRO: arquivo não encontrado: {md_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\n📖 Lendo roteiro: {md_path.name}")
    parsed = parse_roteiro(md_path)
    print(f"   Título: {parsed['title']}")
    print(f"   Slides encontrados: {len(parsed['slides'])}")
    print(f"   Caption: {len(parsed['caption'])} caracteres")

    # Modo editor: abre HTML interativo e termina
    if args.editor:
        launch_editor(parsed, md_path, no_launch=args.no_launch)
        return

    # define output dir
    if args.output_dir:
        out_dir = Path(args.output_dir).expanduser().resolve()
    elif args.keep_images or args.dry_run or args.no_publish:
        # salva ao lado do .md numa subpasta
        out_dir = md_path.parent / f"{md_path.stem} - slides"
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="ig_slides_"))

    print(f"\n🖼️  Renderizando slides em: {out_dir}")
    images = render_all(parsed, out_dir)

    if args.no_publish:
        print(f"\n✅ {len(images)} slides gerados. Não foi feita publicação.")
        print(f"   Pasta: {out_dir}")
        return

    if args.dry_run:
        print(f"\n🔍 DRY RUN — simulando publicação sem postar de fato.")
        publish(images, parsed["caption"], dry_run=True)
        print(f"\n📁 PNGs mantidos em: {out_dir}")
        print(f"   Abre essa pasta pra revisar visualmente antes de publicar.")
        return

    # publicação real
    print(f"\n📤 Publicando @omatheusdelucca...")
    publish(images, parsed["caption"], dry_run=False)

    if not args.keep_images:
        # limpa temp se não for keep
        if out_dir.parent == Path(tempfile.gettempdir()):
            import shutil
            shutil.rmtree(out_dir)
            print(f"\n🧹 Slides temporários removidos.")
    else:
        print(f"\n💾 Slides salvos em: {out_dir}")


if __name__ == "__main__":
    main()
