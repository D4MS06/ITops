import threading

import pytest

from monitoring.api.schemas import CustomServiceRelationUpsertRequest
from monitoring.api.app import (
    _custom_service_record_response_payload,
    _custom_service_record_version_token,
    _extract_custom_service_credential_values,
)
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
        self.lastrowid = self.conn.lastrowid

    def executemany(self, sql, params_seq=None):
        normalized = " ".join(str(sql).split())
        params_list = list(params_seq or [])
        self.conn.statements.append(normalized)
        self.conn.params.append(params_list)
        self.rowcount = len(params_list)
        self.lastrowid = self.conn.lastrowid

    def fetchone(self):
        return (self.conn.fetchone_value,)

    def fetchall(self):
        if self.conn.fetchall_values:
            return self.conn.fetchall_values.pop(0)
        return []


class _FakeConn:
    def __init__(self, *, existing_columns=None, existing_indexes=None, fetchall_values=None):
        self.existing_columns = set(existing_columns or [])
        self.existing_indexes = set(existing_indexes or [])
        self.statements = []
        self.params = []
        self.fetchone_value = 0
        self.fetchall_values = list(fetchall_values or [])
        self.lastrowid = 1000

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


def test_email_system_service_uses_stable_portal_module_code():
    assert MariaDBFileManager._custom_service_module_code("emails") == "service_emails"
    assert MariaDBFileManager._custom_service_module_code("Emails") == "service_emails"


def test_email_account_type_does_not_treat_service_name_as_technical():
    assert MariaDBFileManager._infer_email_account_type(
        address="services-techniques@example.local",
        payload={},
    ) == "generique"


def test_email_record_version_token_ignores_computed_display_values():
    base = {
        "id": "email_1",
        "service_code": "emails",
        "values": {"address": "service@example.local", "type_compte": "generique"},
        "children": [],
        "created_at": "2026-07-28 10:00:00",
        "updated_at": "2026-07-28 10:00:00",
    }
    enriched = {
        **base,
        "values": {
            **base["values"],
            "agents_lies": "Agent Test",
            "services_deduits": "Service Test",
        },
    }

    assert _custom_service_record_version_token(base) == _custom_service_record_version_token(enriched)


def test_custom_service_record_response_masks_credential_password():
    row = {
        "id": "email_1",
        "service_code": "emails",
        "values": {
            "address": "service@example.local",
            "device_password": "secret-password",
        },
        "children": [],
        "created_at": "2026-07-29 10:00:00",
        "updated_at": "2026-07-29 10:00:00",
    }

    payload = _custom_service_record_response_payload(row, credentials_enabled=True)

    assert payload["has_credential_password"] is True
    assert payload["credential_password_masked"] == "********"
    assert "device_password" not in payload["values"]
    assert "password" not in payload["values"]
    assert payload["version_token"]


def test_blank_custom_service_record_password_is_omitted_to_preserve_existing_secret():
    values = _extract_custom_service_credential_values(
        {"device_login": "account", "device_password": ""},
        enabled=True,
    )

    assert values == {"device_login": "account"}


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


def test_directory_schema_creates_system_tables():
    conn = _FakeConn()

    MariaDBBootstrapper.ensure_directory_schema(conn, "itops_test")

    assert any("CREATE TABLE IF NOT EXISTS organization_units" in statement for statement in conn.statements)
    assert any("CREATE TABLE IF NOT EXISTS directory_users" in statement for statement in conn.statements)


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


def test_save_custom_service_rejects_reserved_system_entity_code():
    manager = _make_manager_stub()

    with pytest.raises(ValueError, match="reserve"):
        manager.save_custom_service(
            code="utilisateurs",
            label="Utilisateurs",
            is_active=True,
            credentials_enabled=False,
            child_enabled=False,
            child_label="Elements lies",
            sort_order=100,
            fields=[],
        )


def test_list_custom_services_filters_reserved_system_entity_rows():
    manager = _make_manager_stub()
    conn = _FakeConn(
        fetchall_values=[
            [
                (
                    "utilisateurs",
                    "Utilisateurs",
                    0,
                    0,
                    0,
                    "",
                    100,
                    "",
                    "",
                    "",
                    "",
                    1,
                    1,
                    None,
                    None,
                )
            ],
            [],
        ]
    )
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    rows = manager.list_custom_services()

    assert rows == []


