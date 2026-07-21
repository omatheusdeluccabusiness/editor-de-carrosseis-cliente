# Tweet Neon Highlights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar ao editor Tweet um marca-texto contextual com quatro cores semânticas, persistência segura e renderização adaptativa nos temas claro e escuro, incluindo o PNG exportado.

**Architecture:** A feature permanece autocontida em `templates/tweet_editor.html`. O texto rico continua persistido em `slidesState[index].text`, usando `[hl=color]...[/hl]`; o DOM usa `<mark data-highlight="color">`; e o canvas recebe segmentos `{ text, bold, highlight }` medidos a partir do DOM real. Testes Python verificam os contratos estáticos e a validação final exercita o fluxo real no navegador.

**Tech Stack:** HTML, CSS, JavaScript sem dependências, Canvas 2D, Selection/Range API, Python `unittest`.

## Global Constraints

- Somente `templates/tweet_editor.html` recebe a feature; `Stories` e `Ostentação` permanecem inalterados.
- Cores persistidas aceitas: `yellow`, `pink`, `green`, `blue`.
- A UI deve adaptar-se automaticamente a `light` e `dark` sem regravar o texto.
- O PNG deve usar as mesmas cores semânticas e quebras de linha da pré-visualização.
- Negrito, quebras e realce devem coexistir.
- Nenhuma dependência JavaScript será adicionada.
- Cada alteração de produção começa com um teste falhando.

---

### Task 1: Contrato visual e serialização segura

**Files:**
- Create: `tests/test_tweet_highlights.py`
- Modify: `templates/tweet_editor.html`

**Interfaces:**
- Consumes: `escapeHtml(s)`, `markdownToHtml(text)`, `htmlToMarkdown(html)`, `currentTheme`.
- Produces: `HIGHLIGHT_COLORS`, `HIGHLIGHT_THEME_COLORS`, `normalizeHighlightColor(value)`, DOM canônico `<mark data-highlight>`, sintaxe persistida `[hl=color]...[/hl]` e `#tweet-highlight-menu`.

- [ ] **Step 1: Escrever testes falhando para o contrato visual e de persistência**

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
TWEET = ROOT / "templates" / "tweet_editor.html"

class TweetHighlightsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = TWEET.read_text(encoding="utf-8")

    def test_contextual_palette_is_accessible(self):
        for marker in (
            'id="tweet-highlight-menu"', 'role="toolbar"',
            'aria-label="Cores do marca-texto"', 'data-highlight-color="yellow"',
            'data-highlight-color="pink"', 'data-highlight-color="green"',
            'data-highlight-color="blue"', 'data-highlight-action="clear"',
        ):
            self.assertIn(marker, self.html)

    def test_highlights_use_semantic_theme_maps(self):
        for marker in (
            "const HIGHLIGHT_COLORS = ['yellow', 'pink', 'green', 'blue']",
            "const HIGHLIGHT_THEME_COLORS = {", "light:", "dark:",
            "function normalizeHighlightColor(value)",
            "body.theme-dark .tweet-render mark[data-highlight]",
        ):
            self.assertIn(marker, self.html)

    def test_serialization_contract_is_limited(self):
        for marker in (
            "[hl=", "[/hl]", "data-highlight", "parseRichTextMarkdown",
            "serializeRichTextDOM", "normalizeHighlightColor",
        ):
            self.assertIn(marker, self.html)
```

- [ ] **Step 2: Executar os testes e confirmar falha pelo contrato ausente**

Run: `python3 -m unittest tests.test_tweet_highlights -v`

Expected: `FAIL` porque `tweet-highlight-menu`, mapas de tema e helpers ainda não existem.

- [ ] **Step 3: Adicionar tokens CSS, paleta acessível e conversores canônicos**

Adicionar quatro variáveis claras e quatro escuras, estilos de `mark`, estilos da paleta fixa e o HTML:

```html
<div id="tweet-highlight-menu" class="tweet-highlight-menu" role="toolbar"
     aria-label="Cores do marca-texto" aria-hidden="true">
  <button type="button" data-highlight-color="yellow" aria-label="Marca-texto amarelo"></button>
  <button type="button" data-highlight-color="pink" aria-label="Marca-texto rosa"></button>
  <button type="button" data-highlight-color="green" aria-label="Marca-texto verde"></button>
  <button type="button" data-highlight-color="blue" aria-label="Marca-texto azul"></button>
  <button type="button" data-highlight-action="clear" aria-label="Remover realce">Remover</button>
