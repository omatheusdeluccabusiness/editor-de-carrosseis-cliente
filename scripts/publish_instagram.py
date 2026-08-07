#!/usr/bin/env python3
"""
publish_instagram.py — Publicação automática no Instagram via Meta Graph API
Conta conectada: @omatheusdelucca (Matheusão | OSNL)
"""
import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Carrega o .env do runtime desktop, quando o app o fornece. O fluxo CLI
# continua usando o .env do projeto.
SCRIPT_DIR = Path(__file__).parent
APP_DATA_DIR = os.environ.get("CARROSSEL_APP_DATA_DIR")
ENV_FILE = (
    Path(APP_DATA_DIR).expanduser().resolve() / "credentials" / ".env"
    if APP_DATA_DIR
    else SCRIPT_DIR.parent / ".env"
)
load_dotenv(ENV_FILE)

IG_ID = os.getenv("INSTAGRAM_BUSINESS_ID")
PAGE_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
API_VERSION = os.getenv("META_API_VERSION", "v22.0")
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


def host_image(image_path: str) -> str:
    """Hospeda imagem em URL pública via catbox.moe (free)"""
    print(f"  Subindo {Path(image_path).name}...", end=" ", flush=True)
    with open(image_path, "rb") as f:
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (Path(image_path).name, f, "image/png")},
            timeout=60,
        )
    url = resp.text.strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"Falha no upload: {url}")
    print(f"OK")
    return url


def create_media_container(image_path: str, is_carousel: bool = True) -> str:
    """Cria container de mídia no Instagram"""
    image_url = host_image(image_path)
    data = {
        "access_token": PAGE_TOKEN,
        "image_url": image_url,
    }
    if is_carousel:
        data["is_carousel_item"] = "true"
    resp = requests.post(f"{BASE_URL}/{IG_ID}/media", data=data, timeout=60)
    result = resp.json()
    if "id" not in result:
        raise RuntimeError(f"Erro container: {result}")
    return result["id"]


def create_carousel(media_ids: list, caption: str) -> str:
    """Monta carrossel com os containers criados"""
    resp = requests.post(
        f"{BASE_URL}/{IG_ID}/media",
        data={
            "access_token": PAGE_TOKEN,
            "media_type": "CAROUSEL",
            "children": ",".join(media_ids),
            "caption": caption,
        },
        timeout=30,
    )
    result = resp.json()
    if "id" not in result:
        raise RuntimeError(f"Erro carrossel: {result}")
    return result["id"]


def wait_ready(container_id: str, max_wait: int = 60) -> bool:
    """Aguarda container processar"""
    for i in range(max_wait // 5):
        resp = requests.get(
            f"{BASE_URL}/{container_id}",
            params={"fields": "status_code", "access_token": PAGE_TOKEN},
            timeout=15,
        )
        status = resp.json().get("status_code", "")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError(f"Container com erro: {resp.json()}")
        print(f"  Processando... {i*5}s", flush=True)
        time.sleep(5)
    return False


def publish(container_id: str) -> str:
    """Publica de fato no feed"""
    resp = requests.post(
        f"{BASE_URL}/{IG_ID}/media_publish",
        data={"access_token": PAGE_TOKEN, "creation_id": container_id},
        timeout=30,
    )
    result = resp.json()
    if "id" not in result:
        raise RuntimeError(f"Erro publicar: {result}")
    return result["id"]


def publish_single(image_path: str, caption: str, dry_run: bool = False) -> str:
    """Publica imagem única (não carrossel)"""
    print(f"\nPublicando 1 imagem no Instagram...")
    if dry_run:
        print("[DRY RUN] Tudo OK, parando antes da publicação.")
        return ""
    container_id = create_media_container(image_path, is_carousel=False)
    print(f"  Container criado: {container_id}")
    if not wait_ready(container_id):
        raise RuntimeError("Timeout no processamento.")
    post_id = publish(container_id)
    print(f"\nPublicado! Post ID: {post_id}")
    return post_id


def publish_carousel(images: list, caption: str, dry_run: bool = False) -> str:
    """Publica carrossel (2 a 10 imagens)"""
    if len(images) < 2:
        raise ValueError("Carrossel exige no mínimo 2 imagens.")
    if len(images) > 10:
        raise ValueError("Carrossel aceita no máximo 10 imagens.")

    print(f"\nPublicando carrossel de {len(images)} slides no Instagram...")
    if dry_run:
        print("[DRY RUN] Validação OK. Use sem --dry-run para publicar.")
        return ""

    print("\nPasso 1/3 - Criando containers individuais...")
    ids = [create_media_container(img, is_carousel=True) for img in images]
    print(f"  {len(ids)} containers criados.")

    print("\nPasso 2/3 - Montando carrossel...")
    carousel_id = create_carousel(ids, caption)
    print(f"  Carrossel ID: {carousel_id}")

    print("\nPasso 3/3 - Publicando...")
    if not wait_ready(carousel_id, max_wait=120):
        raise RuntimeError("Timeout no processamento do carrossel.")
    post_id = publish(carousel_id)
    print(f"\n🎉 Publicado com sucesso!")
    print(f"Post ID: {post_id}")
    return post_id


def test_connection() -> dict:
    """Testa se as credenciais funcionam"""
    if not IG_ID or not PAGE_TOKEN:
        return {"ok": False, "error": "Credenciais não encontradas no .env"}
    resp = requests.get(
        f"{BASE_URL}/{IG_ID}",
        params={
            "fields": "id,username,name,followers_count,profile_picture_url",
            "access_token": PAGE_TOKEN,
        },
        timeout=15,
    )
    data = resp.json()
    if "username" in data:
        return {"ok": True, **data}
    return {"ok": False, "error": data}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publica no Instagram via Meta API")
    parser.add_argument("--images", nargs="+", help="Imagens a publicar (1 = post único, 2-10 = carrossel)")
    parser.add_argument("--caption", help="Legenda do post")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem publicar")
    parser.add_argument("--test", action="store_true", help="Apenas testa conexão")
    args = parser.parse_args()

    if args.test:
        print("Testando conexão com a Meta API...")
        result = test_connection()
        if result["ok"]:
            print(f"\n✅ Conexão OK!")
            print(f"   Username:  @{result['username']}")
            print(f"   Nome:      {result.get('name', '-')}")
            print(f"   Seguidores: {result.get('followers_count', '-'):,}")
            print(f"   IG ID:     {result['id']}")
        else:
            print(f"\n❌ Falha: {result['error']}")
            sys.exit(1)
        sys.exit(0)

    if not args.images or not args.caption:
        parser.error("--images e --caption são obrigatórios (a menos que use --test)")

    try:
        if len(args.images) == 1:
            publish_single(args.images[0], args.caption, args.dry_run)
        else:
            publish_carousel(args.images, args.caption, args.dry_run)
    except (RuntimeError, ValueError) as e:
        print(f"\n❌ ERRO: {e}", file=sys.stderr)
        sys.exit(1)
