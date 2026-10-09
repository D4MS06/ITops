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


def test_replace_sync_source_cache_entries_generates_stable_hash_ids():
    class _Cursor:
        def __init__(self):
            self.executions = []

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def execute(self, query, params=None):
            self.executions.append((" ".join(str(query).split()), params))

    class _Connection:
        def __init__(self):
            self.cursor_instance = _Cursor()
            self.committed = False

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def cursor(self):
            return self.cursor_instance

        def commit(self):
            self.committed = True

    manager = _make_manager_stub()
    connection = _Connection()
    manager._ensure_database = lambda: None
    manager._connect = lambda: connection

    count = manager.replace_sync_source_cache_entries(
        target_kind="users",
        entries=[{"objectGUID": "agent-guid", "displayName": "Agent Test"}],
    )

    assert count == 1
    assert connection.committed is True
    insert = next(params for query, params in connection.cursor_instance.executions if query.startswith("INSERT INTO sync_source_cache_entries"))
    assert insert[0] == "6ed6d0fd529b36da877e9849506a7fff51c784d9"
