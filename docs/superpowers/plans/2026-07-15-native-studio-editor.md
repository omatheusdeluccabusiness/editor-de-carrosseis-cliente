# Native Studio Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reestilizar o shell dos editores Tweet e Stories como um aplicativo criativo nativo, com tipografia próxima de SF Pro e sem alterar a lógica dos slides.

**Architecture:** Manter o HTML e JavaScript existentes e substituir apenas o sistema visual do shell por uma camada CSS compartilhada conceitualmente entre os dois templates. Os testes estáticos protegem tokens, tipografia, responsividade e contratos de IDs; a verificação no navegador cobre layout e interação reais.

**Tech Stack:** HTML, CSS, JavaScript sem framework, Python `unittest`, servidor HTTP local na porta 8777, Playwright para QA visual.

## Global Constraints

- A interface usa `-apple-system`, `BlinkMacSystemFont`, `"SF Pro Text"`, `"SF Pro Display"`, `Inter`, `sans-serif`.
- O shell usa `#F2F2F4`, `#FFFFFF`, `#F7F7F8`, `#1D1D1F`, `#6E6E73`, `#D2D2D7`, `#007AFF` e `#FF3B30`.
- O shell não carrega Barlow Condensed, Source Sans 3 ou IBM Plex Mono.
- O shell não usa amarelo como ação ou destaque.
- IDs, handlers, edição, exportação, publicação, Telegram e persistência existentes permanecem intactos.
- Não adicionar framework ou dependência de frontend.
- Não criar commits porque a pasta não é um repositório Git.

---

### Task 1: Contrato visual nativo

**Files:**
- Modify: `tests/test_editor_shell.py`

**Interfaces:**
- Consumes: conteúdo estático de `templates/tweet_editor.html` e `templates/stories_editor.html`.
- Produces: testes que exigem os tokens `--ui-*`, a pilha SF Pro, rótulos em sentence case e ausência das fontes/decoradores rejeitados.

- [ ] **Step 1: Substituir o teste do sistema visual antigo**

```python
def test_templates_use_native_visual_tokens_and_type_roles(self) -> None:
    required = (
        "#F2F2F4", "#FFFFFF", "#F7F7F8", "#1D1D1F",
        "#6E6E73", "#D2D2D7", "#007AFF", "#FF3B30",
        '"SF Pro Text"', '"SF Pro Display"', "-apple-system",
    )
    rejected = ("Barlow Condensed", "Source Sans 3", "IBM Plex Mono", "#F2B705")
    for template_path in TEMPLATES:
        html = template_path.read_text(encoding="utf-8")
        for marker in required:
            self.assertIn(marker, html)
        for marker in rejected:
            self.assertNotIn(marker, html)
```

- [ ] **Step 2: Adicionar testes de acabamento**

```python
def test_templates_have_native_shell_details(self) -> None:
    required = (
        "backdrop-filter: blur(20px)",
        "font-variant-numeric: tabular-nums",
        "border-left: 3px solid var(--ui-blue)",
        "transition: background-color 150ms ease",
    )
    for template_path in TEMPLATES:
        html = template_path.read_text(encoding="utf-8")
        for marker in required:
            self.assertIn(marker, html)
```

- [ ] **Step 3: Rodar os testes e confirmar a falha**

Run: `python3 -m unittest tests/test_editor_shell.py -v`

Expected: FAIL nos tokens antigos e nos detalhes nativos ausentes.

### Task 2: Shell nativo do editor Tweet

**Files:**
- Modify: `templates/tweet_editor.html:5-375`
- Test: `tests/test_editor_shell.py`

**Interfaces:**
- Consumes: classes `.app-header`, `.production-rail`, `.editor-stage`, `.inspector-panel`, `.rail-item`, `.shell-button` e IDs existentes.
- Produces: shell Tweet responsivo com a mesma estrutura e handlers.

- [ ] **Step 1: Remover imports de fontes web do shell**

Remover os três elementos de preconnect/stylesheet do Google Fonts e usar exclusivamente a pilha definida nos Global Constraints.

- [ ] **Step 2: Substituir tokens e tipografia**

