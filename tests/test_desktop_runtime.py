from __future__ import annotations

import base64
import importlib
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import serve_carrossel
from scripts.credenciais import encrypt_payload
from scripts.desktop_paths import desktop_runtime_paths


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def desktop_runtime_server():
    previous_env = os.environ.get("CARROSSEL_APP_DATA_DIR")
    with tempfile.TemporaryDirectory() as tmp:
        app_data_dir = Path(tmp).resolve()
        os.environ["CARROSSEL_APP_DATA_DIR"] = str(app_data_dir)
        importlib.reload(serve_carrossel)
        server = serve_carrossel.ReusableThreadingTCPServer(
            ("127.0.0.1", 0), serve_carrossel.CarrosselHandler
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            yield app_data_dir, f"http://{host}:{port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            if previous_env is None:
                os.environ.pop("CARROSSEL_APP_DATA_DIR", None)
            else:
                os.environ["CARROSSEL_APP_DATA_DIR"] = previous_env
            importlib.reload(serve_carrossel)


class DesktopRuntimeTest(unittest.TestCase):
    def test_sidecar_entrypoint_uses_loopback_and_healthcheck(self) -> None:
        source = (PROJECT_ROOT / "scripts" / "desktop_sidecar.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("127.0.0.1", source)
        self.assertIn("CARROSSEL_APP_DATA_DIR", source)

    def test_sidecar_builder_includes_templates_and_assets(self) -> None:
        source = (PROJECT_ROOT / "scripts" / "build_sidecar.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("templates", source)
        self.assertIn("assets", source)
        self.assertNotIn("credentials.enc.json", source)

    def test_desktop_paths_keep_runtime_and_credentials_out_of_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp).resolve()
            paths = desktop_runtime_paths(str(tmp_path))

            self.assertEqual(paths.editor_dir, tmp_path / "sessions")
            self.assertEqual(paths.credentials_dir, tmp_path / "credentials")

    def test_desktop_runtime_uses_isolated_paths_and_health_is_loopback_only(self) -> None:
        with desktop_runtime_server() as (app_data_dir, base_url):
            self.assertEqual(serve_carrossel.DIR, str(app_data_dir / "sessions"))
            self.assertEqual(
                serve_carrossel.HOME_TG,
                str(app_data_dir / "credentials" / ".matheusao-telegram.json"),
            )

            with urllib.request.urlopen(base_url + "/api/health") as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(
                    json.load(response),
                    {"ok": True, "service": "editor-carrosseis"},
                )

            request = urllib.request.Request(
                base_url + "/api/health", headers={"Host": "example.invalid"}
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request)
            self.assertEqual(raised.exception.code, 403)

    def test_publish_endpoint_passes_desktop_runtime_to_publisher(self) -> None:
        image = base64.b64encode(b"png").decode("ascii")
        with desktop_runtime_server() as (app_data_dir, base_url), patch.object(
            serve_carrossel.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout="Post ID: 123", stderr=""),
        ) as run:
            request = urllib.request.Request(
                base_url + "/api/publicar-instagram",
                data=json.dumps(
                    {"slides_b64": [image, image], "caption": "teste"}
                ).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Origin": base_url,
                    "X-Carrossel-CSRF": serve_carrossel.CSRF_TOKEN,
                },
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                self.assertEqual(json.load(response)["post_id"], "123")

            self.assertEqual(
                run.call_args.kwargs["env"]["CARROSSEL_APP_DATA_DIR"], str(app_data_dir)
            )

    def test_desktop_credentials_import_is_local_authorized_and_redacted(self) -> None:
        recovery_key = "desktop-recovery-key-for-test"
        envelope = encrypt_payload(
            {
                "telegram": {"botToken": "telegram-secret", "chatId": "123"},
                "meta": {
                    "INSTAGRAM_BUSINESS_ID": "456",
                    "INSTAGRAM_ACCESS_TOKEN": "meta-secret",
                },
            },
            recovery_key,
        )
        body = json.dumps(
            {"vault_json": json.dumps(envelope), "recovery_key": recovery_key}
        ).encode()
        with desktop_runtime_server() as (app_data_dir, base_url):
            with urllib.request.urlopen(
                base_url + "/api/desktop-credentials/status"
            ) as response:
                self.assertEqual(json.load(response), {"configured": False})

            unauthorized = urllib.request.Request(
                base_url + "/api/desktop-credentials/import",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(unauthorized)
            self.assertEqual(raised.exception.code, 403)
            self.assertFalse((app_data_dir / "credentials" / ".env").exists())

            invalid = urllib.request.Request(
                base_url + "/api/desktop-credentials/import",
                data=json.dumps(
                    {"vault_json": json.dumps(envelope), "recovery_key": "wrong-key"}
                ).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Origin": base_url,
                    "X-Carrossel-CSRF": serve_carrossel.CSRF_TOKEN,
                },
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(invalid)
            self.assertEqual(raised.exception.code, 400)
            invalid_response = raised.exception.read().decode("utf-8")
            self.assertEqual(json.loads(invalid_response), {"error": "cofre_ou_chave_invalidos"})
            self.assertNotIn("telegram-secret", invalid_response)
            self.assertFalse((app_data_dir / "credentials" / ".env").exists())

            authorized = urllib.request.Request(
                base_url + "/api/desktop-credentials/import",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Origin": base_url,
                    "X-Carrossel-CSRF": serve_carrossel.CSRF_TOKEN,
                },
                method="POST",
            )
            with urllib.request.urlopen(authorized) as response:
                self.assertEqual(json.load(response), {"ok": True, "configured": True})

            with urllib.request.urlopen(
                base_url + "/api/desktop-credentials/status"
            ) as response:
                status_response = response.read().decode("utf-8")
            self.assertEqual(json.loads(status_response), {"configured": True})
            self.assertNotIn("telegram-secret", status_response)
            self.assertNotIn("meta-secret", status_response)
            self.assertTrue((app_data_dir / "credentials" / "credentials.enc.json").is_file())


if __name__ == "__main__":
    unittest.main()
