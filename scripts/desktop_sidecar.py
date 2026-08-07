#!/usr/bin/env python3
"""Executable entrypoint for the packaged desktop application's local server."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _runtime_directory() -> Path:
    """Return the application-owned directory supplied by Tauri."""

    app_data_dir = os.environ.get("CARROSSEL_APP_DATA_DIR")
    if not app_data_dir:
        raise ValueError("CARROSSEL_APP_DATA_DIR não foi definido.")
    return Path(app_data_dir).expanduser().resolve()


def main() -> int:
    """Serve the existing local handler on loopback for the desktop application."""

    try:
        app_data_dir = _runtime_directory()
    except ValueError as error:
        print(f"[desktop-sidecar] {error}", file=sys.stderr)
        return 2

    editor_dir = app_data_dir / "sessions"
    editor_dir.mkdir(parents=True, exist_ok=True)
    os.environ["CARROSSEL_EDITOR_DIR"] = str(editor_dir)

    # Import only after configuring the runtime: serve_carrossel reads its
    # environment at module import time. This deliberately bypasses the CLI
    # supervisor and serves the same handler used by the local web editor.
    import serve_carrossel

    os.chdir(serve_carrossel.DIR)
    with serve_carrossel.ReusableThreadingTCPServer(
        ("127.0.0.1", serve_carrossel.PORT), serve_carrossel.CarrosselHandler
    ) as httpd:
        print(
            "[desktop-sidecar] servindo "
            f"{serve_carrossel.DIR} em http://127.0.0.1:{serve_carrossel.PORT}"
        )
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[desktop-sidecar] encerrando.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
