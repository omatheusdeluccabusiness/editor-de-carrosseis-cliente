from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from scripts.build_sidecar import build


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FrozenDesktopSidecarSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="carrossel-frozen-smoke-")
        root = Path(cls.temp_dir.name)
        cls.app_data_dir = root / "app-data"
        binary = build(root / "dist")
        if not binary.is_file():
            raise AssertionError("O builder não produziu o binário sidecar.")
        if b"credentials.enc.json" in binary.read_bytes():
            raise AssertionError("O binário sidecar incorpora o cofre de credenciais.")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            cls.port = probe.getsockname()[1]

        env = os.environ.copy()
        env["CARROSSEL_APP_DATA_DIR"] = str(cls.app_data_dir)
        env["CARROSSEL_EDITOR_PORT"] = str(cls.port)
        cls.process = subprocess.Popen(
            [str(binary)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        for _ in range(30):
            try:
                with urllib.request.urlopen(cls.base_url + "/api/health", timeout=1) as response:
                    if json.load(response) == {"ok": True, "service": "editor-carrosseis"}:
                        break
            except OSError:
                time.sleep(0.25)
        else:
            cls.tearDownClass()
            raise AssertionError("O sidecar congelado não iniciou.")

    @classmethod
    def tearDownClass(cls) -> None:
        process = getattr(cls, "process", None)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        cls.temp_dir.cleanup()

    def _csrf_token(self) -> str:
        with urllib.request.urlopen(self.base_url + "/", timeout=5) as response:
            page = response.read().decode("utf-8")
        match = re.search(r"window\.CARROSSEL_CSRF=(\"[^\"]+\")", page)
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_frozen_sidecar_creates_tweet_and_stories_sessions(self) -> None:
        csrf_token = self._csrf_token()
        for template_id, expected_template in (("tweet", "Modelo Tweet"), ("stories", "Modelo Stories")):
            with self.subTest(template=template_id):
                request = urllib.request.Request(
                    self.base_url + "/api/sessoes",
                    data=json.dumps({"template": template_id}).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Origin": self.base_url,
                        "X-Carrossel-CSRF": csrf_token,
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    self.assertEqual(response.status, 201)
                    session = json.load(response)

                self.assertTrue((self.app_data_dir / "sessions" / f"{session['session_id']}.html").is_file())
                with urllib.request.urlopen(self.base_url + session["url"], timeout=5) as response:
                    editor_html = response.read().decode("utf-8")
                self.assertIn("const HUB_SESSION = true;", editor_html)
                self.assertIn(expected_template, editor_html)


if __name__ == "__main__":
    unittest.main()
