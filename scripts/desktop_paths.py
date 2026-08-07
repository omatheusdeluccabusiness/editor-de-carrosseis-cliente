"""Paths owned by the packaged desktop application runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    """Directories that must remain outside the application bundle."""

    editor_dir: Path
    credentials_dir: Path


def desktop_runtime_paths(app_data_dir: str | None) -> RuntimePaths:
    """Build the desktop runtime layout from the app-provided data directory."""

    if not app_data_dir:
        raise ValueError("CARROSSEL_APP_DATA_DIR não foi definido.")
    root = Path(app_data_dir).expanduser().resolve()
    return RuntimePaths(root / "sessions", root / "credentials")
