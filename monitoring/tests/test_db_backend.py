from __future__ import annotations

from monitoring.storage.db_backend import resolve_storage_backend
from monitoring.storage.sqlite_manager import SQLiteFileManager


def test_resolve_storage_backend_defaults_to_mariadb(monkeypatch):
    monkeypatch.delenv("NMP_DB_BACKEND", raising=False)
    monkeypatch.delenv("NMP_STORAGE_BACKEND", raising=False)
    assert resolve_storage_backend() == "mariadb"


def test_resolve_storage_backend_accepts_mariadb(monkeypatch):
    monkeypatch.setenv("NMP_DB_BACKEND", "mariadb")
    assert resolve_storage_backend() == "mariadb"


def test_resolve_storage_backend_rejects_sqlite(monkeypatch):
    monkeypatch.setenv("NMP_DB_BACKEND", "sqlite")
    try:
        resolve_storage_backend()
    except RuntimeError as exc:
        assert "retire du runtime" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Une RuntimeError etait attendue.")


def test_resolve_storage_backend_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("NMP_DB_BACKEND", "postgres")
    try:
        resolve_storage_backend()
    except RuntimeError as exc:
        assert "non supporte" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Une RuntimeError etait attendue.")


def test_sqlite_file_manager_legacy_class_still_importable():
    manager = SQLiteFileManager.__new__(SQLiteFileManager)
    assert isinstance(manager, SQLiteFileManager)
