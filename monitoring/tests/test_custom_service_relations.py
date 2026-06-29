import threading

import pytest

from monitoring.api.schemas import CustomServiceRelationUpsertRequest
from monitoring.storage.mariadb_bootstrap import MariaDBBootstrapper
from monitoring.storage.mariadb_manager import MariaDBFileManager


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(str(sql).split())
        self.conn.statements.append(normalized)
        self.conn.params.append(params)
        if "INFORMATION_SCHEMA.COLUMNS" in str(sql):
            table_name = str((params or ["", ""])[1])
            column_name = str((params or ["", "", ""])[2])
            self.conn.fetchone_value = 1 if (table_name, column_name) in self.conn.existing_columns else 0
        elif "INFORMATION_SCHEMA.STATISTICS" in str(sql):
            table_name = str((params or ["", ""])[1])
            index_name = str((params or ["", "", ""])[2])
            self.conn.fetchone_value = 1 if (table_name, index_name) in self.conn.existing_indexes else 0
        else:
            self.conn.fetchone_value = 0
        self.rowcount = 1

    def fetchone(self):
        return (self.conn.fetchone_value,)


class _FakeConn:
    def __init__(self, *, existing_columns=None, existing_indexes=None):
        self.existing_columns = set(existing_columns or [])
        self.existing_indexes = set(existing_indexes or [])
        self.statements = []
        self.params = []
        self.fetchone_value = 0

    def cursor(self):
        return _FakeCursor(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def commit(self):
        pass


def _make_manager_stub() -> MariaDBFileManager:
    manager = object.__new__(MariaDBFileManager)
    manager._bootstrap_lock = threading.Lock()
    manager._bootstrap_completed = False
    manager.db_name = "itops_test"
    return manager


def test_custom_service_relation_schema_is_idempotent_when_columns_and_indexes_exist():
    existing_columns = {
        ("custom_service_relations", column)
        for column in (
            "verb",
            "cardinality",
            "direction",
            "display_label",
            "required",
            "is_active",
            "source_x",
            "source_y",
            "target_x",
            "target_y",
            "sort_order",
            "created_at",
            "updated_at",
        )
    }
    existing_indexes = {
        ("custom_service_relations", "idx_custom_service_relations_source"),
        ("custom_service_relations", "idx_custom_service_relations_target"),
    }
    conn = _FakeConn(existing_columns=existing_columns, existing_indexes=existing_indexes)

    MariaDBBootstrapper.ensure_custom_service_relation_schema(conn, "itops_test")

    assert any("CREATE TABLE IF NOT EXISTS custom_service_relations" in statement for statement in conn.statements)
    assert not [statement for statement in conn.statements if statement.startswith("ALTER TABLE custom_service_relations")]


def test_custom_service_relation_schema_backfills_missing_columns_and_indexes():
    conn = _FakeConn()

    MariaDBBootstrapper.ensure_custom_service_relation_schema(conn, "itops_test")

    alter_statements = [statement for statement in conn.statements if statement.startswith("ALTER TABLE custom_service_relations")]
    assert any("ADD COLUMN verb" in statement for statement in alter_statements)
    assert any("ADD COLUMN target_y" in statement for statement in alter_statements)
    assert any("ADD INDEX idx_custom_service_relations_source" in statement for statement in alter_statements)
    assert any("ADD INDEX idx_custom_service_relations_target" in statement for statement in alter_statements)


def test_custom_service_relation_link_schema_is_idempotent_when_indexes_exist():
    existing_indexes = {
        ("custom_service_relation_links", "idx_custom_service_relation_links_source"),
        ("custom_service_relation_links", "idx_custom_service_relation_links_target"),
    }
    conn = _FakeConn(existing_indexes=existing_indexes)

    MariaDBBootstrapper.ensure_custom_service_relation_link_schema(conn, "itops_test")

    assert any("CREATE TABLE IF NOT EXISTS custom_service_relation_links" in statement for statement in conn.statements)
    assert not [statement for statement in conn.statements if statement.startswith("ALTER TABLE custom_service_relation_links")]


def test_custom_service_relation_link_schema_backfills_missing_indexes():
    conn = _FakeConn()

    MariaDBBootstrapper.ensure_custom_service_relation_link_schema(conn, "itops_test")

    alter_statements = [statement for statement in conn.statements if statement.startswith("ALTER TABLE custom_service_relation_links")]
    assert any("ADD INDEX idx_custom_service_relation_links_source" in statement for statement in alter_statements)
    assert any("ADD INDEX idx_custom_service_relation_links_target" in statement for statement in alter_statements)


def test_custom_service_relation_payload_normalizes_canvas_aliases():
    manager = _make_manager_stub()

    relation = manager._normalize_custom_service_relation_payload(
        source_service_code="Copieurs",
        relation={
            "service_code": "Sites",
            "verb": "est localise sur",
            "relation_type": "one-many",
            "direction": "bad-value",
            "label": "Site",
            "x": "420.6",
            "y": "120",
        },
        sort_order=20,
    )

    assert relation["source_service_code"] == "copieurs"
    assert relation["target_service_code"] == "sites"
    assert relation["cardinality"] == "one_to_many"
    assert relation["direction"] == "out"
    assert relation["display_label"] == "Site"
    assert relation["target_x"] == 421
    assert relation["target_y"] == 120
    assert relation["sort_order"] == 20


def test_custom_service_relation_payload_rejects_self_relation():
    manager = _make_manager_stub()

    with pytest.raises(ValueError, match="meme service"):
        manager._normalize_custom_service_relation_payload(
            source_service_code="copieurs",
            relation={"target_service_code": "copieurs"},
        )


def test_custom_service_relation_request_accepts_legacy_service_code_alias():
    payload = CustomServiceRelationUpsertRequest(service_code="utilisateurs")

    assert payload.target_service_code == ""
    assert payload.service_code == "utilisateurs"


def test_custom_service_relation_payload_still_rejects_missing_target_after_normalization():
    manager = _make_manager_stub()

    with pytest.raises(ValueError, match="cible invalide"):
        manager._normalize_custom_service_relation_payload(
            source_service_code="copieurs",
            relation={},
        )


def test_delete_custom_service_relation_scopes_an_id_to_its_source_service():
    manager = _make_manager_stub()
    conn = _FakeConn()
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    deleted = manager.delete_custom_service_relation(
        relation_id=42,
        source_service_code="copieurs",
    )

    assert deleted == 1
    assert conn.params[-1] == (42, "copieurs")
    assert "WHERE id = %s AND source_service_code = %s" in conn.statements[-1]


def test_delete_custom_service_cleans_incoming_outgoing_relations_and_links():
    manager = _make_manager_stub()
    conn = _FakeConn()
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn
    manager._sync_custom_service_auth_modules = lambda _conn: None

    deleted = manager.delete_custom_service(code="copieurs")

    assert deleted == 1
    assert conn.params[:5] == [
        ("copieurs", "copieurs"),
        ("copieurs",),
        ("copieurs", "copieurs"),
        ("copieurs",),
        ("copieurs",),
    ]
    assert "custom_service_relation_links" in conn.statements[0]
    assert "custom_service_relations" in conn.statements[2]
    assert "DELETE FROM custom_service_records" in conn.statements[3]
    assert "DELETE FROM custom_services" in conn.statements[4]


@pytest.mark.parametrize(
    ("cardinality", "expected"),
    [
        ("many_to_one", (False, True)),
        ("reference", (False, True)),
        ("one_to_many", (True, False)),
        ("one_to_one", (False, False)),
        ("many_to_many", (True, True)),
    ],
)
def test_custom_service_relation_cardinality_limits(cardinality, expected):
    assert MariaDBFileManager._custom_service_relation_cardinality_limits(cardinality) == expected


def test_replace_custom_service_relations_rejects_duplicate_definitions_before_write():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"code": code}

    with pytest.raises(ValueError, match="doublon"):
        manager.replace_custom_service_relations(
            service_code="copieurs",
            relations=[
                {"target_service_code": "sites", "cardinality": "many_to_one", "direction": "out"},
                {"target_service_code": "sites", "cardinality": "reference", "direction": "out"},
            ],
        )
