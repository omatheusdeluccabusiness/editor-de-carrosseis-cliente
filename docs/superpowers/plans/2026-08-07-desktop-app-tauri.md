# Desktop App Tauri Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar o Editor de Carrosseis como app desktop instalavel em macOS e Windows, com a janela nativa carregando o editor Python local ja validado.

**Architecture:** O backend atual continua sendo a unica fonte do editor. Um binario Python sidecar inicia em loopback e recebe diretorio de dados e configuracoes por ambiente. Uma casca Tauri inicia o sidecar, aguarda o health check, exibe `http://127.0.0.1:8777/` em uma janela nativa e o encerra quando o app fecha. PyInstaller empacota o sidecar por plataforma e GitHub Actions constroi artefatos em runners macOS/Windows.

**Tech Stack:** Python 3.10+, http.server, PyInstaller, Tauri 2, Rust, WebView2/WebKit, GitHub Actions.

## Global Constraints

- Manter somente Tweet e Stories como templates executaveis.
- Preservar exportacao PNG, Telegram, imagens, undo e o servidor loopback atual.
- O sidecar deve ouvir exclusivamente `127.0.0.1:8777`.
- Nenhum token, Chat ID, recovery key ou credencial Meta entra no binario, release ou Git.
- macOS e Windows exigem builds nativos separados; o workflow Windows deve gerar `.msi` e `.exe`.
- A primeira entrega nao inclui assinatura Apple, notarizacao, Authenticode, login, nuvem, historico ou sincronizacao.

---

## File Structure

- Create: `scripts/desktop_paths.py` — resolve diretorios de dados e credenciais por plataforma.
- Create: `scripts/desktop_sidecar.py` — entrypoint do servidor Python empacotado.
- Create: `scripts/build_sidecar.py` — comando reproduzivel de PyInstaller.
- Modify: `scripts/serve_carrossel.py` — health check e caminhos configuraveis do runtime desktop.
- Modify: `scripts/credenciais.py` — recebe raiz local de credenciais sem alterar o modo CLI existente.
- Create: `desktop/package.json` — scripts Tauri de desenvolvimento e build.
- Create: `desktop/src-tauri/Cargo.toml` — dependencias Rust da casca desktop.
- Create: `desktop/src-tauri/tauri.conf.json` — nome, icones, bundles e permissao de navegação loopback.
- Create: `desktop/src-tauri/src/main.rs` — inicia sidecar, aguarda health e fecha o filho.
- Create: `desktop/src-tauri/binaries/.gitkeep` — destino previsivel do sidecar local.
- Create: `.github/workflows/desktop-release.yml` — matrix macOS/Windows para artefatos privados.
- Create: `tests/test_desktop_runtime.py` — contratos do runtime e do sidecar.
- Create: `tests/test_desktop_packaging.py` — contratos do Tauri, PyInstaller e CI.
- Modify: `README.md` — instalacao e primeiro uso sem terminal.
- Modify: `.gitignore` — excluir binarios, bundles e dados locais do app.

## Task 1: Runtime local independente do shell

**Files:**
- Create: `scripts/desktop_paths.py`
- Modify: `scripts/serve_carrossel.py`
- Modify: `scripts/credenciais.py`
- Test: `tests/test_desktop_runtime.py`

**Interfaces:**
- Produces `desktop_runtime_paths(app_data_dir: str | None) -> RuntimePaths`.
- Produces `GET /api/health` com `{"ok": true, "service": "editor-carrosseis"}`.
- Consumes `CARROSSEL_APP_DATA_DIR` quando definido; sem a variavel preserva os caminhos CLI atuais.

- [ ] **Step 1: Write the failing tests**

```python
def test_desktop_paths_keep_runtime_and_credentials_out_of_project(tmp_path):
    paths = desktop_runtime_paths(str(tmp_path))
    assert paths.editor_dir == tmp_path / "sessions"
    assert paths.credentials_dir == tmp_path / "credentials"

def test_health_endpoint_is_loopback_safe():
    assert "/api/health" in serve_carrossel.CarrosselHandler.do_GET.__code__.co_consts
```

- [ ] **Step 2: Run the tests to verify failure**

Run: `./.venv/bin/python -m unittest tests.test_desktop_runtime -v`

Expected: FAIL because `desktop_paths` and `/api/health` do not exist.

- [ ] **Step 3: Implement paths and health check**

```python
@dataclass(frozen=True)
class RuntimePaths:
    editor_dir: Path
    credentials_dir: Path

def desktop_runtime_paths(app_data_dir: str | None) -> RuntimePaths:
    root = Path(app_data_dir).expanduser().resolve()
    return RuntimePaths(root / "sessions", root / "credentials")
```

In `serve_carrossel.py`, use `CARROSSEL_APP_DATA_DIR` only to derive the runtime paths and add a read-only `/api/health` branch before static file handling. Keep the default `DIR` and existing home-directory credential paths intact if the variable is absent.

- [ ] **Step 4: Run verification**

