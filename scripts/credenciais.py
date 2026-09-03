#!/usr/bin/env python3
"""Cofre portátil de credenciais do editor de carrosséis."""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import re
import secrets
import sys
import tempfile
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from dotenv import dotenv_values

try:
    from scripts.desktop_paths import desktop_runtime_paths
except ImportError:
    from desktop_paths import desktop_runtime_paths


VAULT_VERSION = 1
ASSOCIATED_DATA = b"carrossel-editor-credentials-v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DATA_DIR = os.environ.get("CARROSSEL_APP_DATA_DIR")
RUNTIME_PATHS = desktop_runtime_paths(APP_DATA_DIR) if APP_DATA_DIR else None
DEFAULT_VAULT_PATH = (
    RUNTIME_PATHS.credentials_dir / "credentials.enc.json"
    if RUNTIME_PATHS
    else PROJECT_ROOT / "secrets" / "credentials.enc.json"
)
DEFAULT_KEY_PATH = (
    RUNTIME_PATHS.credentials_dir / ".carrossel-editor-recovery-key"
    if RUNTIME_PATHS
    else Path.home() / ".carrossel-editor-recovery-key"
)
DEFAULT_PROJECT_ENV_PATH = (
    RUNTIME_PATHS.credentials_dir / ".env"
    if RUNTIME_PATHS
    else PROJECT_ROOT / ".env"
)
DEFAULT_TELEGRAM_PATH = (
    RUNTIME_PATHS.credentials_dir / ".matheusao-telegram.json"
    if RUNTIME_PATHS
    else Path.home() / ".matheusao-telegram.json"
)
META_KEYS = (
    "INSTAGRAM_BUSINESS_ID",
    "INSTAGRAM_ACCESS_TOKEN",
    "INSTAGRAM_TOKEN_EXPIRES_AT",
    "INSTAGRAM_USERNAME",
    "META_API_VERSION",
    "META_APP_ID",
    "META_APP_NAME",
    "META_APP_SECRET",
)


class CredentialsError(RuntimeError):
    """Erro seguro de leitura ou escrita do cofre."""


def _encode_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_bytes(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _derive_key(recovery_key: str, salt: bytes) -> bytes:
    if not recovery_key:
        raise CredentialsError("A chave de recuperação está vazia.")
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(
        recovery_key.encode("utf-8")
    )


def generate_recovery_key() -> str:
    """Gera uma chave URL-safe com 256 bits de entropia."""

    return secrets.token_urlsafe(32).rstrip("=")


def encrypt_payload(payload: dict[str, Any], recovery_key: str) -> dict[str, Any]:
    """Criptografa um payload JSON em um envelope autenticado."""

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = _derive_key(recovery_key, salt)
    plaintext = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, ASSOCIATED_DATA)
    return {
        "version": VAULT_VERSION,
        "cipher": "AES-256-GCM",
        "kdf": "scrypt-n16384-r8-p1",
        "salt": _encode_bytes(salt),
        "nonce": _encode_bytes(nonce),
        "ciphertext": _encode_bytes(ciphertext),
    }


