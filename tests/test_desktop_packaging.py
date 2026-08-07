from __future__ import annotations

import json
import subprocess
import unittest
import urllib.request
from pathlib import Path

from tests.test_desktop_runtime import desktop_runtime_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DesktopPackagingTest(unittest.TestCase):
    def test_tauri_configuration_uses_native_window_and_sidecar(self) -> None:
        config = json.loads(
            (PROJECT_ROOT / "desktop/src-tauri/tauri.conf.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(config["productName"], "Editor de Carrosseis")
        self.assertEqual(
            config["bundle"]["externalBin"], ["binaries/editor-carrosseis-sidecar"]
        )
        self.assertFalse(config["app"]["windows"][0]["create"])
        self.assertNotIn("http://", config["app"]["security"]["csp"])
        self.assertNotIn("https://", config["app"]["security"]["csp"])

    def test_editor_documents_are_local_only_after_navigation(self) -> None:
        stories = (PROJECT_ROOT / "templates/stories_editor.html").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("fonts.googleapis.com", stories)
        self.assertNotIn("fonts.gstatic.com", stories)

        with desktop_runtime_server() as (_, base_url):
            with urllib.request.urlopen(base_url + "/") as response:
                csp = response.headers["Content-Security-Policy"]

        self.assertEqual(
            csp,
            "default-src 'self'; base-uri 'none'; form-action 'self'; "
            "object-src 'none'; img-src 'self' data: blob:; "
            "font-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'",
        )

    def test_tauri_command_prepares_host_sidecar_before_running(self) -> None:
        package = json.loads((PROJECT_ROOT / "desktop/package.json").read_text())
        self.assertEqual(
            package["scripts"]["pretauri"], "node scripts/prepare-sidecar.mjs"
        )
        self.assertEqual(
            package["scripts"]["test:sidecar-integration"],
            "node scripts/run-sidecar-integration.mjs",
        )

        for script in (
            "prepare-sidecar.mjs",
            "run-sidecar-integration.mjs",
        ):
            with self.subTest(script=script):
                result = subprocess.run(
                    ["node", "--check", str(PROJECT_ROOT / "desktop/scripts" / script)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
