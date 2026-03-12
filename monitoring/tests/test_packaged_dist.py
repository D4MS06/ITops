from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIST_ROOT = PROJECT_ROOT / "dist" / "NetworkMonitoringProject"
DIST_EXE = DIST_ROOT / "NetworkMonitoringProject.exe"
EXPECTED_DIST_FILES = (
    DIST_EXE,
    DIST_ROOT / "_internal" / "monitoring" / "web" / "index.html",
    DIST_ROOT / "_internal" / "monitoring" / "web" / "app.js",
    DIST_ROOT / "_internal" / "monitoring" / "web" / "app.css",
    DIST_ROOT / "_internal" / "monitoring" / "ui" / "assets" / "app.ico",
)


def _require_windows_dist() -> None:
    if not sys.platform.startswith("win"):
        pytest.skip("Validation du build Windows uniquement.")
    if not DIST_ROOT.exists():
        pytest.skip("Dossier dist absent. Lance d'abord scripts/build_windows.ps1.")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def test_packaged_dist_contains_expected_files():
    _require_windows_dist()
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in EXPECTED_DIST_FILES if not path.is_file()]
    assert missing == []


def test_packaged_dist_smoke_starts_web_server():
    _require_windows_dist()
    if not DIST_EXE.is_file():
        pytest.skip("Executable packagé absent.")

    port = _find_free_port()
    process = subprocess.Popen(
        [str(DIST_EXE), "--mode", "server", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(DIST_ROOT),
    )
    try:
        deadline = time.time() + 20.0
        health_url = f"http://127.0.0.1:{port}/health"
        while time.time() < deadline:
            if process.poll() is not None:
                raise AssertionError(f"Le serveur packagé s'est arrêté avec le code {process.returncode}.")
            try:
                with urlopen(health_url, timeout=1.0) as response:
                    assert int(getattr(response, "status", 500)) == 200
                    return
            except Exception:
                time.sleep(0.25)
        raise AssertionError(f"Le serveur packagé ne répond pas sur {health_url}.")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)