```css
:root {
  --ui-canvas: #F2F2F4;
  --ui-surface: #FFFFFF;
  --ui-surface-muted: #F7F7F8;
  --ui-text: #1D1D1F;
  --ui-text-secondary: #6E6E73;
  --ui-line: #D2D2D7;
  --ui-blue: #007AFF;
  --ui-blue-soft: rgba(0, 122, 255, 0.10);
  --ui-danger: #FF3B30;
  --ui-font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", Inter, sans-serif;
}
```

- [ ] **Step 3: Reestilizar cabeçalho, sidebar e inspector**

Aplicar superfície contínua branca, divisórias de 1 px, controles de 32–36 px, títulos em sentence case e seleção com `border-left: 3px solid var(--ui-blue)`. O botão `Publicar` usa azul e `Exportar PNGs` usa superfície neutra.

- [ ] **Step 4: Reestilizar área de trabalho e toolbar do slide**

Remover moldura azul do cartão ativo, usar canvas `--ui-canvas`, sombra suave apenas no slide e toolbar branca compacta abaixo do canvas.

- [ ] **Step 5: Preservar responsividade**

Manter breakpoints `1100px` e `760px`, faixa horizontal de slides e `updateTweetPreviewScale()`.

- [ ] **Step 6: Rodar o teste do shell**

Run: `python3 -m unittest tests/test_editor_shell.py -v`

Expected: Tweet atende aos novos marcadores; Stories ainda falha.

### Task 3: Shell nativo do editor Stories

**Files:**
- Modify: `templates/stories_editor.html:5-668`
- Test: `tests/test_editor_shell.py`

**Interfaces:**
- Consumes: o mesmo contrato visual e classes do Task 2.
- Produces: paridade visual entre Stories e Tweet sem alterar o canvas serifado dos Stories.

- [ ] **Step 1: Manter apenas PT Serif como fonte externa do conteúdo do slide**

Alterar o link do Google Fonts para carregar somente `PT Serif`; o shell usa `--ui-font`.

- [ ] **Step 2: Aplicar os mesmos tokens e componentes do Tweet**

Replicar o sistema `--ui-*`, dimensões, sidebars contínuas, seleção azul, botões compactos e inspector branco.

- [ ] **Step 3: Preservar comportamentos exclusivos**

Manter `#block-toolbar.empty { display: none; }`, posicionar a toolbar selecionada abaixo do cabeçalho e preservar o canvas preto/serifado de Stories.

- [ ] **Step 4: Rodar o teste do shell**

Run: `python3 -m unittest tests/test_editor_shell.py -v`

Expected: todos os testes do shell passam.

### Task 4: Regeneração e QA real

**Files:**
- Regenerate: `/tmp/carrossel-editor/validacao-editor-final.html`
- Regenerate: `/tmp/carrossel-editor/teste-stories-17.html`

**Interfaces:**
- Consumes: templates finais e rascunhos existentes.
- Produces: páginas servidas e visualmente verificadas em `localhost:8777`.

- [ ] **Step 1: Rodar a suíte e compilação**

Run: `python3 -m unittest discover -s tests -v`

Expected: 12 ou mais testes, zero falhas.

Run: `python3 -m py_compile scripts/*.py`

Expected: exit 0 sem saída.

- [ ] **Step 2: Regenerar Tweet e Stories**

Run: `python3 scripts/roteiro_to_instagram.py content/rascunhos/validacao-editor-final.md --editor --template tweet --no-launch`

Run: `python3 scripts/roteiro_to_instagram.py content/rascunhos/teste-stories-17.md --editor --template stories --no-launch`

Expected: HTMLs gerados em `/tmp/carrossel-editor`.

- [ ] **Step 3: Validar HTTP**

Run: `curl -I http://localhost:8777/validacao-editor-final.html`

Run: `curl -I http://localhost:8777/teste-stories-17.html`

Expected: `HTTP/1.0 200 OK` nos dois endereços.

- [ ] **Step 4: Verificar desktop, tablet e mobile no navegador**

Em 1440×1000, 1024×900 e 390×844, confirmar ausência de overflow horizontal, contagem correta dos slides, seleção do roteiro, toolbar de Stories e escala móvel do Tweet. Capturar screenshots de Tweet e Stories para autocrítica visual.

- [ ] **Step 5: Criticar e remover um excesso visual**

Comparar as screenshots com a especificação. Se algum adorno, borda ou rótulo competir com o canvas, removê-lo e repetir testes e screenshots.
