# Tweet Profile Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar ao inspector do Modelo Tweet edição persistente de foto, nome e arroba com paridade entre preview e PNG.

**Architecture:** O template mantém um único `profileState`, carregado de `tweet-editor-profile-v1`. O inspector atualiza esse estado e sincroniza todos os cabeçalhos DOM; a exportação passa os mesmos valores para `drawTweet()`. A foto é normalizada em canvas para um JPEG quadrado de 512 px antes da persistência.

**Tech Stack:** HTML, CSS e JavaScript sem framework; Python `unittest`; `localStorage`; Canvas 2D.

## Global Constraints

- A seção `Perfil` fica antes de `Documento` e segue o shell nativo existente.
- O estado interno de arroba nunca contém o prefixo `@`.
- O perfil é global no navegador e vale para todos os slides.
- Preview e exportação usam a mesma fonte de verdade.
- A foto persistida é JPEG 512×512, qualidade 0,88.
- Stories, publicação, Telegram, caption e conteúdo dos slides não mudam.
- A pasta não possui Git; não criar commits.

---

### Task 1: Contrato do inspector

**Files:**
- Modify: `tests/test_editor_shell.py`
- Modify: `templates/tweet_editor.html`

**Interfaces:**
- Produces: `#profile-avatar-preview`, `#profile-avatar-input`, `#profile-name`, `#profile-handle`.

- [ ] Escrever teste que exige a seção antes de `Documento`, labels e input de imagem.
- [ ] Rodar `python3 -m unittest tests.test_editor_shell.EditorShellTest.test_tweet_inspector_exposes_profile_controls -v` e confirmar falha.
- [ ] Adicionar markup e CSS do perfil ao inspector.
- [ ] Rodar o teste e confirmar sucesso.

### Task 2: Estado, persistência e sincronização

**Files:**
- Modify: `tests/test_editor_shell.py`
- Modify: `templates/tweet_editor.html`

**Interfaces:**
- Produces: `PROFILE_STORAGE_KEY`, `profileState`, `normalizeHandle(value)`, `loadProfileState()`, `saveProfileState()`, `syncProfileDOM()`, `setProfileAvatar(dataUrl)`.

- [ ] Escrever teste estático para a chave, funções e remoção dos valores fixos em `buildUI()` e `exportSlideToCanvas()`.
- [ ] Confirmar falha do teste.
- [ ] Implementar estado com defaults atuais e fallback seguro de storage.
- [ ] Fazer `buildUI()` e `exportSlideToCanvas()` consumirem `profileState`.
- [ ] Ligar os inputs a `syncProfileDOM()` sem reconstruir o editor.
- [ ] Rodar o teste e confirmar sucesso.

### Task 3: Normalização do avatar

**Files:**
- Modify: `tests/test_editor_shell.py`
- Modify: `templates/tweet_editor.html`

**Interfaces:**
- Produces: `normalizeAvatarFile(file): Promise<string>` e JPEG 512×512.

- [ ] Escrever teste para canvas 512, crop central, `toDataURL('image/jpeg', 0.88)` e tratamento de erro.
- [ ] Confirmar falha do teste.
- [ ] Implementar leitura por object URL, crop quadrado, encode e atualização de `avatarImg`.
- [ ] Rodar testes do shell e confirmar sucesso.

### Task 4: Verificação final

**Files:**
- Regenerate: `/tmp/carrossel-editor/validacao-editor-final.html`

**Interfaces:**
- Produces: editor servido em `http://localhost:8777/validacao-editor-final.html`.

- [ ] Rodar `python3 -m unittest discover -s tests -v`.
- [ ] Rodar `python3 -m py_compile scripts/*.py`.
- [ ] Regenerar o HTML Tweet.
- [ ] Validar `200` via HTTP.
- [ ] No navegador, alterar nome e arroba, confirmar todos os 10 slides, recarregar e confirmar persistência.
- [ ] Carregar avatar de teste, confirmar preview circular e estado persistido.
- [ ] Verificar 1440×1000 e 390×844 sem overflow horizontal.
