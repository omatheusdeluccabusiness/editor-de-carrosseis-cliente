#!/usr/bin/env python3
"""
Servidor local do editor de carrosséis.

Funções:
1. Serve estáticos do diretório temporário do editor (HTMLs, fonts, telegram-config).
2. Copia ~/.matheusao-telegram.json -> telegram-config.json no boot.
3. POST /api/gerar-imagem  -> chama OpenAI Images API server-side, key isolada.
4. POST /api/salvar-imagem -> grava PNG dentro da pasta da peça no vault.

A key da OpenAI fica em ~/.matheusao-openai.json (perm 600), nunca no browser.
"""

from __future__ import annotations

import os
import sys
import json
import shutil
import base64
import subprocess
import tempfile
import urllib.request
import urllib.error
import http.server
import socketserver
import functools
import re
import html
import urllib.parse
from pathlib import Path

try:
    from scripts.hub_sessions import cleanup_hub_sessions, create_hub_session
    from scripts.template_catalog import public_template_catalog
except ImportError:
    from hub_sessions import cleanup_hub_sessions, create_hub_session
    from template_catalog import public_template_catalog

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT     = Path(__file__).resolve().parent.parent
HUB_TEMPLATE     = PROJECT_ROOT / 'templates' / 'hub.html'
DIR              = os.environ.get('CARROSSEL_EDITOR_DIR', '/tmp/carrossel-editor')
PORT             = int(os.environ.get('CARROSSEL_EDITOR_PORT', '8777'))
HOME_TG          = os.path.expanduser('~/.matheusao-telegram.json')
DEST_TG          = os.path.join(DIR, 'telegram-config.json')
HOME_OPENAI      = os.path.expanduser('~/.matheusao-openai.json')
VAULT_ROOT       = os.environ.get('CARROSSEL_CONTENT_ROOT', str(PROJECT_ROOT / 'content'))
DEFAULT_MODEL    = 'gpt-image-2'
ALLOWED_SIZES    = {'1024x1024', '1024x1536', '1536x1024', '1024x1792', '1792x1024'}
DEFAULT_SIZE     = '1024x1536'  # portrait 2:3, frontend faz crop pra 1080x1350

# Caminho do publisher Instagram (script que chama a Meta API)
INSTAGRAM_PUBLISHER = os.environ.get('CARROSSEL_INSTAGRAM_PUBLISHER', str(Path(__file__).with_name('publish_instagram.py')))

os.makedirs(DIR, exist_ok=True)

# Bootstrap Telegram config
if os.path.exists(HOME_TG):
    shutil.copyfile(HOME_TG, DEST_TG)
    os.chmod(DEST_TG, 0o600)
    print(f"[telegram] config copiada {HOME_TG} -> {DEST_TG}")
else:
    print(f"[telegram] {HOME_TG} não encontrado, config não pré-populada.")

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


def _render_hub() -> str:
    catalog_json = json.dumps(public_template_catalog(), ensure_ascii=False).replace("</", "<\\/")
    return HUB_TEMPLATE.read_text(encoding='utf-8').replace("{{TEMPLATES_JSON}}", catalog_json)

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

    # CORS / pre-flight (mesma origem na maior parte dos casos, mas garantido)
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # No-cache absoluto: editor é dev-time, browser sempre busca versão fresh
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def _send_html(self, status: int, body: str):
        payload = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_root(self):
        self._send_html(200, _render_hub())

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("", "/", "/index.html"):
            return self._send_root()

        name = Path(urllib.parse.unquote(path)).name
        if name.endswith(".pid") or name == "server.log":
            self.send_error(404, "arquivo interno")
            return

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
        try:
            if self.path == '/api/sessoes':
                return self._handle_create_session()
            if self.path == '/api/gerar-imagem':
                return self._handle_gerar()
            if self.path == '/api/salvar-imagem':
                return self._handle_salvar()
            if self.path == '/api/publicar-instagram':
                return self._handle_publicar_instagram()
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

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
    cleanup_hub_sessions(Path(DIR))
    with ReusableThreadingTCPServer(("", PORT), CarrosselHandler) as httpd:
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
