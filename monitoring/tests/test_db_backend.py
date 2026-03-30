from __future__ import annotations

import importlib.util

from monitoring.storage.db_backend import resolve_storage_backend
from monitoring.storage.sqlite_manager import SQLiteFileManager


def test_resolve_storage_backend_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("NMP_DB_BACKEND", raising=False)
    monkeypatch.delenv("NMP_STORAGE_BACKEND", raising=False)
    assert resolve_storage_backend() == "sqlite"


def test_resolve_storage_backend_accepts_mariadb(monkeypatch):
    monkeypatch.setenv("NMP_DB_BACKEND", "mariadb")
    assert resolve_storage_backend() == "mariadb"


def test_sqlite_file_manager_dispatches_to_mariadb(monkeypatch):
    monkeypatch.setenv("NMP_DB_BACKEND", "mariadb")
    if importlib.util.find_spec("pymysql") is None:
        try:
            SQLiteFileManager()
        except RuntimeError as exc:
            assert "PyMySQL" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Une RuntimeError etait attendue sans PyMySQL.")
        return

    from monitoring.storage.mariadb_manager import MariaDBFileManager

    manager = SQLiteFileManager()
    assert isinstance(manager, MariaDBFileManager)


def test_sqlite_file_manager_stays_sqlite_by_default(monkeypatch):
    monkeypatch.delenv("NMP_DB_BACKEND", raising=False)
    monkeypatch.delenv("NMP_STORAGE_BACKEND", raising=False)
    manager = SQLiteFileManager()
    assert isinstance(manager, SQLiteFileManager)
