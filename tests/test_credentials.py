from __future__ import annotations

import json
import unittest

from scripts.credenciais import (
    CredentialsError,
    decrypt_payload,
    encrypt_payload,
    generate_recovery_key,
)


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


if __name__ == "__main__":
    unittest.main()
