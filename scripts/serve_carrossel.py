#!/usr/bin/env python3
"""
Servidor local do editor de carrosséis.

O processo aceita somente conexões loopback. Credenciais permanecem no servidor;
o browser recebe apenas estado redigido e usa endpoints locais protegidos.

A key da OpenAI fica em ~/.matheusao-openai.json (perm 600), nunca no browser.
"""

from __future__ import annotations

import os
import sys
import json
import io
import shutil
import base64
import subprocess
import tempfile
import urllib.request
import urllib.error
import http.server
import socketserver
import functools
import ipaddress
import re
import secrets
import html
import urllib.parse
import zipfile
from pathlib import Path

try:
    from scripts.credenciais import (
        CredentialsError,
        credentials_ready,
        import_credentials_to_directory,
    )
    from scripts.desktop_paths import desktop_runtime_paths
    from scripts.hub_sessions import (
        create_hub_session,
        hub_session_needs_refresh,
        refresh_hub_session,
    )
    from scripts.template_catalog import public_template_catalog
except ImportError:
    from credenciais import (
        CredentialsError,
        credentials_ready,
        import_credentials_to_directory,
    )
    from desktop_paths import desktop_runtime_paths
    from hub_sessions import (
        create_hub_session,
        hub_session_needs_refresh,
        refresh_hub_session,
    )
    from template_catalog import public_template_catalog

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# PyInstaller extracts bundled data folders into ``_MEIPASS``.  In source
# mode, preserve the repository-root calculation used by the local editor.
PROJECT_ROOT     = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
HUB_TEMPLATE     = PROJECT_ROOT / 'templates' / 'hub.html'
HORSHAM_FONT     = PROJECT_ROOT / 'HorshamSerial.otf'
GARAMOND_MODERN_FONT = PROJECT_ROOT / 'assets' / 'fonts' / 'GaramondModern-Regular.otf'
ADVERCASE_REGULAR_FONT = PROJECT_ROOT / 'assets' / 'fonts' / 'Advercase-Regular.otf'
ADVERCASE_BOLD_FONT = PROJECT_ROOT / 'assets' / 'fonts' / 'Advercase-Bold.otf'
APP_DATA_DIR     = os.environ.get('CARROSSEL_APP_DATA_DIR')
RUNTIME_PATHS    = desktop_runtime_paths(APP_DATA_DIR) if APP_DATA_DIR else None
DIR              = str(RUNTIME_PATHS.editor_dir) if RUNTIME_PATHS else os.environ.get('CARROSSEL_EDITOR_DIR', '/tmp/carrossel-editor')
PORT             = int(os.environ.get('CARROSSEL_EDITOR_PORT', '8777'))
HOME_TG          = str(RUNTIME_PATHS.credentials_dir / '.matheusao-telegram.json') if RUNTIME_PATHS else os.path.expanduser('~/.matheusao-telegram.json')
HOME_OPENAI      = str(RUNTIME_PATHS.credentials_dir / '.matheusao-openai.json') if RUNTIME_PATHS else os.path.expanduser('~/.matheusao-openai.json')
VAULT_ROOT       = os.environ.get('CARROSSEL_CONTENT_ROOT', str(PROJECT_ROOT / 'content'))
DEFAULT_MODEL    = 'gpt-image-2'
ALLOWED_SIZES    = {'1024x1024', '1024x1536', '1536x1024', '1024x1792', '1792x1024'}
DEFAULT_SIZE     = '1024x1536'  # portrait 2:3, frontend faz crop pra 1080x1350

# Caminho do publisher Instagram (script que chama a Meta API)
INSTAGRAM_PUBLISHER = os.environ.get('CARROSSEL_INSTAGRAM_PUBLISHER', str(Path(__file__).with_name('publish_instagram.py')))
CSRF_TOKEN = secrets.token_urlsafe(32)
LOOPBACK_NAMES = {'localhost', '127.0.0.1'}
HTML_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; base-uri 'none'; form-action 'self'; object-src 'none'; "
    "img-src 'self' data: blob:; font-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
    "connect-src 'self'"
)