def test_list_custom_service_relations_keeps_system_entity_targets():
    manager = _make_manager_stub()
    conn = _FakeConn(
        fetchall_values=[
            [
                (
                    1,
                    "copieurs",
                    "sites",
                    "est lie a",
                    "many_to_one",
                    "out",
                    "Site",
                    0,
                    1,
                    10,
                    20,
                    300,
                    400,
                    10,
                    "2026-01-01",
                    "2026-01-02",
                ),
                (
                    2,
                    "copieurs",
                    "utilisateurs",
                    "est lie a",
                    "many_to_one",
                    "out",
                    "Utilisateur",
                    0,
                    1,
                    10,
                    20,
                    300,
                    400,
                    20,
                    "2026-01-01",
                    "2026-01-02",
                ),
            ],
        ],
    )
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    rows = manager.list_custom_service_relations(service_code="copieurs")

    assert [row["id"] for row in rows] == [1, 2]
    assert rows[1]["target_service_code"] == "utilisateurs"


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


@pytest.mark.parametrize("code", ["agent", "agents", "ou", "ous", "utilisateurs", "services"])
def test_relation_system_aliases_are_reserved_service_codes(code):
    assert MariaDBFileManager.is_reserved_system_entity_code(code) is True


def test_email_service_code_remains_available_as_dynamic_module():
    assert MariaDBFileManager.is_reserved_system_entity_code("emails") is False
    assert MariaDBFileManager.is_system_custom_service_code("emails") is True


def test_list_custom_services_marks_email_module_as_system():
    manager = _make_manager_stub()
    conn = _FakeConn(
        fetchall_values=[
            [
                (
                    "emails",
                    "Emails",
                    1,
                    1,
                    0,
                    "Agents lies",
                    47,
                    "mail",
                    "",
                    "",
                    "",
                    1,
                    1,
                    None,
                    None,
                )
            ],
            [],
        ]
    )
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    rows = manager.list_custom_services()

    assert rows[0]["code"] == "emails"
    assert rows[0]["is_system"] is True
    assert rows[0]["credentials_enabled"] is True


def test_system_email_module_cannot_be_deleted_or_have_source_relations_replaced():
    manager = _make_manager_stub()
    conn = _FakeConn()
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    with pytest.raises(ValueError, match="systeme"):
        manager.delete_custom_service(code="emails")

    with pytest.raises(ValueError, match="systeme"):
        manager.replace_custom_service_relations(service_code="emails", relations=[])

    with pytest.raises(ValueError, match="systeme"):
        manager.delete_custom_service_relation(source_service_code="emails", target_service_code="utilisateurs")


def test_business_ou_dns_skip_technical_containers_before_linking_agent_to_service():
    dn = "CN=Agent X,OU=Ordinateur,OU=Dev Durable,OU=CTM,OU=MairieVL,DC=mairieVL,DC=local"

    assert MariaDBFileManager._directory_business_ou_dns(dn)[0] == "OU=Dev Durable,OU=CTM,OU=MairieVL,DC=mairieVL,DC=local"


def test_active_directory_email_extraction_reads_mail_proxy_and_other_mailbox():
    rows = MariaDBFileManager._payload_email_addresses(
        {
            "mail": "agent@example.fr",
            "proxyAddresses": ["SMTP:agent@example.fr", "smtp:alias@example.fr"],
            "otherMailbox": ["shared@example.fr"],
        }
    )

    assert [row["address"] for row in rows] == [
        "agent@example.fr",
        "alias@example.fr",
        "shared@example.fr",
    ]


def test_active_directory_email_type_requires_identity_shape_for_nominative():
    payload = {"givenName": "Jean", "sn": "Dupont"}

    assert MariaDBFileManager._infer_email_account_type(address="jean.dupont@example.fr", payload=payload) == "nominatif"
    assert MariaDBFileManager._infer_email_account_type(address="j.dupont@example.fr", payload=payload) == "nominatif"
    assert MariaDBFileManager._infer_email_account_type(address="urbanisme@example.fr", payload=payload) == "generique"
    assert MariaDBFileManager._infer_email_account_type(address="scanner@example.fr", payload=payload) == "technique"
    assert MariaDBFileManager._infer_email_account_type(address="elus@example.fr", payload=payload, kind="proxy") == "partage"


