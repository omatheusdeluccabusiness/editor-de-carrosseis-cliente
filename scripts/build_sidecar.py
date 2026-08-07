#!/usr/bin/env python3
"""Build the Python sidecar used by the Tauri desktop application."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIDECAR_NAME = "editor-carrosseis-sidecar"


def build(target_dir: Path) -> Path:
    """Create a one-file sidecar binary, returning its output path."""

    try:
        import PyInstaller.__main__
    except ImportError as error:
        raise RuntimeError(
            "PyInstaller não está instalado. Rode pip install -r requirements.txt."
        ) from error

    target_dir = target_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    datas = [
        (PROJECT_ROOT / "templates", "templates"),
        (PROJECT_ROOT / "assets", "assets"),
        (PROJECT_ROOT / "secrets" / "credentials.enc.json", "secrets"),
    ]
    add_data = [f"{source}{os.pathsep}{destination}" for source, destination in datas]

    with tempfile.TemporaryDirectory(prefix="carrossel-sidecar-build-") as work_dir:
        PyInstaller.__main__.run(
            [
                "--noconfirm",
                "--clean",
                "--onefile",
                "--name",
                SIDECAR_NAME,
                "--distpath",
                str(target_dir),
                "--workpath",
                work_dir,
                "--specpath",
                work_dir,
                "--hidden-import",
                "serve_carrossel",
                *[item for pair in zip(["--add-data"] * len(add_data), add_data) for item in pair],
                str(PROJECT_ROOT / "scripts" / "desktop_sidecar.py"),
            ]
        )

    suffix = ".exe" if sys.platform == "win32" else ""
    return target_dir / f"{SIDECAR_NAME}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        output = build(args.target_dir)
    except RuntimeError as error:
        print(f"[build-sidecar] {error}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
