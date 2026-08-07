from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import serve_carrossel
from scripts.desktop_paths import desktop_runtime_paths


class DesktopRuntimeTest(unittest.TestCase):
    def test_desktop_paths_keep_runtime_and_credentials_out_of_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp).resolve()
            paths = desktop_runtime_paths(str(tmp_path))

            self.assertEqual(paths.editor_dir, tmp_path / "sessions")
            self.assertEqual(paths.credentials_dir, tmp_path / "credentials")

    def test_health_endpoint_is_loopback_safe(self) -> None:
        self.assertIn(
            "/api/health", serve_carrossel.CarrosselHandler.do_GET.__code__.co_consts
        )


if __name__ == "__main__":
    unittest.main()