def test_seed_system_relation_rows_creates_agents_services_many_to_many_relation():
    conn = _FakeConn()

    MariaDBBootstrapper.ensure_system_relation_rows(conn)

    assert any("INSERT INTO custom_service_relations" in statement for statement in conn.statements)
    assert ("utilisateurs", "services", "appartient a", "Agents / Services", 120, 180, 520, 180, 1) in conn.params
    assert ("utilisateurs", "emails", "possede", "Agents / Emails", 120, 360, 520, 360, 2) in conn.params


def test_seed_email_service_rows_creates_credentials_enabled_dynamic_service():
    conn = _FakeConn()

    MariaDBBootstrapper.ensure_email_service_rows(conn)

    assert any("INSERT INTO custom_services" in statement and "'emails', 'Emails'" in statement for statement in conn.statements)
    assert any("credentials_enabled=1" in statement for statement in conn.statements)
    field_params = next(params for statement, params in zip(conn.statements, conn.params) if statement.startswith("INSERT INTO custom_service_fields"))
    assert field_params[0][:3] == ("address", "Adresse email", "text")
    assert field_params[0][3] == 1
    assert "account_login" not in {row[0] for row in field_params}


def test_seed_system_relation_rows_updates_existing_agents_services_relation_without_duplicate():
    conn = _FakeConn(fetchall_values=[[(42,), (43,)], [(50,)]])

    MariaDBBootstrapper.ensure_system_relation_rows(conn)

    assert any("UPDATE custom_service_relations SET verb = %s, cardinality = 'many_to_many'" in statement for statement in conn.statements)
    assert any("INSERT IGNORE INTO custom_service_relation_links" in statement for statement in conn.statements)
    assert not any(statement.startswith("INSERT INTO custom_service_relations(") for statement in conn.statements)


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


def test_replace_custom_service_relations_accepts_system_entity_target():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"code": code} if code == "copieurs" else None
    conn = _FakeConn(fetchall_values=[[], []])
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    manager.replace_custom_service_relations(
        service_code="copieurs",
        relations=[{"target_service_code": "agents", "cardinality": "many_to_one", "direction": "out"}],
    )

    insert_params = next(
        params
        for statement, params in zip(conn.statements, conn.params)
        if statement.startswith("INSERT INTO custom_service_relations")
    )
    assert insert_params[1] == "utilisateurs"


def test_replace_custom_service_relations_updates_existing_relation_without_delete():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"code": code}
    conn = _FakeConn(
        fetchall_values=[
            [(42, "copieurs", "sites", "many_to_one", "out")],
            [(
                42,
                "copieurs",
                "sites",
                "est installe dans",
                "many_to_one",
                "out",
                "Service",
                0,
                1,
                10,
                20,
                300,
                400,
                10,
                "2026-01-01",
                "2026-01-02",
            )],
        ],
    )
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    rows = manager.replace_custom_service_relations(
        service_code="copieurs",
        relations=[{
            "target_service_code": "sites",
            "cardinality": "many_to_one",
            "direction": "out",
            "verb": "est installe dans",
            "display_label": "Service",
        }],
    )

    assert rows[0]["id"] == 42
    assert any(statement.startswith("UPDATE custom_service_relations") for statement in conn.statements)
    assert not any(statement == "DELETE FROM custom_service_relations WHERE source_service_code = %s" for statement in conn.statements)
    assert not any("DELETE FROM custom_service_relations WHERE source_service_code = %s AND id IN" in statement for statement in conn.statements)


def test_replace_custom_service_relations_refuses_to_remove_linked_relation():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"code": code}
    conn = _FakeConn(
        fetchall_values=[
            [(42, "copieurs", "sites", "many_to_one", "out")],
            [(42, 3)],
        ],
    )
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    with pytest.raises(ValueError, match="contiennent encore des liens"):
        manager.replace_custom_service_relations(
            service_code="copieurs",
            relations=[],
        )

    assert not any("DELETE FROM custom_service_relations WHERE source_service_code = %s AND id IN" in statement for statement in conn.statements)
