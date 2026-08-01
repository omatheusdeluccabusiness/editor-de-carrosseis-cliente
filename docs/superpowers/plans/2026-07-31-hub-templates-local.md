# HUB Local de Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar um HUB local em `localhost:8777` no qual clientes criam sessões novas dos templates oficiais Tweet e Stories, ambos com 10 slides, exportação PNG e Telegram, sem histórico e sem o legado Ostentação.

**Architecture:** Preservar os editores HTML atuais e adicionar uma camada fina de catálogo, sessões temporárias e página inicial. O servidor valida o template escolhido, reutiliza o gerador atual num subprocesso e cria HTMLs efêmeros prefixados com `hub-`; o modo HUB é injetado no HTML para oferecer retorno seguro e ocultar publicação no Instagram sem alterar o fluxo técnico direto.

**Tech Stack:** Python 3.9+ com biblioteca padrão, HTML/CSS/JavaScript sem framework, `unittest`, servidor local `http.server`, armazenamento temporário em `/tmp/carrossel-editor`.

## Global Constraints

- Preservar a porta local `8777`.
- Tweet e Stories começam com exatamente 10 slides e continuam permitindo adicionar ou remover slides.
- O fluxo do HUB não cria Markdown em `content/rascunhos/`.
- Uma criação nova nunca recupera conteúdo de outra sessão.
- Recarregar a sessão atual preserva a edição em andamento.
- Exportação PNG e envio ao Telegram permanecem operantes.
- O HUB não oferece publicação direta no Instagram.
- Credenciais e configurações pessoais permanecem fora do Git.
- Não introduzir framework frontend, banco de dados, login, histórico ou dependência de outro workspace.
- Cada tarefa termina com teste e commit próprios.

---

## File Map

- `scripts/template_catalog.py`: única fonte dos templates oficiais e seus metadados.
- `scripts/hub_sessions.py`: criação, identificação e limpeza das sessões efêmeras.
- `scripts/roteiro_to_instagram.py`: parser/gerador existente; passa a consumir o catálogo e aceitar modo HUB.
- `scripts/novo_carrossel.py`: placeholders técnicos existentes; ambos passam a gerar 10 slides.
- `scripts/serve_carrossel.py`: serve o HUB em `/` e cria sessões por `POST /api/sessoes`.
- `templates/hub.html`: interface enxuta do catálogo e início de criação.
- `templates/tweet_editor.html`: editor validado; recebe somente integração de retorno ao HUB e ocultação contextual do Instagram.
- `templates/stories_editor.html`: editor validado; recebe somente integração de retorno ao HUB e ocultação contextual do Instagram.
- `tests/test_template_catalog.py`: contrato do catálogo e ausência do legado.
- `tests/test_hub_sessions.py`: geração limpa, unicidade e limpeza de sessões.
- `tests/test_hub_server.py`: contrato HTTP da raiz e da criação de sessões.
- `tests/test_hub_editor_mode.py`: modo HUB nos dois editores sem regressão do modo técnico.
- `tests/test_copy_padrao.py`: contagem inicial de 10 slides.
- `tests/test_editor_shell.py`: controles compartilhados do shell.
- `tests/test_editor_undo.py`: contrato de undo apenas dos editores ativos.
- `content/rascunhos/teste-stories-10.md`: fixture Stories atualizada.
- `AGENTS.md` e `README.md`: operação do produto e regras atuais.
- Delete `templates/ostentacao_editor.html`: remoção do template legado.
- Delete `content/rascunhos/teste-stories-17.md`: remoção da fixture antiga.

---

### Task 1: Normalizar Stories para 10 slides

**Files:**
- Modify: `scripts/novo_carrossel.py:61-81`
- Modify: `scripts/roteiro_to_instagram.py:318-321, 651-652, 787`
- Modify: `tests/test_copy_padrao.py:31-73`
- Create: `content/rascunhos/teste-stories-10.md`
- Delete: `content/rascunhos/teste-stories-17.md`
- Modify: `content/rascunhos/novo-carrossel-20260715-1753.md`

**Interfaces:**
- Consumes: `default_roteiro(total_slides: int) -> str`.
- Produces: `stories_placeholder(title: str, date: str) -> str` com 10 parágrafos e `TEMPLATE_SLIDES_BY_NAME["stories"] == 10`.