os.makedirs(DIR, exist_ok=True)

# Remove bootstrap legado que poderia expor credenciais como arquivo estático.
legacy_telegram_config = Path(DIR) / 'telegram-config.json'
legacy_telegram_config.unlink(missing_ok=True)
print(f"[telegram] configuração server-side: {'disponível' if os.path.exists(HOME_TG) else 'ausente'}")

# Verifica OpenAI config
if os.path.exists(HOME_OPENAI):
    print(f"[openai] config encontrada em {HOME_OPENAI}")
else:
    print(f"[openai] {HOME_OPENAI} NÃO encontrado. Endpoint /api/gerar-imagem retornará 500 até key ser configurada.")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_openai_key():
    with open(HOME_OPENAI) as f:
        cfg = json.load(f)
    key = cfg.get('openai_api_key')
    if not key or not key.startswith('sk-'):
        raise RuntimeError(f"key inválida em {HOME_OPENAI}")
    return key

def _vault_path_safe(peca_path: str) -> Path:
    """Aceita só caminhos dentro do vault. Bloqueia path traversal."""
    p = Path(peca_path).expanduser().resolve()
    root = Path(VAULT_ROOT).resolve()
    if root not in p.parents and p != root:
        raise PermissionError(f"path fora do vault: {p}")
    return p

def _slug_id(slide_id: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '', slide_id)[:32] or 'slide'

def _latest_editor_html() -> Path | None:
    html_files = [
        p for p in Path(DIR).glob("*.html")
        if p.is_file() and not p.name.startswith(".")
    ]
    if not html_files:
        return None
    return max(html_files, key=lambda p: p.stat().st_mtime)


def _inject_local_runtime(html_text: str) -> str:
    runtime = (
        '<script>window.CARROSSEL_CSRF='
        + json.dumps(CSRF_TOKEN)
        + ';</script>'
    )
    marker = '</head>' if '</head>' in html_text else '</body>'
    return html_text.replace(marker, runtime + marker, 1)


def _render_hub() -> str:
    catalog_json = json.dumps(public_template_catalog(), ensure_ascii=False).replace("</", "<\\/")
    rendered = HUB_TEMPLATE.read_text(encoding='utf-8').replace("{{TEMPLATES_JSON}}", catalog_json)
    return _inject_local_runtime(rendered)


def _read_telegram_config() -> tuple[str, str]:
    with open(HOME_TG, encoding='utf-8') as config_file:
        config = json.load(config_file)
    token = str(config.get('botToken') or config.get('bot_token') or '').strip()
    chat_id = str(config.get('chatId') or config.get('chat_id') or '').strip()
    if not token or not chat_id:
        raise RuntimeError('Configuração do Telegram incompleta.')
    return token, chat_id


def _desktop_credentials_configured() -> bool:
    """Return only a redacted readiness signal for the installed app."""

    if not RUNTIME_PATHS:
        return False
    return credentials_ready(
        RUNTIME_PATHS.credentials_dir / ".env",
        RUNTIME_PATHS.credentials_dir / ".matheusao-telegram.json",
    )


def _telegram_api_request(method: str, fields: dict[str, str], images: list[bytes] | None = None) -> dict:
    token, _ = _read_telegram_config()
    endpoint = f'https://api.telegram.org/bot{token}/{method}'
    # getMe não recebe campos nem arquivos. Usar GET evita uma requisição
    # multipart vazia, que o Telegram rejeita com HTTP 400.
    if not fields and not images:
        request = urllib.request.Request(endpoint, method='GET')
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())

    boundary = '----carrossel-' + secrets.token_hex(12)
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            str(value).encode('utf-8'), b'\r\n',
        ])
    for index, image_bytes in enumerate(images or []):
        chunks.extend([
            f'--{boundary}\r\nContent-Disposition: form-data; name="file{index}"; filename="slide-{index + 1:02d}.png"\r\nContent-Type: image/png\r\n\r\n'.encode(),
            image_bytes, b'\r\n',
        ])
    chunks.append(f'--{boundary}--\r\n'.encode())
    request = urllib.request.Request(
        endpoint,
        data=b''.join(chunks),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())

# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------

def _call_openai_images(prompt: str, size: str, model: str):
    """
    Chama POST https://api.openai.com/v1/images/generations.
    Retorna dict {model_used, b64, raw_keys}.
    Levanta urllib.error.HTTPError com body legível em caso de erro.
    """
    if size not in ALLOWED_SIZES:
        raise ValueError(f"size '{size}' fora de {sorted(ALLOWED_SIZES)}")

    key = _read_openai_key()
    payload = {'model': model, 'prompt': prompt, 'size': size, 'n': 1}

    req = urllib.request.Request(
        'https://api.openai.com/v1/images/generations',
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        data=json.dumps(payload).encode('utf-8'),
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        result = json.loads(resp.read())

    data = result.get('data', [])
    if not data or 'b64_json' not in data[0]:
        raise RuntimeError(f"resposta inesperada da OpenAI: {list(result.keys())}")

    return {
        'model_used': result.get('model') or model,  # API atual nem sempre echoa o model
        'created':    result.get('created'),
        'usage':      result.get('usage'),
        'b64':        data[0]['b64_json'],
    }

# ---------------------------------------------------------------------------
# Save image to vault
# ---------------------------------------------------------------------------

def _save_image_to_vault(peca_path: str, slide_id: str, version: int, b64: str):
    folder = _vault_path_safe(peca_path) / 'imagens-geradas'
    folder.mkdir(parents=True, exist_ok=True)
    fname = f"slide-{_slug_id(slide_id)}-v{int(version):02d}.png"
    target = folder / fname
    target.write_bytes(base64.b64decode(b64))
    return str(target)

# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class CarrosselHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def end_headers(self):
        # No-cache absoluto: editor é dev-time, browser sempre busca versão fresh
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def _request_is_loopback(self) -> bool:
        try:
            peer = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        host = urllib.parse.urlsplit('//' + self.headers.get('Host', '')).hostname
        return peer.is_loopback and host in LOOPBACK_NAMES

    def _mutation_is_authorized(self) -> bool:
        if not self._request_is_loopback():
            return False
        host = self.headers.get('Host', '').lower()
        origin = self.headers.get('Origin', '').lower()
        if not origin or urllib.parse.urlsplit(origin).scheme != 'http':
            return False
        if urllib.parse.urlsplit(origin).netloc != host:
            return False
        return secrets.compare_digest(self.headers.get('X-Carrossel-CSRF', ''), CSRF_TOKEN)

    def _reject_nonlocal(self) -> bool:
        if self._request_is_loopback():
            return False
        self._send_json(403, {'error': 'acesso_local_obrigatorio'})
        return True

    def _reject_unauthorized_mutation(self) -> bool:
        if self._mutation_is_authorized():
            return False
        self._send_json(403, {'error': 'origem_ou_token_invalido'})
        return True

    def _send_html(self, status: int, body: str):
        payload = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Security-Policy', HTML_CONTENT_SECURITY_POLICY)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_root(self):
        self._send_html(200, _render_hub())

    def _send_local_font(self, font_path: Path):
        """Serve a bundled local font to generated editor HTML files."""
        if not font_path.is_file():
            self.send_error(404, "fonte não encontrada")
            return
        payload = font_path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'font/otf')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self._reject_nonlocal():
            return
        path = urllib.parse.urlparse(self.path).path
        if path == '/api/health':
            return self._send_json(200, {'ok': True, 'service': 'editor-carrosseis'})
        if path in ("", "/", "/index.html"):
            return self._send_root()
        if path == '/HorshamSerial.otf':
            return self._send_local_font(HORSHAM_FONT)
        if path == '/assets/fonts/GaramondModern-Regular.otf':
            return self._send_local_font(GARAMOND_MODERN_FONT)
        if path == '/assets/fonts/Advercase-Regular.otf':
            return self._send_local_font(ADVERCASE_REGULAR_FONT)
        if path == '/assets/fonts/Advercase-Bold.otf':
            return self._send_local_font(ADVERCASE_BOLD_FONT)
        if path == '/api/telegram/status':
            try:
                _read_telegram_config()
                configured = True
            except Exception:
                configured = False
            return self._send_json(200, {'configured': configured})
        if path == '/api/desktop-credentials/status':
            if not RUNTIME_PATHS:
                return self._send_json(404, {'error': 'recurso_disponivel_apenas_no_app_desktop'})
            return self._send_json(200, {'configured': _desktop_credentials_configured()})

        name = Path(urllib.parse.unquote(path)).name
        if name.endswith(".pid") or name in {"server.log", "telegram-config.json"}:
            self.send_error(404, "arquivo interno")
            return

        if name.endswith('.html'):
            target = (Path(DIR) / name).resolve()
            if target.parent == Path(DIR).resolve() and target.is_file():
                session_match = re.fullmatch(r'hub-(tweet|stories)-[0-9a-f]{12}\.html', name)
                if session_match and hub_session_needs_refresh(target, session_match.group(1)):
                    # Sessões do Hub preservam estado no DOC_KEY. Regenerar o
                    # HTML com o mesmo id atualiza a interface ao recarregar
                    # sem apagar a copy/imagens já salvas no browser.
                    refresh_hub_session(target.stem, Path(DIR))
                return self._send_html(200, _inject_local_runtime(target.read_text(encoding='utf-8')))

        return super().do_GET()

    def list_directory(self, path):
        self._send_root()
        return None

    def _read_json_body(self):
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length) if length > 0 else b'{}'
        return json.loads(raw or b'{}')

    def _send_json(self, status: int, body: dict):
        payload = json.dumps(body).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self._reject_unauthorized_mutation():
            return
        try:
            if self.path == '/api/sessoes':
                return self._handle_create_session()
            if self.path == '/api/gerar-imagem':
                return self._handle_gerar()
            if self.path == '/api/salvar-imagem':
                return self._handle_salvar()
            if self.path == '/api/publicar-instagram':
                return self._handle_publicar_instagram()
            if self.path == '/api/telegram/test':
                return self._handle_telegram_test()
            if self.path == '/api/telegram/send':
                return self._handle_telegram_send()
            if self.path == '/api/export/pngs':
                return self._handle_export_pngs()
            if self.path == '/api/desktop-credentials/import':
                return self._handle_desktop_credentials_import()
            self._send_json(404, {'error': f'rota POST {self.path} não existe'})
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            try:
                err = json.loads(body)
            except Exception:
                err = {'raw': body[:1500]}
            self._send_json(e.code, {
                'error': 'openai_http_error',
                'http_status': e.code,
                'detail': err,
            })
        except Exception as e:
            self._send_json(500, {'error': type(e).__name__, 'detail': str(e)})

    def _handle_create_session(self):
        try:
            body = self._read_json_body()
        except json.JSONDecodeError as exc:
            self._send_json(400, {'error': 'json_invalido', 'detail': str(exc)})
            return
        if not isinstance(body, dict):
            self._send_json(400, {
                'error': 'payload_invalido',
                'detail': 'O corpo da requisição deve ser um objeto JSON.',
            })
            return

        template_id = str(body.get('template', '')).strip()
        try:
            session = create_hub_session(template_id, Path(DIR))
        except KeyError as exc:
            self._send_json(400, {'error': 'template_invalido', 'detail': str(exc)})
            return
        self._send_json(201, {'ok': True, 'session_id': session.id, 'url': session.url})

    def do_DELETE(self):
        if self._reject_unauthorized_mutation():
            return
        path = urllib.parse.urlparse(self.path).path
        match = re.fullmatch(r'/api/sessoes/(hub-(?:tweet|stories)-[0-9a-f]{12})', path)
        if not match:
            self._send_json(404, {'error': 'sessao_invalida'})
            return
        session_id = match.group(1)
        target = Path(DIR) / f'{session_id}.html'
        existed = target.is_file()
        target.unlink(missing_ok=True)
        self._send_json(200, {'ok': True, 'deleted': existed})

    def _handle_telegram_test(self):
        result = _telegram_api_request('getMe', {})
        self._send_json(200, {'ok': bool(result.get('ok')), 'configured': True})

    def _handle_desktop_credentials_import(self):
        if not RUNTIME_PATHS:
            self._send_json(404, {'error': 'recurso_disponivel_apenas_no_app_desktop'})
            return
        try:
            body = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {'error': 'payload_invalido'})
            return
        if not isinstance(body, dict):
            self._send_json(400, {'error': 'payload_invalido'})
            return

        vault_json = body.get('vault_json')
        recovery_key = body.get('recovery_key')
        if not isinstance(vault_json, str) or not isinstance(recovery_key, str):
            self._send_json(400, {'error': 'payload_invalido'})
            return
        try:
            import_credentials_to_directory(
                vault_json, recovery_key, RUNTIME_PATHS.credentials_dir
            )
        except CredentialsError:
            # Do not expose parsing, cryptographic or credential details.
            self._send_json(400, {'error': 'cofre_ou_chave_invalidos'})
            return
        self._send_json(200, {'ok': True, 'configured': _desktop_credentials_configured()})

    def _handle_telegram_send(self):
        body = self._read_json_body()
        images_b64 = body.get('images_b64') or []
        caption = str(body.get('caption') or '')
        if not isinstance(images_b64, list) or not images_b64:
            self._send_json(400, {'error': 'images_b64 deve conter ao menos um PNG'})
            return
        _, chat_id = _read_telegram_config()
        images = [base64.b64decode(str(item).split(',')[-1], validate=True) for item in images_b64]
        results = []
        for offset in range(0, len(images), 10):
            chunk = images[offset:offset + 10]
            chunk_caption = caption[:1024] if offset == 0 and caption else ''
            if len(chunk) == 1:
                # Documento preserva o PNG original; enviar como foto faz o
                # Telegram recomprimir a arte e suavizar textos pequenos.
                fields = {'chat_id': chat_id, 'document': 'attach://file0'}
                if chunk_caption:
                    fields['caption'] = chunk_caption
                results.append(_telegram_api_request('sendDocument', fields, chunk))
                continue

            media = []
            for index in range(len(chunk)):
                item = {'type': 'document', 'media': f'attach://file{index}'}
                if index == 0 and chunk_caption:
                    item['caption'] = chunk_caption
                media.append(item)
            results.append(_telegram_api_request(
                'sendMediaGroup',
                {'chat_id': chat_id, 'media': json.dumps(media, ensure_ascii=False)},
                chunk,
            ))
        self._send_json(200, {
            'ok': all(bool(result.get('ok')) for result in results),
            'sent': len(images),
        })

    def _handle_export_pngs(self):
        """Empacota todos os PNGs em um ZIP, sem limite de downloads do browser."""
        body = self._read_json_body()
        images_b64 = body.get('images_b64') or []
        if not isinstance(images_b64, list) or not images_b64:
            self._send_json(400, {'error': 'images_b64 deve conter ao menos um PNG'})
            return

        try:
            images = [
                base64.b64decode(str(item).split(',')[-1], validate=True)
                for item in images_b64
            ]
        except (ValueError, TypeError) as exc:
            self._send_json(400, {'error': 'png_invalido'})
            return

        output = io.BytesIO()
        with zipfile.ZipFile(output, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
            for index, image in enumerate(images, start=1):
                archive.writestr(f'slide-{index:02d}.png', image)
        payload = output.getvalue()
        self.send_response(200)
        self.send_header('Content-Type', 'application/zip')
        self.send_header('Content-Disposition', 'attachment; filename="carrossel-pngs.zip"')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('X-Carrossel-Slides', str(len(images)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_gerar(self):
        body = self._read_json_body()
        prompt   = (body.get('prompt') or '').strip()
        size     = body.get('size', DEFAULT_SIZE)
        model    = body.get('model', DEFAULT_MODEL)
        slide_id = body.get('slide_id', 'unknown')

        if len(prompt) < 8:
            self._send_json(400, {'error': 'prompt vazio ou muito curto'})
            return

        result = _call_openai_images(prompt, size, model)
        self._send_json(200, {
            'ok':         True,
            'slide_id':   slide_id,
            'model_used': result['model_used'],
            'created':    result['created'],
            'usage':      result['usage'],
            'size':       size,
            'b64':        result['b64'],
        })

    def _handle_salvar(self):
        body = self._read_json_body()
        peca_path = body.get('peca_path', '').strip()
        slide_id  = body.get('slide_id', 'unknown')
        version   = body.get('version', 1)
        b64       = body.get('b64', '')
        if not peca_path or not b64:
            self._send_json(400, {'error': 'peca_path e b64 obrigatórios'})
            return
        target = _save_image_to_vault(peca_path, slide_id, version, b64)
        self._send_json(200, {'ok': True, 'saved_to': target})

    def _handle_publicar_instagram(self):
        """
        Recebe N slides em base64 + caption, salva em tempdir e chama
        publish_instagram.py pra publicar via Meta API.
        """
        body = self._read_json_body()
        slides_b64 = body.get('slides_b64', [])
        caption    = body.get('caption', '')
        title      = body.get('title', 'post')

        if not slides_b64:
            self._send_json(400, {'error': 'slides_b64 vazio'})
            return
        if len(slides_b64) < 2:
            self._send_json(400, {'error': 'mínimo 2 slides pra carrossel'})
            return
        if len(slides_b64) > 10:
            self._send_json(400, {'error': 'máximo 10 slides'})
            return
        if not caption.strip():
            self._send_json(400, {'error': 'caption vazia'})
            return
        if not os.path.exists(INSTAGRAM_PUBLISHER):
            self._send_json(500, {'error': f'publisher não encontrado em {INSTAGRAM_PUBLISHER}'})
            return

        tmp_dir = Path(tempfile.mkdtemp(prefix='ig_publish_'))
        try:
            print(f"\n[ig-publish] salvando {len(slides_b64)} slides em {tmp_dir}")
            image_paths = []
            for i, b64_str in enumerate(slides_b64):
                img_path = tmp_dir / f"slide_{i+1:02d}.png"
                img_path.write_bytes(base64.b64decode(b64_str))
                image_paths.append(str(img_path))

            print(f"[ig-publish] chamando publisher ({title[:60]})...")
            cmd = [sys.executable, INSTAGRAM_PUBLISHER, '--images'] + image_paths + ['--caption', caption]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                env=os.environ.copy(),
            )

            if result.returncode == 0:
                post_id = None
                for line in result.stdout.split('\n'):
                    if 'Post ID:' in line:
                        post_id = line.split('Post ID:')[-1].strip()
                        break
                self._send_json(200, {
                    'ok': True,
                    'post_id': post_id or 'ok',
                    'stdout': result.stdout[-2000:],
                })
            else:
                self._send_json(500, {
                    'ok': False,
                    'error': 'publisher_failed',
                    'stdout': result.stdout[-2000:],
                    'stderr': result.stderr[-2000:],
                })
        finally:
            try:
                shutil.rmtree(tmp_dir)
            except Exception:
                pass


class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    os.chdir(DIR)
    # Sessões do Hub não são descartáveis: o estado da criação fica ligado ao
    # id delas no navegador. Mantê-las permite reiniciar o servidor e continuar
    # exatamente de onde a pessoa parou.
    with ReusableThreadingTCPServer(("127.0.0.1", PORT), CarrosselHandler) as httpd:
        print(f"servindo {DIR} em http://localhost:{PORT}")
        print(f"endpoints API:")
        print(f"  POST http://localhost:{PORT}/api/sessoes")
        print(f"  POST http://localhost:{PORT}/api/gerar-imagem")
        print(f"  POST http://localhost:{PORT}/api/salvar-imagem")
        print(f"  POST http://localhost:{PORT}/api/publicar-instagram")
        print(f"modelo padrão: {DEFAULT_MODEL}  size padrão: {DEFAULT_SIZE}")
        if os.path.exists(INSTAGRAM_PUBLISHER):
            print(f"[instagram] publisher disponível em {INSTAGRAM_PUBLISHER}")
        else:
            print(f"[instagram] publisher NÃO encontrado em {INSTAGRAM_PUBLISHER}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nencerrando.")