</div>
```

Substituir os conversores regex por wrappers de API estável:

```javascript
const HIGHLIGHT_COLORS = ['yellow', 'pink', 'green', 'blue'];
const HIGHLIGHT_THEME_COLORS = {
  light: { yellow: 'rgba(255, 228, 94, 0.82)', pink: 'rgba(255, 122, 200, 0.76)', green: 'rgba(128, 226, 126, 0.76)', blue: 'rgba(100, 216, 255, 0.76)' },
  dark: { yellow: 'rgba(172, 129, 0, 0.78)', pink: 'rgba(145, 35, 88, 0.76)', green: 'rgba(24, 108, 64, 0.78)', blue: 'rgba(16, 94, 132, 0.80)' }
};
function normalizeHighlightColor(value) {
  return HIGHLIGHT_COLORS.includes(value) ? value : null;
}
function parseRichTextMarkdown(text) {
  let value = escapeHtml(text || '');
  value = value.replace(/^[ \t]*\*\*[ \t]*$/gm, '');
  value = value.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
  value = value.replace(/\*\*/g, '');
  value = value.replace(/\[hl=(yellow|pink|green|blue)\]([\s\S]*?)\[\/hl\]/g,
    '<mark data-highlight="$1">$2</mark>');
  return value.replace(/\n/g, '<br>').replace(/(<br>\s*){3,}/g, '<br><br>');
}
function serializeRichTextDOM(html) {
  const root = document.createElement('div');
  root.innerHTML = html || '';
  function visit(node) {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent || '';
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    const tag = node.tagName.toUpperCase();
    if (tag === 'BR') return '\n';
    let content = Array.from(node.childNodes, visit).join('');
    if (tag === 'STRONG' || tag === 'B') content = '**' + content + '**';
    if (tag === 'MARK') {
      const color = normalizeHighlightColor(node.dataset.highlight);
      if (color) content = '[hl=' + color + ']' + content + '[/hl]';
    }
    if (tag === 'DIV' || tag === 'P') content = '\n' + content;
    return content;
  }
  return Array.from(root.childNodes, visit).join('')
    .replace(/\u00a0/g, ' ').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n');
}
function markdownToHtml(text) { return parseRichTextMarkdown(text); }
function htmlToMarkdown(html) { return serializeRichTextDOM(html); }
```

- [ ] **Step 4: Executar o teste focal e a suíte existente**

Run: `python3 -m unittest tests.test_tweet_highlights tests.test_editor_shell -v`

Expected: todos os testes passam.

- [ ] **Step 5: Commitar o contrato visual e de serialização**

```bash
git add tests/test_tweet_highlights.py templates/tweet_editor.html
git commit -m "Adiciona base semântica do realce Tweet"
```

---

### Task 2: Seleção contextual, aplicação e remoção

**Files:**
- Modify: `tests/test_tweet_highlights.py`
- Modify: `templates/tweet_editor.html`

**Interfaces:**
- Consumes: `#tweet-highlight-menu`, `normalizeHighlightColor`, `htmlToMarkdown`, `slidesState`, `saveState()`, `applyLayout(index)`.
- Produces: `getTweetBodyForRange(range)`, `showHighlightMenu(range)`, `hideHighlightMenu()`, `applyHighlightToSavedRange(color)`, `clearHighlightFromSavedRange()` e listeners de seleção/teclado.

- [ ] **Step 1: Acrescentar testes falhando para seleção e comandos**

```python
def test_selection_controller_has_bounded_range_and_commands(self):
    for marker in (
        "function getTweetBodyForRange(range)",
        "function showHighlightMenu(range)",
        "function hideHighlightMenu()",
        "function applyHighlightToSavedRange(color)",
        "function clearHighlightFromSavedRange()",
        "document.addEventListener('selectionchange'",
        "e.key === 'Escape'",
        "range.cloneRange()",
        "range.extractContents()",
    ):
        self.assertIn(marker, self.html)

def test_commands_resync_slide_state(self):
    for marker in (
        "syncHighlightedBody(bodyEl)",
        "slidesState[index].text = htmlToMarkdown(bodyEl.innerHTML)",
        "saveState()",
        "applyLayout(index)",
    ):
        self.assertIn(marker, self.html)
```

- [ ] **Step 2: Executar e confirmar falha por funções ausentes**

Run: `python3 -m unittest tests.test_tweet_highlights -v`

Expected: `FAIL` nos dois novos testes.

- [ ] **Step 3: Implementar o controlador de seleção**

Implementar um único menu global. `getTweetBodyForRange` retorna o `.body`
somente quando os dois limites do range pertencem ao mesmo corpo. O menu salva
`range.cloneRange()`, calcula posição por `getBoundingClientRect()`, limita
`left/top` à viewport e restaura o range em `mousedown` antes do comando.

Aplicação usa `range.extractContents()`, remove `<mark>` internos do fragmento,
envolve o fragmento em `<mark data-highlight="...">` e normaliza marcas
adjacentes da mesma cor. Remoção divide marcas nos limites da seleção, extrai o
fragmento, remove somente `<mark>` e reinsere o conteúdo. Ambos chamam:

