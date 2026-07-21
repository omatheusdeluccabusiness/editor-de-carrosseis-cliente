# Undo Global dos Editores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer `Ctrl+Z`/`⌘Z` desfazer todas as mutações editoriais locais nos modelos Tweet e Stories.

**Architecture:** Cada template recebe um controlador autocontido que compara snapshots semânticos do estado persistido, guarda até 50 versões e espelha a pilha em `sessionStorage`. As funções de persistência existentes registram as transições; a restauração é feita no DOM quando a estrutura não muda e por reload quando muda a quantidade de slides.

**Tech Stack:** HTML, CSS, JavaScript vanilla, localStorage/sessionStorage, Python unittest.

## Global Constraints

- Cobrir Tweet e Stories; não alterar Ostentação.
- Atalhos: `Ctrl+Z` no Windows/Linux e `⌘Z` no macOS.
- Não implementar redo.
- Não tentar desfazer downloads, publicações, Telegram ou credenciais.
- Limitar a pilha a 50 snapshots e tolerar quota indisponível.

---

### Task 1: Contrato automatizado do undo

**Files:**
- Create: `tests/test_editor_undo.py`

**Interfaces:**
- Consumes: `templates/tweet_editor.html`, `templates/stories_editor.html`.
- Produces: contrato estático para `createUndoController`, `recordEditorMutation`, `undoEditorAction` e atalhos multiplataforma.

- [ ] **Step 1: Escrever testes inicialmente falhos**

Criar testes que exijam em ambos os templates:

```python
for marker in (
    "function createUndoController(options)",
    "function recordEditorMutation(reason)",
    "function undoEditorAction()",
    "sessionStorage",
    "UNDO_LIMIT = 50",
    "(e.metaKey || e.ctrlKey)",
):
    self.assertIn(marker, html)
```

Adicionar casos específicos para os campos do snapshot, restauração estrutural e ausência de integração com publicação/Telegram.

- [ ] **Step 2: Executar e confirmar RED**

Run: `python3 -m unittest tests.test_editor_undo -v`

Expected: FAIL porque o controlador ainda não existe.

- [ ] **Step 3: Commit dos testes junto da primeira implementação verde**

O commit ocorre no fim da Task 2, para não deixar a branch deliberadamente vermelha.

### Task 2: Histórico do Tweet

**Files:**
- Modify: `templates/tweet_editor.html`
- Test: `tests/test_editor_undo.py`

**Interfaces:**
- Consumes: `slidesState`, `profileState`, `currentTheme`, `currentRatio`, `saveState`, `saveProfileState`.
- Produces: `createUndoController(options)`, `recordEditorMutation(reason)`, `undoEditorAction()` e `armEditorUndo()`.

- [ ] **Step 1: Implementar controlador com deduplicação e persistência resiliente**

O controlador deve expor:

```javascript
const UNDO_LIMIT = 50;
function createUndoController(options) {
  return { arm, record, undo, resetBaseline };
}
```

`record()` compara o snapshot atual com o baseline, empilha o baseline quando mudou e persiste a pilha em `sessionStorage`, removendo entradas antigas se houver erro de quota.

- [ ] **Step 2: Integrar o snapshot Tweet**

Capturar `slides`, `profile`, `theme`, `ratio` e `caption`. Antes da captura, sincronizar o HTML dos corpos e os valores dos inputs com uma cópia, sem alterar a fonte de verdade.

- [ ] **Step 3: Registrar mutações**

Chamar `recordEditorMutation()` depois de persistir slides, perfil, tema, proporção e legenda. Para resets que removem storage diretamente, chamar `pushCurrentUndoSnapshot()` antes da remoção.

- [ ] **Step 4: Restaurar e religar a interface**

Em estados com o mesmo número de slides, atualizar variáveis, storage, texto, perfil, tema, proporção, imagens, rail e legenda no lugar. Se a contagem mudou, persistir o snapshot e executar `location.reload()`.

- [ ] **Step 5: Confirmar GREEN parcial**

Run: `python3 -m unittest tests.test_editor_undo -v`

Expected: testes comuns e Tweet passam; casos Stories continuam falhando.

- [ ] **Step 6: Commit**

```bash
git add tests/test_editor_undo.py templates/tweet_editor.html
git commit -m "Implementa undo global no editor Tweet"
```

### Task 3: Histórico do Stories

**Files:**
- Modify: `templates/stories_editor.html`
- Test: `tests/test_editor_undo.py`

**Interfaces:**
- Consumes: `doc`, `saveDoc`, `renderAll`, `buildSlideRail`, tema Stories e legenda.
- Produces: o mesmo contrato de undo autocontido usado no Tweet.

- [ ] **Step 1: Integrar o controlador e o snapshot Stories**

Capturar uma cópia profunda de `doc`, sobrepor os `innerHTML` vivos dos blocos e incluir tema e legenda.

- [ ] **Step 2: Registrar todas as mutações de documento**

Fazer `saveDoc()` registrar transições depois de salvar. Integrar tema, legenda e o reset que remove o documento diretamente. As mutações de texto, blocos, sliders, imagens, drag e zoom já convergem em `saveDoc()`.

- [ ] **Step 3: Restaurar o Stories**

Substituir `doc`, persistir sem criar novo histórico, reaplicar tema e legenda, limpar seleção, renderizar todos os slides e reconstruir o rail. Recarregar apenas quando a quantidade de slides mudar.

- [ ] **Step 4: Confirmar GREEN completo**

Run: `python3 -m unittest tests.test_editor_undo -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_editor_undo.py templates/stories_editor.html
git commit -m "Implementa undo global no editor Stories"
```

### Task 4: Auditoria integrada

**Files:**
- Verify: `templates/tweet_editor.html`
- Verify: `templates/stories_editor.html`
- Verify: `tests/test_editor_undo.py`

**Interfaces:**
- Consumes: os dois controladores concluídos.
- Produces: evidência de build, runtime e navegador.

- [ ] **Step 1: Executar a suíte completa e validações estáticas**

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py
bash -n start.sh stop.sh novo.sh configurar-credenciais.sh
git diff --check
```

- [ ] **Step 2: Gerar os dois editores**

```bash
python3 scripts/roteiro_to_instagram.py content/rascunhos/validacao-editor-final.md --editor --template tweet --no-launch
python3 scripts/roteiro_to_instagram.py content/rascunhos/validacao-editor-final.md --editor --template stories --no-launch
```

- [ ] **Step 3: Auditar no navegador**

No Tweet, editar texto, alternar tema e adicionar/excluir slide, desfazendo cada ação. No Stories, editar bloco, alterar tema e adicionar/excluir slide, desfazendo cada ação. Confirmar zero erros de console.

- [ ] **Step 4: Validar localhost e publicar**

Confirmar HTTP 200 em `localhost:8777`, enviar `main` ao GitHub e comparar SHA local/remoto.