Run: `python3 -m py_compile scripts/*.py && ./.venv/bin/python -m unittest tests.test_desktop_runtime tests.test_hub_server -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/desktop_paths.py scripts/serve_carrossel.py scripts/credenciais.py tests/test_desktop_runtime.py
git commit -m "Prepara runtime local para app desktop"
```

## Task 2: Sidecar Python empacotavel

**Files:**
- Create: `scripts/desktop_sidecar.py`
- Create: `scripts/build_sidecar.py`
- Modify: `requirements.txt`
- Test: `tests/test_desktop_runtime.py`

**Interfaces:**
- `desktop_sidecar.main() -> int` inicia `serve_carrossel` com ambiente desktop.
- `build_sidecar.py --target-dir <path>` grava `editor-carrosseis-sidecar` ou `editor-carrosseis-sidecar.exe` no diretorio informado.
- Tauri executara o binario com `CARROSSEL_APP_DATA_DIR` definido.

- [ ] **Step 1: Write the failing tests**

```python
def test_sidecar_entrypoint_uses_loopback_and_healthcheck():
    source = (PROJECT_ROOT / "scripts/desktop_sidecar.py").read_text()
    assert "127.0.0.1" in source
    assert "CARROSSEL_APP_DATA_DIR" in source

def test_sidecar_builder_includes_templates_and_assets():
    source = (PROJECT_ROOT / "scripts/build_sidecar.py").read_text()
    assert "templates" in source
    assert "assets" in source
```

- [ ] **Step 2: Run the tests to verify failure**

Run: `./.venv/bin/python -m unittest tests.test_desktop_runtime -v`

Expected: FAIL because both entrypoints do not exist.

- [ ] **Step 3: Implement the sidecar and builder**

`desktop_sidecar.py` must import and run the same handler as `serve_carrossel.py`, read `CARROSSEL_APP_DATA_DIR`, set `CARROSSEL_EDITOR_DIR` to `<data>/sessions`, and not use the CLI supervisor.

`build_sidecar.py` must invoke PyInstaller in one-file mode with these data folders:

```python
datas = [
    (PROJECT_ROOT / "templates", "templates"),
    (PROJECT_ROOT / "assets", "assets"),
    (PROJECT_ROOT / "secrets" / "credentials.enc.json", "secrets"),
]
```

Add `pyinstaller>=6,<7` to `requirements.txt`. The generated executable is ignored by Git.

- [ ] **Step 4: Run a local smoke test**

Run: `./.venv/bin/python scripts/build_sidecar.py --target-dir /tmp/carrossel-sidecar && CARROSSEL_APP_DATA_DIR=/tmp/carrossel-desktop-data /tmp/carrossel-sidecar/editor-carrosseis-sidecar &`

Run: `curl -fsS http://127.0.0.1:8777/api/health`

Expected: JSON `{"ok": true, "service": "editor-carrosseis"}`.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt scripts/desktop_sidecar.py scripts/build_sidecar.py tests/test_desktop_runtime.py .gitignore
git commit -m "Adiciona sidecar Python do app desktop"
```

## Task 3: Casca Tauri com ciclo de vida do sidecar

**Files:**
- Create: `desktop/package.json`
- Create: `desktop/src-tauri/Cargo.toml`
- Create: `desktop/src-tauri/tauri.conf.json`
- Create: `desktop/src-tauri/src/main.rs`
- Create: `desktop/src-tauri/binaries/.gitkeep`
- Test: `tests/test_desktop_packaging.py`

**Interfaces:**
- O binario Tauri chama `start_sidecar(app_data_dir) -> Child`.
- `wait_for_health() -> Result<(), String>` tenta `http://127.0.0.1:8777/api/health` por no maximo 10 segundos.
- `RunEvent::ExitRequested` encerra o filho antes de o app finalizar.

- [ ] **Step 1: Write the failing tests**

```python
def test_tauri_configuration_uses_native_window_and_sidecar():
    config = json.loads((PROJECT_ROOT / "desktop/src-tauri/tauri.conf.json").read_text())
    assert config["productName"] == "Editor de Carrosseis"
    assert "externalBin" in config["bundle"]

def test_rust_shell_waits_for_health_and_stops_child():
    source = (PROJECT_ROOT / "desktop/src-tauri/src/main.rs").read_text()
    assert "/api/health" in source
    assert "ExitRequested" in source
```

- [ ] **Step 2: Run the tests to verify failure**

Run: `./.venv/bin/python -m unittest tests.test_desktop_packaging -v`

Expected: FAIL because the Tauri project does not exist.

- [ ] **Step 3: Implement the minimal native shell**

Use Tauri 2 with a splash HTML embedded as `frontendDist` that says `Abrindo Editor de Carrosseis…`. In Rust, determine `app.path().app_data_dir()`, spawn the external sidecar with `CARROSSEL_APP_DATA_DIR`, poll `/api/health`, then navigate the main webview to `http://127.0.0.1:8777/`. Register `on_window_event` and `RunEvent::ExitRequested` to kill the child process.

`tauri.conf.json` must list the binary basename under `bundle.externalBin`; do not add unrestricted HTTP permissions or any external navigation allowlist.