- [ ] **Step 1: Alterar o teste de placeholder para exigir 10 slides**

```python
def test_stories_placeholder_has_ten_identical_slides(self) -> None:
    markdown = novo_carrossel.stories_placeholder("Título", "2026-07-31")
    self.assertEqual(roteiro_blocks(markdown), [DEFAULT_COPY] * 10)
```

Atualizar também `expected_counts` para usar `teste-stories-10.md: 10` e `novo-carrossel-20260715-1753.md: 10`.

- [ ] **Step 2: Rodar o teste e confirmar a falha esperada**

Run: `python3 -m unittest tests.test_copy_padrao.DefaultCopyTest.test_stories_placeholder_has_ten_identical_slides -v`

Expected: FAIL mostrando 17 blocos em vez de 10.

- [ ] **Step 3: Aplicar a contagem 10 ao placeholder e ao gerador**

```python
def stories_placeholder(title: str, date: str) -> str:
    roteiro = default_roteiro(10)
```

```python
TEMPLATE_SLIDES_BY_NAME = {"stories": 10, "tweet": 10}
```

Atualizar os comentários de fatiamento e schema para não mencionarem 17 slides.

- [ ] **Step 4: Substituir as fixtures Stories por versões de 10 blocos**

Criar `content/rascunhos/teste-stories-10.md` com o mesmo frontmatter e caption da fixture anterior, título `teste-stories-10` e exatamente 10 parágrafos `adicione aqui a sua copy`. Reduzir `novo-carrossel-20260715-1753.md` para os mesmos 10 parágrafos.

- [ ] **Step 5: Rodar testes de contagem e geração**

Run: `python3 -m unittest tests.test_copy_padrao -v`

Run: `python3 scripts/roteiro_to_instagram.py content/rascunhos/teste-stories-10.md --editor --template stories --no-launch`

Expected: testes PASS e saída `Template: stories (10 slides)`.

- [ ] **Step 6: Commit**

```bash
git add scripts/novo_carrossel.py scripts/roteiro_to_instagram.py tests/test_copy_padrao.py content/rascunhos/teste-stories-10.md content/rascunhos/teste-stories-17.md content/rascunhos/novo-carrossel-20260715-1753.md
git commit -m "Normaliza Stories para dez slides"
```

---

### Task 2: Remover o modo Ostentação do runtime

**Files:**
- Modify: `scripts/roteiro_to_instagram.py:644-652, 787-815, 900-995`
- Modify: `tests/test_editor_undo.py:94-99`
- Create: `tests/test_template_catalog.py`
- Delete: `templates/ostentacao_editor.html`

**Interfaces:**
- Consumes: mapas `EDITOR_TEMPLATES` e `TEMPLATE_SLIDES_BY_NAME` ainda locais nesta tarefa.
- Produces: CLI com escolhas exclusivas `tweet|stories`, default `tweet` e chave de documento sem identificador legado.

- [ ] **Step 1: Escrever o teste de remoção do legado**

```python
class ActiveTemplatesTest(unittest.TestCase):
    def test_only_tweet_and_stories_are_executable(self) -> None:
        self.assertEqual(set(roteiro_to_instagram.EDITOR_TEMPLATES), {"tweet", "stories"})
        self.assertEqual(roteiro_to_instagram.TEMPLATE_SLIDES_BY_NAME, {"tweet": 10, "stories": 10})
        self.assertFalse((PROJECT_ROOT / "templates" / "ostentacao_editor.html").exists())

    def test_generator_source_has_no_legacy_runtime_identifier(self) -> None:
        source = (PROJECT_ROOT / "scripts" / "roteiro_to_instagram.py").read_text(encoding="utf-8")
        self.assertNotIn("ostentacao", source.lower())
```

Remover `test_legacy_editor_stays_out_of_scope` de `tests/test_editor_undo.py`; a ausência do arquivo será coberta pelo novo teste.

- [ ] **Step 2: Rodar o teste e confirmar a falha esperada**

Run: `python3 -m unittest tests.test_template_catalog.ActiveTemplatesTest -v`

Expected: FAIL porque o mapa e o arquivo legado ainda existem.

- [ ] **Step 3: Remover o template e limpar o gerador**

