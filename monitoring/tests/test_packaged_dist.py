from __future__ import annotations

import os
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
)
EXPECTED_ICON_PATHS = (
    DIST_ROOT / "_internal" / "monitoring" / "assets" / "app.ico",
    DIST_ROOT / "_internal" / "monitoring" / "ui" / "assets" / "app.ico",
)


def _require_windows_dist() -> None:
    if not sys.platform.startswith("win"):
        pytest.skip("Validation du build Windows uniquement.")
    if not DIST_ROOT.exists():
        pytest.skip("Dossier dist absent. Lance d'abord scripts/build_windows.ps1.")


def _require_mariadb_runtime() -> None:
    try:
        import pymysql
    except ModuleNotFoundError:
        pytest.skip("PyMySQL absent: runtime MariaDB non disponible sur cette machine de test.")
    host = str(os.environ.get("NMP_MARIADB_HOST") or "127.0.0.1").strip()
    port = int(str(os.environ.get("NMP_MARIADB_PORT") or "3306").strip() or 3306)
    user = str(os.environ.get("NMP_MARIADB_USER") or "root").strip()
    password = str(os.environ.get("NMP_MARIADB_PASSWORD") or "")
    database = str(os.environ.get("NMP_MARIADB_DATABASE") or "network_monitoring").strip()
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=2,
            read_timeout=2,
            write_timeout=2,
            autocommit=True,
        )
    except Exception as exc:
        pytest.skip(f"Serveur MariaDB indisponible pour le smoke test package: {exc}")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
    finally:
        conn.close()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def test_packaged_dist_contains_expected_files():
    _require_windows_dist()
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in EXPECTED_DIST_FILES if not path.is_file()]
    if not any(path.is_file() for path in EXPECTED_ICON_PATHS):
        missing.append(str(EXPECTED_ICON_PATHS[0].relative_to(PROJECT_ROOT)))
    assert missing == []


def test_packaged_dist_smoke_starts_web_server():
    _require_windows_dist()
    _require_mariadb_runtime()
    if not DIST_EXE.is_file():
        pytest.skip("Executable package absent.")

    port = _find_free_port()
    try:
        process = subprocess.Popen(
            [str(DIST_EXE), "--mode", "server", "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(DIST_ROOT),
        )
    except OSError as exc:
        if getattr(exc, "winerror", None) == 740:
            pytest.skip("Le binaire package requiert une elevation Windows sur cette machine.")
        raise

    try:
        deadline = time.time() + 20.0
        health_url = f"http://127.0.0.1:{port}/health"
        while time.time() < deadline:
            if process.poll() is not None:
                raise AssertionError(f"Le serveur package s'est arrete avec le code {process.returncode}.")
            try:
                with urlopen(health_url, timeout=1.0) as response:
                    assert int(getattr(response, "status", 500)) == 200
                    return
            except Exception:
                time.sleep(0.25)
        raise AssertionError(f"Le serveur package ne repond pas sur {health_url}.")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)
