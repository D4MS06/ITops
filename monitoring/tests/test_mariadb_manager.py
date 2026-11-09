import threading
from unittest.mock import patch

from monitoring.storage.mariadb_manager import CustomServiceAlreadyExistsError, MariaDBFileManager


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


def test_subject_module_grants_returns_active_roles_and_normalized_permissions():
    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params):
            assert "u.is_active = 1" in query
            assert params == ("alice", "module_builder")

        def fetchall(self):
            return [("creator", '["create", "update"]'), ("reader", '["read"]')]

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return _Cursor()

    manager = _make_manager_stub()
    manager._ensure_database = lambda: None
    manager._connect = lambda: _Connection()

    assert manager.subject_module_grants(subject="alice", module_code="module_builder") == {
        "creator": ["read", "create", "update"],
        "reader": ["read"],
    }


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


def test_create_only_service_insert_maps_concurrent_duplicate_to_conflict(monkeypatch):
    from types import SimpleNamespace
    import monitoring.storage.mariadb_manager as manager_module

    class _DuplicateKeyError(Exception):
        pass

    class _Cursor:
        insert_sql = ""

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, _params=None):
            if "INSERT INTO custom_services" in query:
                self.insert_sql = query
                raise _DuplicateKeyError(1062, "Duplicate entry")

        def fetchone(self):
            return None

    class _Connection:
        def __init__(self):
            self.cursor_instance = _Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return self.cursor_instance

    manager = _make_manager_stub()
    connection = _Connection()
    manager._ensure_database = lambda: None
    manager._connect = lambda: connection
    monkeypatch.setattr(manager_module, "pymysql", SimpleNamespace(err=SimpleNamespace(IntegrityError=_DuplicateKeyError)))

    try:
        manager.save_custom_service(
            code="new_module", label="Nouveau", is_active=True,
            credentials_enabled=False, child_enabled=False, child_label="Elements lies",
            sort_order=100, fields=[], owner_subject="alice", create_only=True,
        )
        assert False, "expected duplicate-key conflict"
    except CustomServiceAlreadyExistsError:
        pass

    assert "ON DUPLICATE KEY UPDATE" not in connection.cursor_instance.insert_sql