```python
EDITOR_TEMPLATES = {
    "stories": TEMPLATE_DIR / "stories_editor.html",
    "tweet": TEMPLATE_DIR / "tweet_editor.html",
}
EDITOR_TEMPLATE = EDITOR_TEMPLATES["tweet"]
TEMPLATE_TOTAL_SLIDES = 10
TEMPLATE_SLIDES_BY_NAME = {"stories": 10, "tweet": 10}
```

```python
SCHEMA_VERSION = "v6"

def _make_doc_key(roteiro_md: Path, content_hash: str = "") -> str:
    base = slugify(roteiro_md.stem)
    h = content_hash[:10] if content_hash else "v1"
    return f"carrossel-editor-{base}-{SCHEMA_VERSION}-{h}"
```

Alterar o argumento CLI para `default="tweet"` e help limitado a Tweet e Stories. Excluir `templates/ostentacao_editor.html`.

- [ ] **Step 4: Rodar a suíte relevante e procurar referências executáveis**

Run: `python3 -m unittest tests.test_template_catalog tests.test_editor_undo -v`

Run: `rg -n -i 'ostentacao' scripts templates tests AGENTS.md README.md`

Expected: testes PASS; `rg` pode apontar a asserção negativa do próprio teste e documentação ainda pendente, nunca código executável ou template.

- [ ] **Step 5: Commit**

```bash
git add scripts/roteiro_to_instagram.py tests/test_editor_undo.py tests/test_template_catalog.py templates/ostentacao_editor.html
git commit -m "Remove template legado Ostentacao"
```

---

### Task 3: Criar o catálogo oficial de templates

**Files:**
- Create: `scripts/template_catalog.py`
- Modify: `scripts/roteiro_to_instagram.py:639-652, 988-996`
- Modify: `tests/test_template_catalog.py`

**Interfaces:**
- Consumes: `PROJECT_ROOT / templates`.
- Produces: `TemplateDefinition`, `TEMPLATE_CATALOG`, `get_template(template_id)` e `public_template_catalog()`.

- [ ] **Step 1: Escrever os testes do contrato do catálogo**

```python
class TemplateCatalogTest(unittest.TestCase):
    def test_public_catalog_contains_only_official_templates(self) -> None:
        items = public_template_catalog()
        self.assertEqual([item["id"] for item in items], ["tweet", "stories"])
        self.assertEqual([item["initial_slides"] for item in items], [10, 10])

    def test_unknown_template_is_rejected(self) -> None:
        with self.assertRaisesRegex(KeyError, "Template desconhecido"):
            get_template("inexistente")

    def test_template_files_exist(self) -> None:
        for definition in TEMPLATE_CATALOG.values():
            with self.subTest(template=definition.id):
                self.assertTrue(definition.template_path.is_file())
```

- [ ] **Step 2: Rodar os testes e confirmar import failure**

Run: `python3 -m unittest tests.test_template_catalog.TemplateCatalogTest -v`

Expected: ERROR porque `scripts.template_catalog` ainda não existe.

- [ ] **Step 3: Implementar o catálogo mínimo**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

@dataclass(frozen=True)
class TemplateDefinition:
    id: str
    name: str
    description: str
    aspect_ratio: str
    initial_slides: int
    template_path: Path
    preview_kind: str
    active: bool

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "aspect_ratio": self.aspect_ratio,
            "initial_slides": self.initial_slides,
            "preview_kind": self.preview_kind,
        }

TEMPLATE_CATALOG = {
    "tweet": TemplateDefinition("tweet", "Modelo Tweet", "Post em formato de conversa.", "4:5", 10, PROJECT_ROOT / "templates" / "tweet_editor.html", "tweet", True),
    "stories": TemplateDefinition("stories", "Stories", "Narrativa vertical em tela cheia.", "9:16", 10, PROJECT_ROOT / "templates" / "stories_editor.html", "stories", True),
}

def get_template(template_id: str) -> TemplateDefinition:
    try:
        definition = TEMPLATE_CATALOG[template_id]
    except KeyError as exc:
        raise KeyError(f"Template desconhecido: {template_id}") from exc
    if not definition.active:
        raise KeyError(f"Template indisponível: {template_id}")
    return definition

def public_template_catalog() -> list[dict]:
    return [definition.public_dict() for definition in TEMPLATE_CATALOG.values() if definition.active]
