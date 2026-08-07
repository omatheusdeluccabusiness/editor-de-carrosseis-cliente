from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DesktopPackagingTest(unittest.TestCase):
    def test_tauri_configuration_uses_native_window_and_sidecar(self) -> None:
        config = json.loads(
            (PROJECT_ROOT / "desktop/src-tauri/tauri.conf.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(config["productName"], "Editor de Carrosseis")
        self.assertIn("externalBin", config["bundle"])

    def test_rust_shell_waits_for_health_and_stops_child(self) -> None:
        source = (PROJECT_ROOT / "desktop/src-tauri/src/main.rs").read_text(
            encoding="utf-8"
        )

        self.assertIn("/api/health", source)
        self.assertIn("ExitRequested", source)


if __name__ == "__main__":
    unittest.main()
