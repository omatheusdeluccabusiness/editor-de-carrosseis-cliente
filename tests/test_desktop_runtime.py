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
from scripts.desktop_paths import desktop_runtime_paths


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


if __name__ == "__main__":
    unittest.main()
