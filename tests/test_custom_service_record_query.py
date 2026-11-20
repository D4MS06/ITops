from __future__ import annotations

from monitoring.storage.mariadb_manager import MariaDBFileManager
import pytest


class _Cursor:
    def __init__(self, conn: "_Connection") -> None:
        self.conn = conn
        self._result = []

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params=None) -> None:
        normalized = " ".join(str(sql or "").split())
        self.conn.calls.append((normalized, list(params or [])))
        if normalized.startswith("SELECT COUNT(*)"):
            self._result = [(2,)]
            return
        if "SELECT r.id, r.service_code" in normalized:
            self._result = [
                ("rec-1", "apps", '{"name": "Portail"}', "2026-01-01 10:00:00", "2026-01-02 10:00:00", "Portail"),
                ("rec-2", "apps", '{"name": "Intranet"}', "2026-01-03 10:00:00", "2026-01-04 10:00:00", "Intranet"),
            ]
            return
        if "FROM custom_service_children" in normalized:
            self._result = [(7, "rec-1", "Child A", "child-a", 10)]
            return
        self._result = []

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return list(self._result)


class _Connection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[object]]] = []

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self) -> _Cursor:
        return _Cursor(self)


def test_query_custom_service_record_index_returns_page_with_children() -> None:
    manager = object.__new__(MariaDBFileManager)
    conn = _Connection()
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    page = manager.query_custom_service_record_index(
        service_code="Apps",
        search="Portail",
        limit=25,
        offset=50,
        sort="updated_at",
        direction="desc",
    )

    assert page["total"] == 2
    assert page["limit"] == 25
    assert page["offset"] == 50
    assert [item["id"] for item in page["items"]] == ["rec-1", "rec-2"]
    assert page["items"][0]["values"] == {"name": "Portail"}
    assert page["items"][0]["children"] == [{"id": "7", "name": "Child A", "code": "child-a", "sort_order": 10}]
    select_call = next(sql for sql, _params in conn.calls if "ORDER BY r.updated_at DESC" in sql)
    assert "LIMIT %s OFFSET %s" in select_call
    assert conn.calls[0][1] == ["apps", "%Portail%"]
    assert conn.calls[1][1] == ["apps", "%Portail%", 25, 50]


def test_numeric_field_sort_is_applied_before_pagination_and_rejects_invalid_key() -> None:
    manager = object.__new__(MariaDBFileManager)
    conn = _Connection()
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn
    manager.query_custom_service_record_index(service_code="apps", sort="field:montant", direction="desc", limit=10, offset=20)
    sql, params = conn.calls[1]
    assert "JSON_EXTRACT(r.payload_json, '$.\"montant\"')" in sql
    assert "AS DECIMAL(65,20)) END DESC" in sql
    assert "ORDER BY" in sql and "LIMIT %s OFFSET %s" in sql
    assert params == ["apps", 10, 20]
    with pytest.raises(ValueError, match="Champ de tri invalide"):
        manager.query_custom_service_record_index(service_code="apps", sort="field:montant' OR 1=1")