```javascript
function syncHighlightedBody(bodyEl) {
  const index = Number(bodyEl.id.replace('body-', ''));
  if (!Number.isInteger(index) || !slidesState[index]) return;
  slidesState[index].text = htmlToMarkdown(bodyEl.innerHTML);
  saveState();
  applyLayout(index);
}
```

Conectar os quatro botões, a remoção, `selectionchange`, `resize`, `scroll` e
`Escape`. Usar `mousedown.preventDefault()` para não perder a seleção.

- [ ] **Step 4: Executar testes focais e a suíte completa**

Run: `python3 -m unittest tests.test_tweet_highlights -v && python3 -m unittest discover -s tests -v`

Expected: todos os testes passam.

- [ ] **Step 5: Commitar a interação contextual**

```bash
git add tests/test_tweet_highlights.py templates/tweet_editor.html
git commit -m "Implementa seleção e paleta de realce Tweet"
```

---

### Task 3: Paridade do canvas, temas e auditoria final

**Files:**
- Modify: `tests/test_tweet_highlights.py`
- Modify: `templates/tweet_editor.html`

**Interfaces:**
- Consumes: `HIGHLIGHT_THEME_COLORS`, `getLineSegmentsFromDOM(bodyEl)`, `drawTweet(...)`, `currentTheme`.
- Produces: segmentos `{ text, bold, highlight }`, `drawMarkerStroke(ctx, x, y, width, fontSize, color)` e pintura anterior a `ctx.fillText`.

- [ ] **Step 1: Acrescentar testes falhando para segmentos e canvas**

```python
def test_dom_segments_carry_highlight_identity(self):
    for marker in (
        "{ text: ch, bold: isBold, highlight: highlightColor }",
        "const newHighlight = tag === 'MARK'",
        "walk(child, newBold, newHighlight)",
    ):
        self.assertIn(marker, self.html)

def test_canvas_draws_theme_marker_before_text(self):
    for marker in (
        "function drawMarkerStroke(ctx, x, y, width, fontSize, color)",
        "HIGHLIGHT_THEME_COLORS[dark ? 'dark' : 'light']",
        "drawMarkerStroke(ctx, x, y, segmentWidth, fontSize, markerColor)",
    ):
        self.assertIn(marker, self.html)
    self.assertLess(
        self.html.index("drawMarkerStroke(ctx, x, y, segmentWidth"),
        self.html.index("ctx.fillText(seg.text, x, y)")
    )
```

- [ ] **Step 2: Executar e confirmar falha pelo pipeline incompleto**

Run: `python3 -m unittest tests.test_tweet_highlights -v`

Expected: `FAIL` porque segmentos e canvas ainda não conhecem realces.

- [ ] **Step 3: Propagar a cor e desenhar o traço determinístico**

Alterar `getLineSegmentsFromDOM` para carregar `highlight` no estado recursivo e
abrir segmento novo quando `bold` ou `highlight` mudar. O fallback de
`drawTweet` também interpreta `[hl=color]...[/hl]`.

Adicionar:

```javascript
function drawMarkerStroke(ctx, x, y, width, fontSize, color) {
  if (!color || width <= 0) return;
  const top = y + fontSize * 0.30;
  const bottom = y + fontSize * 1.08;
  const pad = Math.max(3, fontSize * 0.08);
  ctx.save();
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x - pad, top + 1);
  ctx.lineTo(x + width + pad, top - 1);
  ctx.lineTo(x + width + pad * 0.7, bottom + 1);
  ctx.lineTo(x - pad * 0.8, bottom - 1);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}
```

No loop de cada linha, medir `segmentWidth`, resolver a cor pelo tema, desenhar
`drawMarkerStroke` e somente depois executar `fillText`. O DOM usa gradientes
lineares e `box-decoration-break: clone` com os mesmos tokens temáticos.

- [ ] **Step 4: Executar verificações automatizadas completas**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py
bash -n start.sh stop.sh novo.sh configurar-credenciais.sh
git diff --check
```

Expected: todos os comandos terminam com código `0`.

- [ ] **Step 5: Regenerar, servir e auditar o fluxo real**

Run:

```bash
./novo.sh tweet
./start.sh
curl -fsS -o /dev/null -w '%{http_code} %{content_type}\n' http://localhost:8777
```

Expected: `200 text/html`.

No navegador, validar: seleção, quatro cores, remoção, negrito combinado,
quebra de linha, atualização da página, troca claro/escuro e PNG exportado.

- [ ] **Step 6: Commitar a paridade de exportação**

```bash
git add tests/test_tweet_highlights.py templates/tweet_editor.html
git commit -m "Renderiza realce adaptativo no PNG Tweet"
```

- [ ] **Step 7: Auditar o diff final contra a especificação**

Run:

```bash
git diff main...HEAD -- templates/tweet_editor.html tests/test_tweet_highlights.py
git status --short
```

Expected: apenas os arquivos planejados, mais este plano e a especificação já
aprovada; nenhuma alteração em Stories, Ostentação, credenciais ou publicação.