```

- [ ] **Step 4: Fazer o gerador consumir o catálogo**

No gerador, importar com fallback compatível com execução direta:

```python
try:
    from scripts.template_catalog import TEMPLATE_CATALOG
except ImportError:
    from template_catalog import TEMPLATE_CATALOG

EDITOR_TEMPLATES = {key: item.template_path for key, item in TEMPLATE_CATALOG.items()}
TEMPLATE_SLIDES_BY_NAME = {key: item.initial_slides for key, item in TEMPLATE_CATALOG.items()}
```

- [ ] **Step 5: Rodar catálogo, parser e geração dos dois modelos**

Run: `python3 -m unittest tests.test_template_catalog tests.test_copy_padrao -v`

Run Tweet: `python3 scripts/roteiro_to_instagram.py content/rascunhos/teste-tweet-10.md --editor --template tweet --no-launch`

Run Stories: `python3 scripts/roteiro_to_instagram.py content/rascunhos/teste-stories-10.md --editor --template stories --no-launch`

Expected: ambos geram HTML com 10 slides.

- [ ] **Step 6: Commit**

```bash
git add scripts/template_catalog.py scripts/roteiro_to_instagram.py tests/test_template_catalog.py
git commit -m "Adiciona catalogo oficial de templates"
```

---

### Task 4: Criar sessões efêmeras sem rascunhos

**Files:**
- Create: `scripts/hub_sessions.py`
- Create: `tests/test_hub_sessions.py`

**Interfaces:**
- Consumes: `get_template(template_id)`, `tweet_placeholder`, `stories_placeholder` e CLI de `roteiro_to_instagram.py`.
- Produces: `HubSession`, `create_hub_session(template_id, editor_dir) -> HubSession` e `cleanup_hub_sessions(editor_dir) -> list[Path]`.

- [ ] **Step 1: Escrever testes de geração, unicidade e limpeza**

```python
class HubSessionsTest(unittest.TestCase):
    def test_creates_unique_html_without_project_draft(self) -> None:
        before = set(CONTENT_DIR.glob("*.md"))
        with tempfile.TemporaryDirectory() as tmp:
            first = create_hub_session("tweet", Path(tmp))
            second = create_hub_session("tweet", Path(tmp))
            self.assertNotEqual(first.id, second.id)
            self.assertTrue(first.path.is_file())
            self.assertEqual(first.url, f"/{first.path.name}")
            self.assertEqual(list(Path(tmp).glob("*.md")), [])
        self.assertEqual(set(CONTENT_DIR.glob("*.md")), before)

    def test_generated_stories_session_has_ten_slides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = create_hub_session("stories", Path(tmp))
            html = session.path.read_text(encoding="utf-8")
            self.assertIn("10 slides", html)

    def test_cleanup_removes_only_hub_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub = root / "hub-tweet-deadbeef.html"
            manual = root / "meu-rascunho.html"
            hub.write_text("hub", encoding="utf-8")
            manual.write_text("manual", encoding="utf-8")
            removed = cleanup_hub_sessions(root)
            self.assertEqual(removed, [hub])
            self.assertTrue(manual.exists())
```

- [ ] **Step 2: Rodar testes e confirmar import failure**

Run: `python3 -m unittest tests.test_hub_sessions -v`

Expected: ERROR porque `scripts.hub_sessions` ainda não existe.

- [ ] **Step 3: Implementar o serviço de sessão**

```python
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import uuid

@dataclass(frozen=True)
class HubSession:
    id: str
    path: Path
    url: str

def cleanup_hub_sessions(editor_dir: Path) -> list[Path]:
    removed = []
    for path in sorted(editor_dir.glob("hub-*.html")):
        path.unlink()
        removed.append(path)
    return removed