def decrypt_payload(envelope: dict[str, Any], recovery_key: str) -> dict[str, Any]:
    """Abre um envelope ou levanta um erro que não revela detalhes sensíveis."""

    try:
        if envelope.get("version") != VAULT_VERSION:
            raise CredentialsError("Versão de cofre incompatível.")
        salt = _decode_bytes(str(envelope["salt"]))
        nonce = _decode_bytes(str(envelope["nonce"]))
        ciphertext = _decode_bytes(str(envelope["ciphertext"]))
        key = _derive_key(recovery_key, salt)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, ASSOCIATED_DATA)
        payload = json.loads(plaintext.decode("utf-8"))
        if not isinstance(payload, dict):
            raise CredentialsError("Conteúdo do cofre inválido.")
        return payload
    except CredentialsError:
        raise
    except (InvalidTag, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise CredentialsError("Cofre ou chave de recuperação inválidos.") from error


def _atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        if os.name != "nt":
            os.chmod(temp_path, mode)
        temp_path.replace(path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def _read_recovery_key(path: Path) -> str:
    try:
        recovery_key = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise CredentialsError("A chave de recuperação local não foi encontrada.") from error
    if not recovery_key:
        raise CredentialsError("A chave de recuperação local está vazia.")
    return recovery_key


def _validate_payload(payload: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    telegram = payload.get("telegram")
    meta = payload.get("meta")
    if not isinstance(telegram, dict) or not isinstance(meta, dict):
        raise CredentialsError("O cofre não contém as seções obrigatórias.")

    telegram_clean = {
        "botToken": str(telegram.get("botToken", "")).strip(),
        "chatId": str(telegram.get("chatId", "")).strip(),
    }
    meta_clean = {
        key: str(meta.get(key, "")).strip()
        for key in META_KEYS
        if str(meta.get(key, "")).strip()
    }
    if not telegram_clean["botToken"] or not telegram_clean["chatId"]:
        raise CredentialsError("As credenciais do Telegram estão incompletas.")
    if not meta_clean.get("INSTAGRAM_BUSINESS_ID") or not meta_clean.get(
        "INSTAGRAM_ACCESS_TOKEN"
    ):
        raise CredentialsError("As credenciais do Instagram estão incompletas.")
    return telegram_clean, meta_clean


def seal_credentials(
    telegram_path: Path,
    meta_env_path: Path,
    vault_path: Path,
    key_path: Path,
) -> None:
    """Lê fontes locais e grava somente o envelope criptografado."""

    try:
        telegram = json.loads(telegram_path.read_text(encoding="utf-8"))
        meta_values = dotenv_values(meta_env_path)
    except (OSError, json.JSONDecodeError) as error:
        raise CredentialsError("Não foi possível ler as fontes de credenciais.") from error

    payload = {
        "telegram": telegram,
        "meta": {
            key: str(meta_values.get(key, "")).strip()
            for key in META_KEYS
            if str(meta_values.get(key, "")).strip()
        },
    }
    _validate_payload(payload)

    if key_path.exists():
        recovery_key = _read_recovery_key(key_path)
    else:
        recovery_key = generate_recovery_key()
        _atomic_write(key_path, recovery_key + "\n", mode=0o600)

    envelope = encrypt_payload(payload, recovery_key)
    _atomic_write(
        vault_path,
        json.dumps(envelope, indent=2, sort_keys=True) + "\n",
        mode=0o600,
    )


def restore_credentials(
    vault_path: Path,
    key_path: Path,
    project_env_path: Path,
    telegram_path: Path,
) -> None:
    """Restaura os formatos locais depois de validar todo o cofre."""

    try:
        envelope = json.loads(vault_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CredentialsError("O cofre criptografado não pôde ser lido.") from error

    recovery_key = _read_recovery_key(key_path)
    payload = decrypt_payload(envelope, recovery_key)
    telegram, meta = _validate_payload(payload)

    env_content = "\n".join(
        f"{key}={json.dumps(meta[key], ensure_ascii=False)}"
        for key in META_KEYS
        if key in meta
    ) + "\n"
    telegram_content = json.dumps(
        telegram,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    _atomic_write(project_env_path, env_content, mode=0o600)
    _atomic_write(telegram_path, telegram_content, mode=0o600)


def import_credentials_to_directory(
    vault_json: str,
    recovery_key: str,
    credentials_dir: Path,
) -> None:
    """Validate a user-selected vault, then restore it into desktop app data.

    The vault and recovery key are deliberately supplied by the local user
    interface; neither belongs in the application bundle.  Parsing, decrypting
    and payload validation happen before any destination is modified so a bad
    import cannot replace a working local configuration.
    """

    if not isinstance(vault_json, str) or len(vault_json.encode("utf-8")) > 131072:
        raise CredentialsError("Cofre ou chave de recuperação inválidos.")
    if not isinstance(recovery_key, str) or not recovery_key.strip() or len(recovery_key) > 1024:
        raise CredentialsError("Cofre ou chave de recuperação inválidos.")

    try:
        envelope = json.loads(vault_json)
    except (TypeError, json.JSONDecodeError) as error:
        raise CredentialsError("Cofre ou chave de recuperação inválidos.") from error
    if not isinstance(envelope, dict):
        raise CredentialsError("Cofre ou chave de recuperação inválidos.")

    # Complete validation must precede every write.
    payload = decrypt_payload(envelope, recovery_key.strip())
    telegram, meta = _validate_payload(payload)
    env_content = "\n".join(
        f"{key}={json.dumps(meta[key], ensure_ascii=False)}"
        for key in META_KEYS
        if key in meta
    ) + "\n"
    telegram_content = json.dumps(
        telegram,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    vault_content = json.dumps(envelope, indent=2, sort_keys=True) + "\n"

    credentials_dir = credentials_dir.expanduser().resolve()
    _atomic_write(credentials_dir / "credentials.enc.json", vault_content, mode=0o600)
    _atomic_write(
        credentials_dir / ".carrossel-editor-recovery-key",
        recovery_key.strip() + "\n",
        mode=0o600,
    )
    _atomic_write(credentials_dir / ".env", env_content, mode=0o600)
    _atomic_write(
        credentials_dir / ".matheusao-telegram.json", telegram_content, mode=0o600
    )


def credentials_ready(project_env_path: Path, telegram_path: Path) -> bool:
    try:
        meta = dotenv_values(project_env_path)
        telegram = json.loads(telegram_path.read_text(encoding="utf-8"))
        return bool(
            meta.get("INSTAGRAM_BUSINESS_ID")
            and meta.get("INSTAGRAM_ACCESS_TOKEN")
            and telegram.get("botToken")
            and telegram.get("chatId")
        )
    except (OSError, json.JSONDecodeError):
        return False


def read_telegram_text_source(source_path: Path) -> tuple[str, str]:
    """Lê o TXT simples de configuração do Telegram sem expor seus valores."""

    try:
        text = source_path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise CredentialsError("O arquivo local do Telegram não pôde ser lido.") from error
    if len(text.encode("utf-8")) > 16_384:
        raise CredentialsError("O arquivo local do Telegram é inválido.")

    token_match = re.search(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b", text)
    labeled_chat = re.search(
        r"(?im)^\s*(?:chat[ _-]*id|id[ _-]*chat|chat)\s*[:=-]\s*(-?\d{5,})\s*$",
        text,
    )
    chat_id = labeled_chat.group(1) if labeled_chat else ""
    if not chat_id:
        candidates = re.findall(r"(?<![\w:-])-?\d{5,}(?![\w:-])", text)
        chat_id = candidates[-1] if candidates else ""
    if not token_match or not chat_id:
        raise CredentialsError("O arquivo local do Telegram está incompleto.")

    return token_match.group(0), chat_id


def import_telegram_text_source(source_path: Path, telegram_path: Path) -> None:
    """Importa uma migração local de Telegram sem registrar os valores.

    É destinado somente à transferência pontual entre computadores. O arquivo
    de origem deve ser removido após uma conexão bem-sucedida.
    """

    token, chat_id = read_telegram_text_source(source_path)

    telegram_content = json.dumps(
        {"botToken": token, "chatId": chat_id},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    _atomic_write(telegram_path, telegram_content, mode=0o600)


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configura o cofre criptografado do editor de carrosséis."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seal = subparsers.add_parser("seal", help="Cria ou atualiza o cofre.")
    seal.add_argument("--telegram", required=True, type=_path)
    seal.add_argument("--meta-env", required=True, type=_path)
    seal.add_argument("--vault", type=_path, default=DEFAULT_VAULT_PATH)
    seal.add_argument("--key-file", type=_path, default=DEFAULT_KEY_PATH)

    restore = subparsers.add_parser("restore", help="Restaura credenciais locais.")
    restore.add_argument("--vault", type=_path, default=DEFAULT_VAULT_PATH)
    restore.add_argument("--key-file", type=_path, default=DEFAULT_KEY_PATH)
    restore.add_argument("--project-env", type=_path, default=DEFAULT_PROJECT_ENV_PATH)
    restore.add_argument("--telegram-dest", type=_path, default=DEFAULT_TELEGRAM_PATH)
    restore.add_argument("--if-needed", action="store_true")
    restore.add_argument("--non-interactive", action="store_true")

    status = subparsers.add_parser("status", help="Mostra somente presença e caminhos.")
    status.add_argument("--vault", type=_path, default=DEFAULT_VAULT_PATH)
    status.add_argument("--key-file", type=_path, default=DEFAULT_KEY_PATH)
    status.add_argument("--project-env", type=_path, default=DEFAULT_PROJECT_ENV_PATH)
    status.add_argument("--telegram-dest", type=_path, default=DEFAULT_TELEGRAM_PATH)

    telegram_import = subparsers.add_parser(
        "import-telegram",
        help="Importa uma transferência local de Telegram sem exibir as credenciais.",
    )
    telegram_import.add_argument("--source", required=True, type=_path)
    telegram_import.add_argument(
        "--telegram-dest", type=_path, default=DEFAULT_TELEGRAM_PATH
    )
    return parser


def _run_restore(args: argparse.Namespace) -> int:
    if args.if_needed and credentials_ready(args.project_env, args.telegram_dest):
        return 0

    if not args.key_file.exists():
        if args.non_interactive:
            print(
                "Cofre disponível. Rode ./configurar-credenciais.sh uma vez "
                "para habilitar publicações neste computador."
            )
            return 0 if args.if_needed else 2
        recovery_key = os.environ.get("CARROSSEL_RECOVERY_KEY", "").strip()
        if not recovery_key:
            recovery_key = getpass.getpass("Cole a chave de recuperação: ").strip()
        if not recovery_key:
            raise CredentialsError("A chave de recuperação está vazia.")
        _atomic_write(args.key_file, recovery_key + "\n", mode=0o600)

    restore_credentials(
        args.vault,
        args.key_file,
        args.project_env,
        args.telegram_dest,
    )
    print("Credenciais locais restauradas com segurança.")
    print(f"Meta/Instagram: {args.project_env}")
    print(f"Telegram: {args.telegram_dest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "seal":
            seal_credentials(args.telegram, args.meta_env, args.vault, args.key_file)
            print(f"Cofre criptografado criado: {args.vault}")
            print(f"Chave de recuperação local criada: {args.key_file}")
            return 0
        if args.command == "restore":
            return _run_restore(args)
        if args.command == "status":
            print(f"cofre: {'ok' if args.vault.exists() else 'ausente'}")
            print(f"chave local: {'ok' if args.key_file.exists() else 'ausente'}")
            print(
                "credenciais locais: "
                f"{'ok' if credentials_ready(args.project_env, args.telegram_dest) else 'ausentes'}"
            )
            return 0
        if args.command == "import-telegram":
            import_telegram_text_source(args.source, args.telegram_dest)
            print("Credenciais locais do Telegram importadas.")
            return 0
    except CredentialsError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
