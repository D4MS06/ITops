import threading
from unittest.mock import patch

from monitoring.storage.mariadb_manager import MariaDBFileManager


def _make_manager_stub() -> MariaDBFileManager:
    manager = object.__new__(MariaDBFileManager)
    manager._bootstrap_lock = threading.Lock()
    manager._bootstrap_completed = False
    return manager


def test_mariadb_ensure_database_bootstraps_once():
    manager = _make_manager_stub()
    calls: list[int] = []

    def _fake_bootstrap(_manager):
        calls.append(1)

    with patch("monitoring.storage.mariadb_manager.MariaDBBootstrapper.ensure_database", side_effect=_fake_bootstrap):
        manager._ensure_database()
        manager._ensure_database()

    assert calls == [1]
    assert manager._bootstrap_completed is True


def test_mariadb_ensure_database_retries_if_first_bootstrap_fails():
    manager = _make_manager_stub()
    state = {"count": 0}

    def _fake_bootstrap(_manager):
        state["count"] += 1
        if state["count"] == 1:
            raise RuntimeError("boom")

    with patch("monitoring.storage.mariadb_manager.MariaDBBootstrapper.ensure_database", side_effect=_fake_bootstrap):
        try:
            manager._ensure_database()
            assert False, "expected RuntimeError"
        except RuntimeError:
            pass
        manager._ensure_database()

    assert state["count"] == 2
    assert manager._bootstrap_completed is True
