from __future__ import annotations

import json
import re
import subprocess
import unittest
import urllib.request
from pathlib import Path

import yaml
from PIL import Image

from tests.test_desktop_runtime import desktop_runtime_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DesktopPackagingTest(unittest.TestCase):
    def _release_workflow(self) -> dict[str, object]:
        return yaml.safe_load(
            (PROJECT_ROOT / ".github/workflows/desktop-release.yml").read_text(
                encoding="utf-8"
            )
        )

    def test_release_workflow_builds_each_platform_natively(self) -> None:
        workflow = self._release_workflow()
        raw_workflow = (
            PROJECT_ROOT / ".github/workflows/desktop-release.yml"
        ).read_text(encoding="utf-8")

        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertNotIn("secrets.", raw_workflow.lower())
        self.assertNotIn("github_token", raw_workflow.lower())

        jobs = workflow["jobs"]
        self.assertEqual(set(jobs), {"macos", "windows"})

        expected_uploads = {
            "macos": ["desktop/src-tauri/target/release/bundle/dmg/*.dmg"],
            "windows": [
                "desktop/src-tauri/target/release/bundle/msi/*.msi",
                "desktop/src-tauri/target/release/bundle/nsis/*.exe",
            ],
        }
        for platform, runner in (("macos", "macos-latest"), ("windows", "windows-latest")):
            with self.subTest(platform=platform):
                job = jobs[platform]
                self.assertEqual(job["runs-on"], runner)
                steps = job["steps"]
                uses = [step["uses"] for step in steps if "uses" in step]
                self.assertTrue(uses)
                self.assertTrue(
                    all(re.search(r"@[0-9a-f]{40}$", action) for action in uses)
                )

                checkout = next(step for step in steps if step.get("name") == "Checkout")
                self.assertFalse(checkout["with"]["persist-credentials"])
                rust = next(
                    step for step in steps if step.get("name") == "Install Rust toolchain"
                )
                self.assertEqual(rust["with"]["toolchain"], "stable")

                stage = next(
                    step for step in steps if step.get("name") == "Build and stage the native sidecar"
                )
                self.assertIn("scripts/build_sidecar.py", stage["run"])
                self.assertIn("desktop/src-tauri/binaries", stage["run"])
                suffix = "-${target}" if platform == "macos" else "-$target.exe"
                self.assertIn(f"editor-carrosseis-sidecar{suffix}", stage["run"])

                build = next(
                    step for step in steps if step.get("name") == "Build Tauri bundle"
                )
                self.assertEqual(build["run"], "npm run build")
                verify = next(
                    step
                    for step in steps
                    if step.get("name") == "Verify native installer outputs"
                )
                for suffix in expected_uploads[platform]:
                    self.assertIn(suffix.rsplit("/", 1)[-1], verify["run"])
                upload = next(
                    step for step in steps if step.get("name").startswith("Upload")
                )
                paths = upload["with"]["path"].splitlines()
                self.assertEqual([path.strip() for path in paths], expected_uploads[platform])
                self.assertEqual(upload["with"]["if-no-files-found"], "error")

    def test_tauri_bundle_uses_versioned_square_icons(self) -> None:
        config = json.loads(
            (PROJECT_ROOT / "desktop/src-tauri/tauri.conf.json").read_text(
                encoding="utf-8"
            )
        )

        icons = config["bundle"]["icon"]
        self.assertEqual(
            icons,
            ["icons/icon.icns", "icons/icon.ico", "icons/icon.png"],
        )
        for relative_icon in icons:
            with self.subTest(icon=relative_icon):
                icon = PROJECT_ROOT / "desktop/src-tauri" / relative_icon
                self.assertTrue(icon.is_file())
                with Image.open(icon) as image:
                    self.assertEqual(image.width, image.height)
                    self.assertGreaterEqual(image.width, 256)

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
        self.assertFalse(config["app"]["windows"][0]["visible"])
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

    def test_windows_workflow_runs_the_production_rust_lifecycle_test(self) -> None:
        workflow = (
            PROJECT_ROOT / ".github/workflows/desktop-lifecycle-windows.yml"
        ).read_text(encoding="utf-8")

        self.assertRegex(workflow, r"runs-on:\s*windows-latest")
        self.assertIn(
            "cargo test --manifest-path desktop/src-tauri/Cargo.toml",
            workflow,
        )
        self.assertIn("tests.test_desktop_sidecar_integration", workflow)


if __name__ == "__main__":
    unittest.main()
