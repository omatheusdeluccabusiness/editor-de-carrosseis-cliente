from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from scripts.build_sidecar import build


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HEALTH_PAYLOAD = b'{"ok": true, "service": "editor-carrosseis"}'


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.2)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def _wait_for(predicate, timeout: float, message: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(message)


def _health_is_available(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health", timeout=0.3
        ) as response:
            return response.read() == HEALTH_PAYLOAD
    except (OSError, urllib.error.URLError):
        return False


def _start_sentinel(port: int) -> subprocess.Popen[str]:
    code = """
import socket
import sys

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('127.0.0.1', int(sys.argv[1])))
listener.listen()
while True:
    client, _ = listener.accept()
    client.close()
"""
    sentinel = subprocess.Popen(
        [sys.executable, "-u", "-c", code, str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
    )
    _wait_for(
        lambda: sentinel.poll() is None and _port_is_open(port),
        timeout=3,
        message=f"sentinela não iniciou: {sentinel.stderr.read() if sentinel.poll() else ''}",
    )
    return sentinel


def _stop_process_tree(process: subprocess.Popen[str]) -> None:
    try:
        if process.poll() is not None:
            return
        if os.name == "nt":
            completed = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode:
                raise AssertionError(completed.stderr or completed.stdout)
        else:
            os.killpg(process.pid, 15)
        process.wait(timeout=5)
    finally:
        if process.stderr:
            process.stderr.close()


class DesktopSidecarIntegrationTest(unittest.TestCase):
    """Native sidecar lifecycle checks, also executed by each platform CI runner."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(prefix="carrossel-sidecar-integration-")
        cls.root = Path(cls.tempdir.name)
        cls.sidecar = build(cls.root / "binaries")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def _start_sidecar(self, port: int) -> subprocess.Popen[str]:
        app_data_dir = self.root / f"app-data-{port}"
        environment = os.environ.copy()
        environment.update(
            {
                "CARROSSEL_APP_DATA_DIR": str(app_data_dir),
                "CARROSSEL_EDITOR_PORT": str(port),
            }
        )
        return subprocess.Popen(
            [str(self.sidecar)],
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=os.name != "nt",
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
        )

    def test_sidecar_refuses_an_external_sentinel_without_stopping_it(self) -> None:
        port = _free_loopback_port()
        sentinel = _start_sentinel(port)
        sidecar = self._start_sidecar(port)
        try:
            _wait_for(
                lambda: sidecar.poll() is not None,
                timeout=5,
                message="sidecar não falhou ao encontrar a porta externa ocupada",
            )
            self.assertIsNone(sentinel.poll())
            self.assertTrue(_port_is_open(port))
        finally:
            _stop_process_tree(sidecar)
            _stop_process_tree(sentinel)

    def test_real_sidecar_tree_stops_without_touching_external_sentinel(self) -> None:
        sidecar_port = _free_loopback_port()
        sentinel_port = _free_loopback_port()
        sentinel = _start_sentinel(sentinel_port)
        sidecar = self._start_sidecar(sidecar_port)
        try:
            _wait_for(
                lambda: _health_is_available(sidecar_port),
                timeout=10,
                message="sidecar real não respondeu ao health check",
            )
            self.assertIsNone(sentinel.poll())

            _stop_process_tree(sidecar)

            _wait_for(
                lambda: not _health_is_available(sidecar_port),
                timeout=5,
                message="health do sidecar continuou disponível após encerrar a árvore",
            )
            self.assertIsNone(sentinel.poll())
            self.assertTrue(_port_is_open(sentinel_port))
        finally:
            _stop_process_tree(sidecar)
            _stop_process_tree(sentinel)


if __name__ == "__main__":
    unittest.main()
