#!/usr/bin/env python3
"""Small persistent supervisor for the local carousel editor server."""

from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


PORT = int(os.environ.get("CARROSSEL_EDITOR_PORT", "8777"))
EDITOR_DIR = Path(os.environ.get("CARROSSEL_EDITOR_DIR", "/tmp/carrossel-editor"))
SUPERVISOR_PID_FILE = EDITOR_DIR / "carrossel-supervisor.pid"
SERVER_PID_FILE = EDITOR_DIR / "carrossel-server.pid"
LOG_FILE = EDITOR_DIR / "server.log"
SERVER_SCRIPT = Path(__file__).with_name("serve_carrossel.py")


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # No Windows, os.kill(pid, 0) pode lançar WinError 87 para um PID
        # órfão/stale. Ele não representa um processo que possamos supervisionar.
        return False


def _read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def _write_pid(path: Path, pid: int) -> None:
    EDITOR_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid))


def _terminate_process(pid: int) -> None:
    """Terminate a supervised process on either POSIX or Windows."""
    try:
        if os.name != "nt" and hasattr(os, "killpg"):
            os.killpg(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _remove_pid(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _port_open(port: int = PORT) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def _wait_for_port(timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open():
            return True
        time.sleep(0.25)
    return False


def start() -> int:
    EDITOR_DIR.mkdir(parents=True, exist_ok=True)

    if _port_open():
        print(f"carrossel server already running on http://localhost:{PORT}")
        return 0

    supervisor_pid = _read_pid(SUPERVISOR_PID_FILE)
    if supervisor_pid and _is_pid_running(supervisor_pid):
        if _wait_for_port():
            print(f"carrossel supervisor already active (PID {supervisor_pid})")
            return 0
        print(f"carrossel supervisor active but port {PORT} is not ready yet")
        return 1

    log = open(LOG_FILE, "a", buffering=1)
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "supervise"],
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    _write_pid(SUPERVISOR_PID_FILE, proc.pid)

    if _wait_for_port():
        print(f"carrossel supervisor started (PID {proc.pid})")
        print(f"http://localhost:{PORT}")
        return 0

    print(f"carrossel supervisor started, but server did not answer. See {LOG_FILE}")
    return 1


def stop() -> int:
    stopped = False

    supervisor_pid = _read_pid(SUPERVISOR_PID_FILE)
    if supervisor_pid and _is_pid_running(supervisor_pid):
        _terminate_process(supervisor_pid)
        stopped = True
    _remove_pid(SUPERVISOR_PID_FILE)

    server_pid = _read_pid(SERVER_PID_FILE)
    if server_pid and _is_pid_running(server_pid):
        _terminate_process(server_pid)
        stopped = True
    _remove_pid(SERVER_PID_FILE)

    if stopped:
        print("carrossel server stopped")
    else:
        print("carrossel server was not running")
    return 0


def status() -> int:
    supervisor_pid = _read_pid(SUPERVISOR_PID_FILE)
    server_pid = _read_pid(SERVER_PID_FILE)
    port = _port_open()
    print(f"port {PORT}: {'open' if port else 'closed'}")
    print(f"supervisor pid: {supervisor_pid or '-'}")
    print(f"server pid: {server_pid or '-'}")
    return 0 if port else 1


def supervise() -> int:
    EDITOR_DIR.mkdir(parents=True, exist_ok=True)
    _write_pid(SUPERVISOR_PID_FILE, os.getpid())
    child: subprocess.Popen | None = None

    def shutdown(signum, frame):
        if child and child.poll() is None:
            _terminate_process(child.pid)
        _remove_pid(SERVER_PID_FILE)
        _remove_pid(SUPERVISOR_PID_FILE)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while True:
        if _port_open() and child is None:
            time.sleep(5)
            continue

        if child is None or child.poll() is not None:
            with open(LOG_FILE, "a", buffering=1) as log:
                print(f"[supervisor] starting {SERVER_SCRIPT}", file=log)
                child = subprocess.Popen(
                    [sys.executable, str(SERVER_SCRIPT)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            _write_pid(SERVER_PID_FILE, child.pid)

        time.sleep(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the local carousel editor server.")
    parser.add_argument("command", choices=["start", "stop", "status", "supervise"])
    args = parser.parse_args()

    if args.command == "start":
        return start()
    if args.command == "stop":
        return stop()
    if args.command == "status":
        return status()
    return supervise()


if __name__ == "__main__":
    raise SystemExit(main())
