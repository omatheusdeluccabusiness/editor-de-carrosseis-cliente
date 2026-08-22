from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from scripts.credenciais import (
    CredentialsError,
    decrypt_payload,
    encrypt_payload,
    generate_recovery_key,
    import_credentials_to_directory,
    import_telegram_text_source,
    restore_credentials,
    seal_credentials,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CredentialsCryptoTest(unittest.TestCase):
    def test_encrypted_payload_round_trips_without_plaintext(self) -> None:
        payload = {
            "telegram": {
                "botToken": "telegram-value-for-test",
                "chatId": "123456",
            },
            "meta": {
                "INSTAGRAM_ACCESS_TOKEN": "meta-value-for-test",
            },
        }

        envelope = encrypt_payload(payload, "recovery-key-for-test")

        self.assertEqual(
            decrypt_payload(envelope, "recovery-key-for-test"), payload
        )
        serialized = json.dumps(envelope)
        self.assertNotIn("telegram-value-for-test", serialized)
        self.assertNotIn("meta-value-for-test", serialized)

    def test_wrong_recovery_key_is_rejected(self) -> None:
        envelope = encrypt_payload(
            {"telegram": {"chatId": "123456"}},
            "correct-recovery-key",
        )

        with self.assertRaises(CredentialsError):
            decrypt_payload(envelope, "wrong-recovery-key")

    def test_generated_recovery_keys_are_unique(self) -> None:
        first = generate_recovery_key()
        second = generate_recovery_key()

        self.assertNotEqual(first, second)
        self.assertGreaterEqual(len(first), 40)
        self.assertNotIn("=", first)


class CredentialsFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.telegram_source = self.root / "telegram-source.json"
        self.meta_source = self.root / "meta-source.env"
        self.vault = self.root / "secrets" / "credentials.enc.json"
        self.key_file = self.root / "home" / ".carrossel-editor-recovery-key"
        self.restored_env = self.root / "clone" / ".env"
        self.restored_telegram = self.root / "other-home" / ".matheusao-telegram.json"
        self.telegram_source.write_text(
            json.dumps(
                {
                    "botToken": "telegram-value-for-test",
                    "chatId": "123456",
                }
            ),
            encoding="utf-8",
        )
        self.meta_source.write_text(
            "\n".join(
                (
                    "INSTAGRAM_BUSINESS_ID=987654",
                    "INSTAGRAM_ACCESS_TOKEN=meta-value-for-test",
                    "META_API_VERSION=v22.0",
                    "META_APP_ID=app-id-for-test",
                    "META_APP_SECRET=app-secret-for-test",
                    "UNRELATED_VALUE=must-not-be-exported",
                    "",
                )
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_seal_and_restore_write_expected_local_formats(self) -> None:
        seal_credentials(
            self.telegram_source,
            self.meta_source,
            self.vault,
            self.key_file,
        )

        restore_credentials(
            self.vault,
            self.key_file,
            self.restored_env,
            self.restored_telegram,
        )

        restored_meta = self.restored_env.read_text(encoding="utf-8")
        restored_tg = json.loads(
            self.restored_telegram.read_text(encoding="utf-8")
        )
        self.assertIn("INSTAGRAM_ACCESS_TOKEN=", restored_meta)
        self.assertIn("META_APP_SECRET=", restored_meta)
        self.assertNotIn("UNRELATED_VALUE", restored_meta)
        self.assertEqual(restored_tg["chatId"], "123456")
        self.assertEqual(restored_tg["botToken"], "telegram-value-for-test")
        if os.name != "nt":
            self.assertEqual(
                stat.S_IMODE(self.key_file.stat().st_mode),
                0o600,
            )

    def test_wrong_key_does_not_modify_existing_destinations(self) -> None:
        seal_credentials(
            self.telegram_source,
            self.meta_source,
            self.vault,
            self.key_file,
        )
        self.key_file.write_text("wrong-recovery-key", encoding="utf-8")
        self.restored_env.parent.mkdir(parents=True)
        self.restored_telegram.parent.mkdir(parents=True)
        self.restored_env.write_text("env-sentinel", encoding="utf-8")
        self.restored_telegram.write_text("telegram-sentinel", encoding="utf-8")

        with self.assertRaises(CredentialsError):
            restore_credentials(
                self.vault,
                self.key_file,
                self.restored_env,
                self.restored_telegram,
            )

        self.assertEqual(
            self.restored_env.read_text(encoding="utf-8"), "env-sentinel"
        )
        self.assertEqual(
            self.restored_telegram.read_text(encoding="utf-8"),
            "telegram-sentinel",
        )

    def test_desktop_import_restores_selected_encrypted_vault(self) -> None:
        seal_credentials(
            self.telegram_source,
            self.meta_source,
            self.vault,
            self.key_file,
        )
        destination = self.root / "desktop-data" / "credentials"

        import_credentials_to_directory(
            self.vault.read_text(encoding="utf-8"),
            self.key_file.read_text(encoding="utf-8").strip(),
            destination,
        )

        self.assertTrue((destination / "credentials.enc.json").is_file())
        self.assertTrue((destination / ".carrossel-editor-recovery-key").is_file())
        self.assertIn(
            "INSTAGRAM_ACCESS_TOKEN=",
            (destination / ".env").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            json.loads(
                (destination / ".matheusao-telegram.json").read_text(encoding="utf-8")
            )["chatId"],
            "123456",
        )

    def test_desktop_import_invalid_vault_leaves_existing_state_unchanged(self) -> None:
        destination = self.root / "desktop-data" / "credentials"
        destination.mkdir(parents=True)
        sentinels = {
            "credentials.enc.json": "vault-sentinel",
            ".carrossel-editor-recovery-key": "key-sentinel",
            ".env": "env-sentinel",
            ".matheusao-telegram.json": "telegram-sentinel",
        }
        for name, content in sentinels.items():
            (destination / name).write_text(content, encoding="utf-8")

        with self.assertRaises(CredentialsError):
            import_credentials_to_directory("not-json", "wrong-key", destination)

        for name, content in sentinels.items():
            self.assertEqual((destination / name).read_text(encoding="utf-8"), content)

    def test_telegram_text_migration_writes_only_the_local_destination(self) -> None:
        text_source = self.root / "telegram-transfer.txt"
        destination = self.root / "other-home" / ".matheusao-telegram.json"
        text_source.write_text(
            "Bot token: 123456:abcdefghijklmnopqrstuvwx\nChat ID: -1001234567890\n",
            encoding="utf-8",
        )

        import_telegram_text_source(text_source, destination)

        restored = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(restored["botToken"], "123456:abcdefghijklmnopqrstuvwx")
        self.assertEqual(restored["chatId"], "-1001234567890")


class CredentialsBootstrapTest(unittest.TestCase):
    def test_bootstrap_scripts_and_docs_expose_first_use_flow(self) -> None:
        configure = (PROJECT_ROOT / "configurar-credenciais.sh").read_text(
            encoding="utf-8"
        )
        start = (PROJECT_ROOT / "start.sh").read_text(encoding="utf-8")
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("scripts/credenciais.py restore", configure)
        self.assertIn("scripts/credenciais.py restore --if-needed", start)
        self.assertIn("secrets/*", gitignore)
        self.assertIn("!secrets/credentials.enc.json", gitignore)
        self.assertIn("./configurar-credenciais.sh", readme)
        self.assertIn("chave de recuperacao", readme.lower())


if __name__ == "__main__":
    unittest.main()
