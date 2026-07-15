# Texto padrão dos slides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer todo slide vazio de Tweet ou Stories nascer com o texto exato `adicione aqui a sua copy`.

**Architecture:** O gerador Markdown passa a produzir 10 ou 17 parágrafos idênticos. O fatiador preserva esse placeholder curto sem agrupá-lo, enquanto mantém o agrupamento atual para copy real. Os templates usam a mesma frase ao adicionar slides, e uma migração pontual atualiza os cinco rascunhos existentes.

**Tech Stack:** Python 3, `unittest`, HTML/CSS/JavaScript estático, servidor HTTP local.

## Global Constraints

- O texto deve ser exatamente `adicione aqui a sua copy`, em minúsculas e sem ponto final.
- Títulos, frontmatter e captions existentes devem permanecer intactos.
- Tweet deve continuar gerando 10 slides e Stories, 17 slides.
- O template legado Ostentação fica fora do escopo.
- A porta local permanece `8777`.

---

### Task 1: Testes de regressão do placeholder

**Files:**
- Create: `tests/test_copy_padrao.py`
- Test: `tests/test_copy_padrao.py`

**Interfaces:**
- Consumes: `tweet_placeholder(title: str, date: str) -> str`, `stories_placeholder(title: str, date: str) -> str`, `_fatiar_roteiro_em_slides(roteiro_text: str, total_slides: int) -> list[dict]`.
- Produces: testes executáveis por `python3 -m unittest tests/test_copy_padrao.py -v`.

- [ ] **Step 1: Criar testes para conteúdo, contagem, templates e rascunhos**

O teste deve extrair `## Roteiro`, verificar 10 ocorrências no Tweet e 17 no Stories, exigir que o fatiador preserve cada ocorrência, exigir a frase no botão `+ Slide` dos dois templates e verificar os cinco arquivos atuais conforme o tipo do frontmatter.

- [ ] **Step 2: Executar e confirmar a falha correta**

Run: `python3 -m unittest tests/test_copy_padrao.py -v`

Expected: `FAIL`, mostrando que os placeholders atuais e o agrupamento de parágrafos curtos ainda não correspondem ao comportamento solicitado.

### Task 2: Padrão no gerador, parser e templates

**Files:**
- Modify: `scripts/novo_carrossel.py`
- Modify: `scripts/roteiro_to_instagram.py`
- Modify: `templates/tweet_editor.html`
- Modify: `templates/stories_editor.html`
- Test: `tests/test_copy_padrao.py`

**Interfaces:**
- Produces: `DEFAULT_SLIDE_COPY = "adicione aqui a sua copy"` em cada módulo Python que precisa reconhecer o valor.
- Preserva: assinaturas públicas existentes dos geradores e do fatiador.

- [ ] **Step 1: Gerar o roteiro padrão por repetição**

Em `tweet_placeholder`, montar exatamente 10 parágrafos de `DEFAULT_SLIDE_COPY`. Em `stories_placeholder`, montar exatamente 17. Manter frontmatter, H1 e caption atuais.

- [ ] **Step 2: Preservar o placeholder curto no fatiador**

Em `_coalesce_short_paragraphs`, retornar a lista sem agrupamento quando todos os parágrafos forem iguais a `DEFAULT_SLIDE_COPY`; manter o algoritmo atual nos demais roteiros.

- [ ] **Step 3: Atualizar o botão de novo slide**

Trocar `Texto do slide. Clica e edita.` por `adicione aqui a sua copy` em `tweet_editor.html` e `stories_editor.html`.

- [ ] **Step 4: Executar os testes focados**

Run: `python3 -m unittest tests/test_copy_padrao.py -v`

Expected: testes de gerador, parser e templates passam; os testes dos rascunhos permanecem falhando até a migração pontual.

### Task 3: Migrar rascunhos existentes

**Files:**
- Modify: `content/rascunhos/novo-carrossel-20260715-1753.md`
- Modify: `content/rascunhos/novo-tweet-20260715-1753.md`
- Modify: `content/rascunhos/teste-stories-17.md`
- Modify: `content/rascunhos/teste-tweet-10.md`
- Modify: `content/rascunhos/validacao-editor-final.md`
- Test: `tests/test_copy_padrao.py`

**Interfaces:**
- Consumes: contagem definida pelo campo `tipo` do frontmatter.
- Produces: seções `## Roteiro` com 10 blocos no Tweet e 17 no Stories.

- [ ] **Step 1: Substituir somente o bloco Roteiro**

Cada parágrafo do roteiro deve conter apenas `adicione aqui a sua copy`. Não alterar o H1, o frontmatter nem `## Caption Instagram`.

- [ ] **Step 2: Executar toda a suíte**

Run: `python3 -m unittest discover -s tests -v`

Expected: `OK`.

### Task 4: Regenerar e validar o editor servido

**Files:**
- Regenerate: `/tmp/carrossel-editor/*.html`
- Verify: `scripts/*.py`, `localhost:8777`

**Interfaces:**
- Consumes: os cinco rascunhos migrados e os templates modificados.
- Produces: HTMLs atuais acessíveis na porta `8777`.

- [ ] **Step 1: Compilar Python**

Run: `python3 -m py_compile scripts/*.py`

Expected: exit code `0` sem saída.

- [ ] **Step 2: Regenerar os cinco HTMLs sem abrir navegador**

Executar `scripts/roteiro_to_instagram.py` com `--editor --no-launch`, usando `--template tweet` para os três rascunhos Tweet e `--template stories` para os dois Stories.

- [ ] **Step 3: Validar conteúdo e HTTP**

Confirmar que cada HTML contém `adicione aqui a sua copy`, não contém `Reescreve` nem `Texto do slide. Clica e edita.`, e responde `200` em `http://localhost:8777`.

- [ ] **Step 4: Rodar a suíte final novamente**

Run: `python3 -m unittest discover -s tests -v`

Expected: `OK`.

Não há etapa de commit porque esta pasta ainda não é um repositório Git.
