from __future__ import annotations

from monitoring.storage.mariadb_bootstrap import MariaDBBootstrapper


class _Cursor:
    def __init__(self, conn: "_Connection") -> None:
        self.conn = conn
        self._result = (0,)

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params=None) -> None:
        normalized_sql = " ".join(str(sql or "").split())
        self.conn.statements.append(normalized_sql)
        if "INFORMATION_SCHEMA.COLUMNS" in normalized_sql:
            table_name = str((params or ("", "", ""))[1])
            column_name = str((params or ("", "", ""))[2])
            self._result = (1 if column_name in self.conn.columns.get(table_name, set()) else 0,)
            return
        if normalized_sql.startswith("ALTER TABLE"):
            parts = normalized_sql.split()
            table_name = parts[2]
            column_name = parts[parts.index("COLUMN") + 1]
            self.conn.columns.setdefault(table_name, set()).add(column_name)

    def fetchone(self):
        return self._result


class _Connection:
    def __init__(self) -> None:
        self.columns: dict[str, set[str]] = {
            "custom_services": {"code", "label", "is_active", "credentials_enabled"},
            "custom_service_fields": {
                "id",
                "service_code",
                "field_key",
                "label",
                "field_kind",
                "required",
                "options",
                "default_value",
                "sort_order",
                "list_source_kind",
                "shared_list_code",
            },
        }
        self.statements: list[str] = []

    def cursor(self) -> _Cursor:
        return _Cursor(self)


def test_custom_service_schema_columns_are_idempotent() -> None:
    conn = _Connection()

    MariaDBBootstrapper.ensure_custom_service_columns(conn, "network_monitoring")
    MariaDBBootstrapper.ensure_custom_service_field_columns(conn, "network_monitoring")
    MariaDBBootstrapper.ensure_custom_service_history_schema(conn, "network_monitoring")
    first_alters = [statement for statement in conn.statements if statement.startswith("ALTER TABLE")]
    MariaDBBootstrapper.ensure_custom_service_columns(conn, "network_monitoring")
    MariaDBBootstrapper.ensure_custom_service_field_columns(conn, "network_monitoring")
    MariaDBBootstrapper.ensure_custom_service_history_schema(conn, "network_monitoring")
    second_alters = [statement for statement in conn.statements if statement.startswith("ALTER TABLE")][len(first_alters):]

    assert "icon" in conn.columns["custom_services"]
    assert "updated_at" in conn.columns["custom_services"]
    assert "show_in_list" in conn.columns["custom_service_fields"]
    assert "max_value" in conn.columns["custom_service_fields"]
    assert "track_history" in conn.columns["custom_service_fields"]
    assert any("CREATE TABLE IF NOT EXISTS custom_service_record_history" in statement for statement in conn.statements)
    assert first_alters
    assert second_alters == []


def test_custom_service_record_index_table_uses_idempotent_create() -> None:
    source = MariaDBBootstrapper.ensure_database.__code__.co_consts
    create_statements = [item for item in source if isinstance(item, str) and "custom_service_record_index" in item]

    assert create_statements
    assert "CREATE TABLE IF NOT EXISTS custom_service_record_index" in create_statements[0]
    assert "FULLTEXT KEY ft_csri_search_blob" in create_statements[0]