- [ ] **Step 4: Run development verification**

Run: `cd desktop && npm install && npm run tauri dev`

Expected: uma janela nativa abre o HUB; ao fechar a janela, `curl -fsS http://127.0.0.1:8777/api/health` falha porque o sidecar foi encerrado.

- [ ] **Step 5: Commit**

```bash
git add desktop tests/test_desktop_packaging.py
git commit -m "Adiciona casca Tauri do editor"
```

## Task 4: Bundles e verificacoes de release

**Files:**
- Create: `.github/workflows/desktop-release.yml`
- Modify: `desktop/package.json`
- Modify: `README.md`
- Test: `tests/test_desktop_packaging.py`

**Interfaces:**
- Workflow manual `workflow_dispatch` produz `Editor de Carrosseis.dmg` no macOS e instaladores `.msi` e `.exe` no Windows.
- O workflow nao recebe, imprime ou baixa credenciais em texto puro.

- [ ] **Step 1: Write the failing tests**

```python
def test_release_workflow_builds_each_platform_natively():
    workflow = (PROJECT_ROOT / ".github/workflows/desktop-release.yml").read_text()
    assert "macos-latest" in workflow
    assert "windows-latest" in workflow
    assert "desktop/src-tauri/binaries" in workflow
```

- [ ] **Step 2: Run the tests to verify failure**

Run: `./.venv/bin/python -m unittest tests.test_desktop_packaging -v`

Expected: FAIL because the release workflow does not exist.

- [ ] **Step 3: Implement native release jobs**

Each job must: checkout, install Python, install dependencies, run the Python suite, build the sidecar for its own runner, copy it to `desktop/src-tauri/binaries` with the suffix Tauri expects, install Node dependencies, run `npm run tauri build`, and upload only the produced bundle files as GitHub Actions artifacts.

Use `actions/upload-artifact@v4`; configure no release publishing and no repository secrets. Add `.gitignore` entries for `desktop/node_modules/`, `desktop/src-tauri/target/`, `desktop/src-tauri/binaries/editor-carrosseis-sidecar*`, `build/`, and `dist/`.

- [ ] **Step 4: Verify locally and statically**

Run: `./.venv/bin/python -m unittest tests.test_desktop_packaging -v && git check-ignore desktop/node_modules desktop/src-tauri/target`

Expected: PASS; ambos os caminhos de build sao ignorados.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/desktop-release.yml desktop/package.json README.md .gitignore tests/test_desktop_packaging.py
git commit -m "Automatiza instaladores desktop"
```

## Task 5: Documentacao de instalacao e qualidade final

**Files:**
- Modify: `README.md`
- Modify: `tests/test_packaging.py`
- Test: `tests/test_desktop_runtime.py`
- Test: `tests/test_desktop_packaging.py`

**Interfaces:**
- `README.md` oferece dois fluxos distintos: `Usar o app instalado` e `Desenvolver com Codex`.
- O fluxo instalado explica primeira abertura, restauracao da recovery key, exportacao e atualizacao sem expor segredos.

- [ ] **Step 1: Write the failing documentation test**

```python
def test_readme_documents_desktop_install_and_local_credentials():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "Aplicativo desktop" in readme
    assert "chave de recuperacao" in readme
    assert "Windows" in readme and "macOS" in readme
```

- [ ] **Step 2: Run the test to verify failure**

Run: `./.venv/bin/python -m unittest tests.test_packaging -v`

Expected: FAIL because the installed-app guide does not exist.

- [ ] **Step 3: Write the guide**

Document exactly: baixar o artefato da plataforma, instalar, abrir o app, inserir a recovery key apenas quando solicitada, verificar Telegram opcionalmente e atualizar instalando a versao nova. State that unsigned builds can show a system warning and that neither the app nor support should request Bot Token, Chat ID or Meta credentials by chat.

- [ ] **Step 4: Run the final verification**

Run: `python3 -m py_compile scripts/*.py && ./.venv/bin/python -m unittest discover -s tests -v && ./start.sh && curl -fsS http://127.0.0.1:8777/api/health && ./stop.sh`

Expected: suite PASS, health JSON valido e servidor encerrado.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_packaging.py tests/test_desktop_runtime.py tests/test_desktop_packaging.py
git commit -m "Documenta uso do app desktop"
```

## Self-review

- Spec coverage: tarefas 1 e 2 cobrem dados locais, credenciais, health e sidecar; tarefa 3 cobre a janela nativa e ciclo de vida; tarefa 4 cobre builds macOS/Windows; tarefa 5 cobre orientacao e verificacao final.
- Scope: nao inclui assinatura, publicacao em loja, login, nuvem, historico, sincronizacao ou novos templates.
- Type consistency: `CARROSSEL_APP_DATA_DIR`, `/api/health`, `desktop_runtime_paths`, `desktop_sidecar.main`, `start_sidecar` e `wait_for_health` usam os mesmos nomes em todas as tarefas.
- Safety: todos os artefatos sao compilados por plataforma e nenhum passo requer segredo de CI.