def create_hub_session(template_id: str, editor_dir: Path) -> HubSession:
    definition = get_template(template_id)
    session_id = f"hub-{definition.id}-{uuid.uuid4().hex[:12]}"
    placeholder = tweet_placeholder if definition.id == "tweet" else stories_placeholder
    markdown = placeholder(session_id, date.today().isoformat())
    editor_dir.mkdir(parents=True, exist_ok=True)
    path = editor_dir / f"{session_id}.html"
    with tempfile.TemporaryDirectory(prefix="carrossel-hub-") as tmp:
        md_path = Path(tmp) / f"{session_id}.md"
        md_path.write_text(markdown, encoding="utf-8")
        env = os.environ.copy()
        env["CARROSSEL_EDITOR_DIR"] = str(editor_dir)
        try:
            subprocess.run(
                [sys.executable, str(GENERATOR), str(md_path), "--editor", "--template", definition.id, "--no-launch"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
        except Exception:
            path.unlink(missing_ok=True)
            raise
    if not path.is_file():
        raise RuntimeError("O editor temporário não foi gerado.")
    return HubSession(session_id, path, f"/{path.name}")
```

Definir imports com fallback `scripts.*`/execução direta, e `GENERATOR = PROJECT_ROOT / "scripts" / "roteiro_to_instagram.py"`.

- [ ] **Step 4: Rodar testes do serviço e a suíte de geração**

Run: `python3 -m unittest tests.test_hub_sessions tests.test_copy_padrao -v`

Expected: PASS e nenhum novo arquivo em `content/rascunhos/`.

- [ ] **Step 5: Commit**

```bash
git add scripts/hub_sessions.py tests/test_hub_sessions.py
git commit -m "Cria sessoes efemeras do HUB"
```

---

### Task 5: Servir o HUB e criar sessões pela API local

**Files:**
- Create: `templates/hub.html`
- Modify: `scripts/serve_carrossel.py:1-100, 161-260, 370-386`
- Create: `tests/test_hub_server.py`

**Interfaces:**
- Consumes: `public_template_catalog()`, `create_hub_session(template_id, Path(DIR))`, `cleanup_hub_sessions(Path(DIR))`.
- Produces: `GET /` com HUB, `POST /api/sessoes` com `{ok, session_id, url}` e erro 400 para template inválido.

- [ ] **Step 1: Escrever testes do HTML e do contrato HTTP**

```python
class HubServerTest(unittest.TestCase):
    def test_root_renders_only_official_templates(self) -> None:
        html = serve_carrossel._render_hub()
        self.assertIn("Editor de Carrosséis", html)
        self.assertIn('"id": "tweet"', html)
        self.assertIn('"id": "stories"', html)
        self.assertNotIn('"id": "ostentacao"', html)

    def test_create_session_response(self) -> None:
        with running_test_server() as base_url, patch.object(
            serve_carrossel,
            "create_hub_session",
            return_value=HubSession("hub-tweet-abc", Path("/tmp/hub-tweet-abc.html"), "/hub-tweet-abc.html"),
        ):
            req = urllib.request.Request(
                base_url + "/api/sessoes",
                data=json.dumps({"template": "tweet"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            body = json.loads(urllib.request.urlopen(req).read())
            self.assertEqual(body["url"], "/hub-tweet-abc.html")

    def test_invalid_template_returns_400(self) -> None:
        with running_test_server() as base_url:
            req = urllib.request.Request(
                base_url + "/api/sessoes",
                data=b'{"template":"inexistente"}',
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(req)
            self.assertEqual(raised.exception.code, 400)
            body = json.loads(raised.exception.read())
            self.assertEqual(body["error"], "template_invalido")
```

O helper `running_test_server()` deve usar `ReusableThreadingTCPServer(("127.0.0.1", 0), CarrosselHandler)` numa thread daemon e restaurar `serve_carrossel.DIR` ao sair.

- [ ] **Step 2: Rodar testes e confirmar as falhas esperadas**

Run: `python3 -m unittest tests.test_hub_server -v`

Expected: FAIL porque `_render_hub` e `/api/sessoes` ainda não existem.

- [ ] **Step 3: Criar `templates/hub.html`**

O template deve usar a pilha `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif`, fundo `#F2F2F4`, cards brancos e azul `#007AFF`. Incluir:

```html
<main class="hub-shell">
  <header class="hub-header">
    <p class="eyebrow">Editor de Carrosséis</p>
    <h1>O que vamos criar?</h1>
    <p>Escolha um modelo para começar uma criação nova.</p>
  </header>
  <section id="template-grid" class="template-grid" aria-label="Templates disponíveis"></section>
  <p id="hub-status" class="hub-status" role="status" aria-live="polite"></p>
</main>
<script>const TEMPLATES = {{TEMPLATES_JSON}};</script>
```

Renderizar miniaturas CSS representativas: Tweet com avatar/cabeçalho/texto em cartão 4:5; Stories com fundo vertical e blocos tipográficos. Não usar imagens remotas.

A ação usa:

```javascript
async function createCarousel(templateId, button) {
  button.disabled = true;
  setStatus('Preparando seu editor…');
  try {
    const response = await fetch('/api/sessoes', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({template: templateId})
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'Não foi possível criar o carrossel.');
    window.location.assign(payload.url);
  } catch (error) {
    button.disabled = false;
    setStatus(error.message, true);
  }
}
```

- [ ] **Step 4: Integrar catálogo e sessões ao servidor**

```python
HUB_TEMPLATE = PROJECT_ROOT / "templates" / "hub.html"

def _render_hub() -> str:
    catalog_json = json.dumps(public_template_catalog(), ensure_ascii=False).replace("</", "<\\/")
    return HUB_TEMPLATE.read_text(encoding="utf-8").replace("{{TEMPLATES_JSON}}", catalog_json)
```

Alterar `_send_root()` para sempre `self._send_html(200, _render_hub())`. No `do_POST()`:

```python
if self.path == "/api/sessoes":
    return self._handle_create_session()
```

```python
def _handle_create_session(self):
    template_id = str(self._read_json_body().get("template", "")).strip()
    try:
        session = create_hub_session(template_id, Path(DIR))
    except KeyError as exc:
        self._send_json(400, {"error": "template_invalido", "detail": str(exc)})
        return
    self._send_json(201, {"ok": True, "session_id": session.id, "url": session.url})
```

Executar `cleanup_hub_sessions(Path(DIR))` dentro do bloco `if __name__ == '__main__':`, imediatamente antes de abrir o servidor. Não executar a limpeza durante o import do módulo, para que testes e ferramentas de diagnóstico não apaguem sessões ativas.

- [ ] **Step 5: Rodar testes e validar HTTP real**

Run: `python3 -m unittest tests.test_hub_server tests.test_hub_sessions -v`

Run: `./stop.sh && ./start.sh`

Run: `curl -sS -o /tmp/hub-check.html -w '%{http_code} %{content_type}\n' http://localhost:8777/`

Expected: `200 text/html` e `rg 'Modelo Tweet|Stories' /tmp/hub-check.html` encontra os dois templates.

- [ ] **Step 6: Commit**

```bash
git add templates/hub.html scripts/serve_carrossel.py tests/test_hub_server.py
git commit -m "Adiciona HUB local de templates"
```

---

### Task 6: Integrar o modo HUB aos editores sem alterar o modo técnico

**Files:**
- Modify: `scripts/roteiro_to_instagram.py:900-1012`
- Modify: `scripts/hub_sessions.py`
- Modify: `templates/tweet_editor.html:480-495, scripts finais`
- Modify: `templates/stories_editor.html:680-695, scripts finais`
- Modify: `tests/test_editor_shell.py`
- Create: `tests/test_hub_editor_mode.py`

**Interfaces:**
- Consumes: CLI `--hub-session` e token `{{HUB_SESSION}}`.
- Produces: `launch_editor(..., hub_session: bool = False)`, botão `Voltar aos modelos` em sessões HUB e ocultação contextual de `btn-publish-ig`.

- [ ] **Step 1: Escrever testes de modo HUB e modo técnico**

```python
class HubEditorModeTest(unittest.TestCase):
    def test_hub_session_enables_safe_return_and_hides_instagram(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = create_hub_session("tweet", Path(tmp))
            html = session.path.read_text(encoding="utf-8")
            self.assertIn("const HUB_SESSION = true;", html)
            self.assertIn('id="btn-back-hub"', html)
            self.assertIn("publishButton.hidden = true", html)

    def test_direct_generation_keeps_existing_publish_flow(self) -> None:
        html = generate_direct_editor("tweet")
        self.assertIn("const HUB_SESSION = false;", html)
        self.assertIn('id="btn-publish-ig"', html)
```

Adicionar ao contrato de shell dos dois templates os marcadores `{{HUB_SESSION}}`, `btn-back-hub` e `returnToHub`.

- [ ] **Step 2: Rodar testes e confirmar as falhas esperadas**

Run: `python3 -m unittest tests.test_hub_editor_mode tests.test_editor_shell -v`

Expected: FAIL por ausência do token e do controle.

- [ ] **Step 3: Adicionar flag ao gerador e ao serviço de sessão**

```python
def launch_editor(parsed: dict, roteiro_md: Path, no_launch: bool = False, hub_session: bool = False) -> str:
    # geração existente
    out_html = out_html.replace("{{HUB_SESSION}}", "true" if hub_session else "false")
```

```python
parser.add_argument("--hub-session", action="store_true", help=argparse.SUPPRESS)
```

Chamar `launch_editor(..., hub_session=args.hub_session)` e incluir `--hub-session` no subprocesso de `create_hub_session`.

- [ ] **Step 4: Adicionar integração mínima aos dois templates**

No cabeçalho:

```html
<button id="btn-back-hub" class="shell-button quiet" type="button" hidden>Voltar aos modelos</button>
```

No script:

```javascript
const HUB_SESSION = {{HUB_SESSION}};

function configureHubSession() {
  if (!HUB_SESSION) return;
  const backButton = document.getElementById('btn-back-hub');
  const publishButton = document.getElementById('btn-publish-ig');
  backButton.hidden = false;
  publishButton.hidden = true;
  backButton.addEventListener('click', returnToHub);
}

function returnToHub() {
  if (!window.confirm('Descartar esta criação e voltar aos modelos?')) return;
  window.location.assign('/');
}
```

Chamar `configureHubSession()` no bootstrap existente. Não alterar handlers de PNG, Telegram, undo ou publicação direta.

- [ ] **Step 5: Rodar regressão dos editores e gerar os quatro casos**

Run: `python3 -m unittest tests.test_hub_editor_mode tests.test_editor_shell tests.test_editor_undo tests.test_tweet_highlights -v`

Gerar Tweet/Stories em modo técnico e modo HUB. Expected: técnico contém publicação; HUB mostra retorno e oculta publicação; todos contêm PNG e Telegram.

- [ ] **Step 6: Commit**

```bash
git add scripts/roteiro_to_instagram.py scripts/hub_sessions.py templates/tweet_editor.html templates/stories_editor.html tests/test_editor_shell.py tests/test_hub_editor_mode.py
git commit -m "Integra editores ao fluxo do HUB"
```

---

### Task 7: Atualizar documentação e regras operacionais

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: documentação ativa em `docs/superpowers/` que ainda prescreva 17 slides ou o template removido

**Interfaces:**
- Consumes: fluxo final `/`, `POST /api/sessoes`, templates Tweet/Stories e comandos existentes.
- Produces: instrução consistente para Mac, Windows e Codex.

- [ ] **Step 1: Escrever teste de documentação ativa**

Adicionar a `tests/test_packaging.py`:

```python
def test_active_docs_describe_the_hub_and_current_templates(self) -> None:
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    for text in (agents, readme):
        self.assertIn("Tweet", text)
        self.assertIn("Stories", text)
        self.assertIn("10 slides", text)
        self.assertNotIn("ostentacao", text.lower())
        self.assertNotIn("17 slides", text.lower())
    self.assertIn("HUB", readme)
    self.assertIn("http://localhost:8777", readme)
```

- [ ] **Step 2: Rodar o teste e confirmar a falha esperada**

Run: `python3 -m unittest tests.test_packaging.PackagingTest.test_active_docs_describe_the_hub_and_current_templates -v`

Expected: FAIL pelas referências atuais.

- [ ] **Step 3: Atualizar documentação**

README deve descrever:

```text
./start.sh
abrir http://localhost:8777
escolher Tweet ou Stories
editar
exportar PNGs ou enviar ao Telegram
```

Documentar que o HUB não mantém histórico; `./novo.sh tweet|stories` continua sendo o fluxo técnico com rascunho Markdown; ambos começam com 10 slides; `git pull --ff-only` atualiza o produto sem substituir credenciais locais.

Atualizar `AGENTS.md` para listar apenas Tweet e Stories, ambos com 10 slides, e registrar `templates/hub.html`, `scripts/template_catalog.py` e `scripts/hub_sessions.py` como arquivos importantes.

Nos documentos históricos ainda úteis, trocar nomes de fixture `teste-stories-17` por `teste-stories-10` e expectativas 17 por 10. Não reescrever decisões sem relação com o HUB.

- [ ] **Step 4: Rodar teste e auditoria textual**

Run: `python3 -m unittest tests.test_packaging -v`

Run: `rg -n -i '17 slides|teste-stories-17' AGENTS.md README.md scripts templates tests content`

Expected: nenhuma ocorrência.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md README.md docs/superpowers tests/test_packaging.py
git commit -m "Documenta operacao do HUB local"
```

---

### Task 8: Verificação ponta a ponta e entrega segura

**Files:**
- Modify only if verification finds a defect in files owned by Tasks 1–7.

**Interfaces:**
- Consumes: produto completo.
- Produces: evidência de que HUB, Tweet, Stories, PNG, Telegram e fluxos técnicos continuam operantes.

- [ ] **Step 1: Rodar toda a suíte e verificações estáticas**

Run: `python3 -m unittest discover -s tests -v`

Run: `python3 -m py_compile scripts/*.py`

Run: `bash -n start.sh stop.sh novo.sh configurar-credenciais.sh`

Run: `git diff --check`

Expected: zero falhas e zero erros.

- [ ] **Step 2: Reiniciar o servidor e validar rotas**

Run: `./stop.sh && ./start.sh`

Run: `curl -sS -o /tmp/hub-final.html -w '%{http_code} %{content_type}\n' http://localhost:8777/`

Run invalid template:

```bash
curl -sS -X POST http://localhost:8777/api/sessoes \
  -H 'Content-Type: application/json' \
  -d '{"template":"inexistente"}'
```

Expected: HUB `200 text/html`; template inválido `400` com `template_invalido`.

- [ ] **Step 3: Validar criação real dos dois templates**

Criar Tweet e Stories pelo `POST /api/sessoes`, abrir as URLs retornadas e confirmar exatamente 10 itens em `#slide-rail-list`, copy padrão, botão de retorno, PNG e Telegram. Confirmar que `btn-publish-ig` está oculto no modo HUB.

- [ ] **Step 4: Fazer auditoria visual no navegador**

Em viewport desktop e mobile:

- HUB sem overflow e com dois cards claramente distintos;
- Tweet e Stories abrem sem console errors;
- adicionar e remover slide preserva texto existente;
- `Ctrl+Z`/`Cmd+Z` desfaz alteração;
- recarregar preserva somente a sessão atual;
- iniciar outra criação abre conteúdo limpo;
- retorno ao HUB pede confirmação.

- [ ] **Step 5: Validar PNG e Telegram sem expor segredos**

Baixar um PNG de Tweet e um de Stories e verificar dimensões e conteúdo. Para Telegram, usar a configuração local já existente, enviar um carrossel de teste e conferir o estado de sucesso na interface; não imprimir token ou Chat ID em logs, testes ou resposta final.

- [ ] **Step 6: Validar limpeza de sessões e fluxo técnico**

Reiniciar o servidor e confirmar que `hub-*.html` antigos foram removidos, enquanto HTMLs gerados por `./novo.sh` permanecem. Rodar `./novo.sh tweet --no-launch` e `./novo.sh stories --no-launch` via script Python equivalente se o wrapper não aceitar flags, confirmando criação do Markdown técnico e 10 slides.

- [ ] **Step 7: Corrigir somente defeitos encontrados e repetir a verificação completa**

Qualquer correção deve ganhar teste de regressão no arquivo de teste responsável. Repetir Steps 1–6 após a última mudança.

- [ ] **Step 8: Commit final de hardening, somente se necessário**

```bash
git add -A
git commit -m "Valida fluxo completo do HUB local"
```

Se nenhuma correção for necessária, não criar commit vazio.

---

## Definition of Done

- `localhost:8777` abre o HUB, não um editor anterior.
- O catálogo contém apenas Tweet e Stories.
- Ambos começam com 10 slides.
- Cada clique cria uma sessão limpa e única.
- Não existe histórico visível nem rascunho Markdown criado pelo HUB.
- PNG e Telegram funcionam nos dois modelos.
- Publicação no Instagram não aparece em sessões de cliente.
- Fluxos técnicos diretos continuam disponíveis.
- O template Ostentação não existe nem é executável.
- Suíte completa, compilação Python, scripts shell, HTTP e auditoria visual passam.
- Commits são pequenos, reversíveis e enviados ao repositório privado somente após verificação final.
