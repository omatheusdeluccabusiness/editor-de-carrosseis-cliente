# Mesa de produção do editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganizar o shell dos editores Tweet e Stories como uma mesa de produção responsiva, preservando o canvas e os fluxos existentes.

**Architecture:** Cada template continua standalone e preserva seus IDs de integração. O HTML passa a usar `app-header`, `production-rail`, `editor-stage` e `inspector-panel`; uma pequena camada JavaScript deriva o trilho do estado já existente e sincroniza navegação e seleção.

**Tech Stack:** HTML, CSS e JavaScript vanilla embutidos nos templates, Python `unittest`, servidor HTTP local.

## Global Constraints

- Não alterar a aparência interna dos slides.
- Não alterar handlers, endpoints ou chaves de persistência existentes.
- Manter a porta `8777`.
- Não alterar `templates/ostentacao_editor.html`.
- Usar os tokens e famílias tipográficas registrados na especificação.
- Suportar desktop, tablet, mobile, teclado e movimento reduzido.

---

### Task 1: Contrato estrutural do shell

**Files:**
- Create: `tests/test_editor_shell.py`
- Test: `tests/test_editor_shell.py`

**Interfaces:**
- Consumes: `templates/tweet_editor.html`, `templates/stories_editor.html`.
- Produces: testes para estrutura, tokens, acessibilidade, responsividade, IDs únicos e trilho dinâmico.

- [ ] **Step 1: Escrever testes que exijam o novo shell**

Os testes devem exigir, nos dois templates: `app-header`, `production-rail`, `slide-rail-list`, `editor-stage`, `inspector-panel`, `inspector-section`, os seis tokens hexadecimais, `:focus-visible`, `prefers-reduced-motion`, media queries para `1100px` e `760px`, e as funções `buildSlideRail` e `setRailActive`.

- [ ] **Step 2: Verificar a falha inicial**

Run: `python3 -m unittest tests/test_editor_shell.py -v`

Expected: `FAIL` porque os templates ainda usam o toolbar centralizado e não possuem trilho ou inspetor.

### Task 2: Shell do Tweet

**Files:**
- Modify: `templates/tweet_editor.html`
- Test: `tests/test_editor_shell.py`

**Interfaces:**
- Consumes: `slidesState`, `activeSlideIndex`, `setActiveSlide(i)` e os IDs de ação existentes.
- Produces: `buildSlideRail() -> void`, `setRailActive(index: number) -> void`, itens `[data-rail-index]`.

- [ ] **Step 1: Adicionar tokens, fontes e CSS responsivo**

Adicionar variáveis CSS para os tokens, estilos de header, rail, stage e inspector, foco visível, breakpoints `1100px` e `760px`, e fallback para movimento reduzido.

- [ ] **Step 2: Reorganizar o markup sem trocar IDs**

Mover `btn-download-all` e `btn-publish-ig` para o header; `btn-add-slide` e `btn-delete-slide` para o rail; formato, tema, caption, Telegram e manutenção para o inspector; manter `wrap` no centro.

- [ ] **Step 3: Sincronizar trilho e seleção**

`buildSlideRail()` deve criar um botão por item de `slidesState`, rolar até `.slide-card` e chamar `setActiveSlide(index)`. `setActiveSlide` deve chamar `setRailActive`.

- [ ] **Step 4: Remover o ID duplicado de status**

Manter uma única ocorrência de `id="send-status"` e uma única ocorrência de `id="save-status"`.

- [ ] **Step 5: Rodar os testes focados**

Run: `python3 -m unittest tests/test_editor_shell.py -v`

Expected: Tweet passa; Stories permanece falhando.

### Task 3: Shell do Stories

**Files:**
- Modify: `templates/stories_editor.html`
- Test: `tests/test_editor_shell.py`

**Interfaces:**
- Consumes: `doc.slides`, `activeStageIndex`, `selectedSlideIdx` e `.slide-wrap`.
- Produces: `buildSlideRail() -> void`, `setRailActive(index: number) -> void`, itens `[data-rail-index]`.

- [ ] **Step 1: Aplicar a mesma linguagem visual do Tweet**

Adicionar tokens, fontes e shell claro, mantendo `#block-toolbar` como ferramenta contextual escura abaixo do header.

- [ ] **Step 2: Reorganizar ações no markup**

Mover exportação e publicação para o header; slide add/delete para o rail; tema, caption, Telegram, imagem ativa e manutenção para o inspector; manter `.grid` no centro.

- [ ] **Step 3: Sincronizar trilho com stages**

Construir os itens após `loadOrInitDoc()`. Clicar em um item deve ativar e rolar até `.stage`; clicar em um stage ou selecionar um bloco deve atualizar o item ativo.

- [ ] **Step 4: Rodar toda a suíte**

Run: `python3 -m unittest discover -s tests -v`

Expected: `OK`.

### Task 4: Regeneração e QA visual

**Files:**
- Regenerate: `/tmp/carrossel-editor/validacao-editor-final.html`
- Regenerate: `/tmp/carrossel-editor/teste-stories-10.html`

**Interfaces:**
- Consumes: os templates modificados.
- Produces: páginas servidas e verificadas em `localhost:8777`.

- [ ] **Step 1: Compilar Python e regenerar HTMLs**

Run: `python3 -m py_compile scripts/*.py`

Run Tweet: `python3 scripts/roteiro_to_instagram.py content/rascunhos/validacao-editor-final.md --editor --template tweet --no-launch`

Run Stories: `python3 scripts/roteiro_to_instagram.py content/rascunhos/teste-stories-10.md --editor --template stories --no-launch`

Expected: Tweet e Stories com 10 slides.

- [ ] **Step 2: Verificar desktop e mobile no navegador**

Desktop: `1440×1000`. Mobile: `390×844`. Confirmar header, rail, canvas, inspector, ausência de overflow horizontal e preservação dos controles internos.

- [ ] **Step 3: Verificar HTTP e suíte final**

Run: `curl -I http://localhost:8777/validacao-editor-final.html` e `curl -I http://localhost:8777/teste-stories-10.html`.

Run: `python3 -m unittest discover -s tests -v`

Expected: HTTP `200` e testes `OK`.

Não há etapa de commit porque esta pasta ainda não é um repositório Git.
