#!/usr/bin/env python3
"""Cofre portátil de credenciais do editor de carrosséis."""

from __future__ import annotations

import base64
import json
import secrets
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


VAULT_VERSION = 1
ASSOCIATED_DATA = b"carrossel-editor-credentials-v1"


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
