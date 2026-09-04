import threading
from types import SimpleNamespace

import pytest

from monitoring.api.schemas import CustomServiceRecordDuplicateMergeRequest, CustomServiceRelationUpsertRequest
from monitoring.api.app import (
    _directory_agent_inherited_module_sections,
    _directory_record_primary_label,
    _directory_service_path_label,
    _directory_service_path_parts,
    _directory_shared_path_prefix_length,
    _is_additional_active_directory_profile,
    _active_directory_profile_uses_source,
    _refresh_active_directory_cache_for_target,
    _custom_service_record_response_payload,
    _custom_service_record_response,
    _custom_service_record_version_token,
    _migrate_legacy_custom_service_record_password,
    _store_custom_service_record_password,
    _strip_custom_service_credential_password,
    _extract_custom_service_credential_values,
    _group_custom_service_record_duplicates,
)
from monitoring.storage.mariadb_bootstrap import MariaDBBootstrapper
from monitoring.storage.mariadb_manager import MariaDBFileManager


def test_primary_active_directory_sync_excludes_secondary_profiles():
    primary_profile = {"options": {"source_ids": ["primary"]}}
    legacy_profile = {"options": {}}
    school_profile = {"options": {"source_ids": ["ecoles"]}}
    school_schema_profile = SimpleNamespace(options={"source_ids": ["ecoles"]})

    assert _active_directory_profile_uses_source(primary_profile, "primary")
    assert _active_directory_profile_uses_source(legacy_profile, "primary")
    assert not _active_directory_profile_uses_source(school_profile, "primary")
    assert _active_directory_profile_uses_source(school_profile, "ecoles")
    assert not _active_directory_profile_uses_source(school_schema_profile, "primary")
    assert _active_directory_profile_uses_source(school_schema_profile, "ecoles")


def test_only_one_explicit_additional_source_can_own_a_custom_ad_profile():
    additional_sources = {"ecoles", "mediatheque"}

    assert _is_additional_active_directory_profile({"options": {"source_ids": ["ecoles"]}}, additional_sources)
    assert not _is_additional_active_directory_profile({"options": {}}, additional_sources)
    assert not _is_additional_active_directory_profile({"options": {"source_ids": ["primary"]}}, additional_sources)
    assert not _is_additional_active_directory_profile({"options": {"source_ids": ["ecoles", "mediatheque"]}}, additional_sources)


def test_legacy_service_password_is_moved_out_of_record_payload(monkeypatch):
    stored_secrets = {}
    removed = []
    secrets = SimpleNamespace(
        get_password=lambda account: stored_secrets.get(account, ""),
        set_or_delete_password=lambda account, value: stored_secrets.pop(account, None) if not value else stored_secrets.__setitem__(account, value),
    )
    api = SimpleNamespace(logs=SimpleNamespace(
        remove_custom_service_record_credential_password=lambda **kwargs: removed.append(kwargs) or 1,
    ))
    monkeypatch.setattr("monitoring.api.app._secrets_store", lambda: secrets)

    values, password = _strip_custom_service_credential_password({"address": "support@example.test", "device_password": "secret"})
    assert values == {"address": "support@example.test"}
    assert password == "secret"

    migrated = _migrate_legacy_custom_service_record_password(
        api,
        {"id": "mail-1", "values": {"address": "support@example.test", "device_password": "secret"}},
        service_code="emails",
    )
    assert migrated["values"] == {"address": "support@example.test"}
    assert stored_secrets["__custom_service_credential__emails__mail-1"] == "secret"
    assert removed == [{"service_code": "emails", "record_id": "mail-1"}]


def test_primary_ad_refresh_preserves_secondary_cache_without_refreshing_it(monkeypatch):
    class _Logs:
        replaced_entries = []

        def list_sync_source_cache_entries(self, **_kwargs):
            return [
                {"payload": {"name": "Ancien agent principal"}},
                {"payload": {"__sync_source_id": "ecoles", "name": "Ecole"}},
            ]

        def list_sync_source_profiles(self, **_kwargs):
            return []

        def replace_sync_source_cache_entries(self, **kwargs):
            self.replaced_entries = list(kwargs["entries"])
            return len(self.replaced_entries)

    settings = SimpleNamespace(active_directory_base_dn="DC=principal,DC=local", active_directory_sources_json="[]")
    api = SimpleNamespace(settings_service=SimpleNamespace(get=lambda: settings), logs=_Logs())
    fetched_settings = []

    def fetch_entries(_engine, connection, **_kwargs):
        fetched_settings.append(connection)
        return [{"name": "Nouvel agent principal"}]

    monkeypatch.setattr("monitoring.api.app.ActiveDirectorySyncEngine.fetch_entries", fetch_entries)

    assert _refresh_active_directory_cache_for_target(api, "users") == 1
    assert fetched_settings == [settings]
    assert [entry["name"] for entry in api.logs.replaced_entries] == ["Nouvel agent principal", "Ecole"]


def test_directory_agent_inherited_modules_merge_service_and_direct_links():
    class _Logs:
        def list_custom_services(self):
            return [{
                "code": "assets",
                "label": "Materiels",
                "is_active": True,
                "treeview_config": '{"relationship_inheritance":{"enabled":true,"relation_id":"41"}}',
                "fields": [{"field_key": "name", "sort_order": 10}],
            }]

        def list_custom_service_records(self, *, service_code):
            assert service_code == "assets"
            return [
                {"id": "asset-service", "values": {"name": "Materiel Service"}},
                {"id": "asset-direct", "values": {"name": "Materiel Direct"}},
            ]

        def list_custom_service_relations(self, *, service_code):
            assert service_code == "assets"
            return [
                {"id": 41, "source_service_code": "assets", "target_service_code": "services", "is_active": True},
                {"id": 42, "source_service_code": "assets", "target_service_code": "utilisateurs", "is_active": True},
            ]

        def list_custom_service_relation_links_for_record_ids(self, *, service_code, record_ids, relation_id):
            assert service_code == "assets"
            assert record_ids == ["asset-service", "asset-direct"]
            if relation_id == 41:
                return {
                    "asset-service": [{"linked_record": {"id": "service-a"}}],
                    "asset-direct": [],
                }
            if relation_id == 42:
                return {
                    "asset-service": [],
                    "asset-direct": [{"linked_record": {"id": "agent-a"}}],
                }
            return {}

    rows = [{"id": "agent-a", "linked_service_ids": ["service-a"]}]
    _directory_agent_inherited_module_sections(type("Api", (), {"logs": _Logs()})(), rows)

    assert rows[0]["inherited_module_sections"] == [{
        "service_code": "assets",
        "label": "Materiels",
        "records": [
            {"id": "asset-service", "label": "Materiel Service"},
            {"id": "asset-direct", "label": "Materiel Direct"},
        ],
    }]


def test_directory_agent_inherited_modules_resolve_services_without_directory_projection():
    """Inheritance is a relation contract, not an optional directory display field."""
    class _Logs:
        def list_custom_services(self):
            return [{
                "code": "printers",
                "label": "Copieurs",
                "is_active": True,
                "treeview_config": '{"relationship_inheritance":{"enabled":true,"relation_id":"41"}}',
                "fields": [{"field_key": "name", "sort_order": 10}],
            }]

        def list_custom_service_records(self, *, service_code):
            assert service_code == "printers"
            return [{"id": "printer-1", "values": {"name": "Copieur accueil"}}]

        def list_custom_service_relations(self, *, service_code):
            if service_code == "utilisateurs":
                return [{"id": 3, "source_service_code": "utilisateurs", "target_service_code": "services", "is_active": True}]
            assert service_code == "printers"
            return [{"id": 41, "source_service_code": "printers", "target_service_code": "services", "is_active": True}]

        def list_custom_service_relation_links_for_record_ids(self, *, service_code, record_ids, relation_id):
            if service_code == "utilisateurs" and relation_id == 3:
                return {"agent-a": [{"linked_record": {"id": "service-a"}}]}
            if service_code == "printers" and relation_id == 41:
                return {"printer-1": [{"linked_record": {"id": "service-a"}}]}
            return {}

    rows = [{"id": "agent-a"}]
    _directory_agent_inherited_module_sections(type("Api", (), {"logs": _Logs()})(), rows)

    assert rows[0]["linked_service_ids"] == ["service-a"]
    assert rows[0]["inherited_module_sections"] == [{
        "service_code": "printers",
        "label": "Copieurs",
        "records": [{"id": "printer-1", "label": "Copieur accueil"}],
    }]


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
            self.conn.fetchone_value = self.conn.fetchone_values.pop(0) if self.conn.fetchone_values else 0
        self.rowcount = next(
            (count for prefix, count in self.conn.rowcounts.items() if normalized.startswith(prefix)),
            1,
        )
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
    def __init__(self, *, existing_columns=None, existing_indexes=None, fetchall_values=None, fetchone_values=None, rowcounts=None):
        self.existing_columns = set(existing_columns or [])
        self.existing_indexes = set(existing_indexes or [])
        self.statements = []
        self.params = []
        self.fetchone_value = 0
        self.fetchone_values = list(fetchone_values or [])
        self.fetchall_values = list(fetchall_values or [])
        self.rowcounts = dict(rowcounts or {})
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


def test_directory_agent_label_prefers_identity_over_email_address():
    assert _directory_record_primary_label({
        "service_code": "utilisateurs",
        "values": {
            "display_name": "Jeanne Martin",
            "mail": "jeanne.martin@example.local",
        },
    }) == "Jeanne Martin"


def test_directory_service_path_disambiguates_same_named_organizational_units():
    ctm_finance = _directory_service_path_parts("OU=Finance,OU=CTM,OU=MairieVL,DC=mairieVL,DC=local")
    finance = _directory_service_path_parts("OU=Finance,OU=MairieVL,DC=mairieVL,DC=local")

    prefix_length = _directory_shared_path_prefix_length([ctm_finance, finance])

    assert _directory_service_path_label(ctm_finance[prefix_length:]) == "CTM / Finance"
    assert _directory_service_path_label(finance[prefix_length:]) == "Finance"
    assert _directory_record_primary_label({
        "service_code": "services",
        "values": {"name": "Finance", "path_label": "CTM / Finance"},
    }) == "CTM / Finance"


def test_services_relation_entity_accepts_a_local_service_when_ad_has_no_matching_ou():
    manager = object.__new__(MariaDBFileManager)
    manager.get_sync_source_cache_entry_by_external_id = lambda **_kwargs: None
    manager._relation_manual_service_record = lambda *, record_id: {
        "id": record_id,
        "service_code": "services",
        "values": {"name": "Service local"},
    }

    record = manager._system_relation_record(service_code="services", record_id="service_local_1")

    assert record is not None
    assert record["values"]["name"] == "Service local"
    assert manager._system_relation_record(service_code="utilisateurs", record_id="agent_local_1") is None


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


def test_record_response_keeps_the_stored_record_version_when_vault_password_is_present():
    row = {
        "id": "copieur_cab",
        "service_code": "copieur",
        "values": {"adresse_ip": "192.168.10.105", "device_login": "Admin"},
        "children": [],
        "created_at": "2026-08-12 09:28:28",
        "updated_at": "2026-08-19 09:03:23",
    }

    decorated_row = {
        **row,
        "values": {**row["values"], "device_password": "stored-in-vault", "agents_lies": "Agent CAB"},
    }
    payload = _custom_service_record_response_payload(
        decorated_row,
        credentials_enabled=True,
        has_credential_password=True,
        version_source=row,
    )

    assert payload["has_credential_password"] is True
    assert "device_password" not in payload["values"]
    assert payload["version_token"] == _custom_service_record_version_token(row)


@pytest.mark.parametrize("service_code", ["copieur", "logiciels", "module_personnalise"])
def test_every_custom_service_response_uses_the_persisted_record_for_its_version_token(monkeypatch, service_code):
    row = {
        "id": f"{service_code}_1",
        "service_code": service_code,
        "values": {"nom": "Fiche", "adresse_ip": "192.168.10.105"},
        "children": [],
        "created_at": "2026-08-12 09:28:28",
        "updated_at": "2026-08-19 09:03:23",
    }
    monkeypatch.setattr("monitoring.api.app._custom_service_record_password", lambda *_args, **_kwargs: "secret-in-vault")

    response = _custom_service_record_response(
        SimpleNamespace(),
        row,
        service_code=service_code,
        credentials_enabled=True,
    )

    assert response["has_credential_password"] is True
    assert response["version_token"] == _custom_service_record_version_token(row)


def test_blank_custom_service_record_password_is_omitted_to_preserve_existing_secret():
    values = _extract_custom_service_credential_values(
        {"device_login": "account", "device_password": ""},
        enabled=True,
    )

    assert values == {"device_login": "account"}


def test_clearing_an_absent_custom_service_password_does_not_rewrite_vault(monkeypatch):
    calls = []
    secrets = SimpleNamespace(
        get_password=lambda _account: "",
        set_or_delete_password=lambda account, value: calls.append((account, value)),
    )
    monkeypatch.setattr("monitoring.api.app._secrets_store", lambda: secrets)

    _store_custom_service_record_password("emails", "mail-1", "")

    assert calls == []


def test_duplicate_merge_request_requires_a_field_keeper_and_duplicate():
    request = CustomServiceRecordDuplicateMergeRequest(
        field_key="address",
        keeper_record_id="mail-keep",
        duplicate_record_ids=["mail-duplicate"],
    )

    assert request.field_key == "address"
    assert request.keeper_record_id == "mail-keep"
    assert request.duplicate_record_ids == ["mail-duplicate"]


def test_duplicate_groups_are_normalized_sorted_and_skip_blank_identifiers():
    groups = _group_custom_service_record_duplicates([
        {"id": "local-b", "created_at": "2026-08-02", "values": {"address": "B@example.test"}},
        {"id": "local-a", "created_at": "2026-08-01", "values": {"address": " b@example.test "}},
        {"id": "empty", "values": {"address": ""}},
        {"id": "single", "values": {"address": "single@example.test"}},
    ], field_key="address")

    assert len(groups) == 1
    assert groups[0][0] == "b@example.test"
    assert [row["id"] for row in groups[0][1]] == ["local-a", "local-b"]


def test_reminder_tasks_schema_is_created_for_duplicate_merges():
    conn = _FakeConn()

    MariaDBBootstrapper.ensure_custom_service_reminder_tasks_schema(conn, "itops_test")

    assert any("CREATE TABLE IF NOT EXISTS custom_service_reminder_tasks" in statement for statement in conn.statements)


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
                "filter_candidates_by_shared_relation",
                "show_indirect_relations",
                "track_history",
                "record_display_mode",
                "assignment_resource_service_code",
                "unique_value_field_key",
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
            "filter_candidates_by_shared_relation": True,
            "unique_value_field_key": "Asset_Tag",
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
    assert relation["filter_candidates_by_shared_relation"] is True
    assert relation["unique_value_field_key"] == "asset_tag"
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
    payload = CustomServiceRelationUpsertRequest(
        service_code="utilisateurs",
        filter_candidates_by_shared_relation=True,
        unique_value_field_key="code",
    )

    assert payload.target_service_code == ""
    assert payload.service_code == "utilisateurs"
    assert payload.filter_candidates_by_shared_relation is True
    assert payload.unique_value_field_key == "code"


def test_custom_service_relation_payload_still_rejects_missing_target_after_normalization():
    manager = _make_manager_stub()

    with pytest.raises(ValueError, match="cible invalide"):
        manager._normalize_custom_service_relation_payload(
            source_service_code="copieurs",
            relation={},
        )


def test_filtered_relation_candidate_uses_shared_related_record_generically():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {}
    relations_by_service = {
        "allocations": [
            {"id": 10, "source_service_code": "allocations", "target_service_code": "membres", "is_active": True},
            {"id": 11, "source_service_code": "allocations", "target_service_code": "equipements", "is_active": True},
        ],
        "membres": [
            {"id": 12, "source_service_code": "membres", "target_service_code": "equipements", "is_active": True},
        ],
    }
    linked_records = {
        ("allocations", "allocation_1", 11): [{"linked_record": {"id": "equipment_1"}}],
        ("membres", "agent_ok", 12): [{"linked_record": {"id": "equipment_1"}}],
        ("membres", "agent_other", 12): [{"linked_record": {"id": "equipment_2"}}],
    }
    manager.list_custom_service_relations = lambda *, service_code="": relations_by_service.get(service_code, [])
    manager.list_custom_service_record_relation_links = lambda *, service_code, record_id, relation_id: linked_records.get(
        (service_code, record_id, relation_id),
        [],
    )
    relation = {
        "id": 10,
        "source_service_code": "allocations",
        "target_service_code": "membres",
        "filter_candidates_by_shared_relation": True,
    }

    manager._validate_relation_shared_candidate(
        relation=relation,
        source_record_id="allocation_1",
        target_record_id="agent_ok",
    )

    with pytest.raises(ValueError, match="compatible"):
        manager._validate_relation_shared_candidate(
            relation=relation,
            source_record_id="allocation_1",
            target_record_id="agent_other",
        )


def test_filtered_relation_candidate_accepts_agent_inherited_from_service():
    manager = _make_manager_stub()
    manager.get_sync_source_cache_entry_by_external_id = lambda **_kwargs: None
    relations_by_service = {
        "codes": [
            {"id": 10, "source_service_code": "codes", "target_service_code": "utilisateurs", "is_active": True},
            {"id": 11, "source_service_code": "codes", "target_service_code": "copieurs", "is_active": True},
        ],
        "utilisateurs": [
            {"id": 12, "source_service_code": "utilisateurs", "target_service_code": "copieurs", "is_active": True},
            {"id": 30, "source_service_code": "utilisateurs", "target_service_code": "services", "is_active": True},
        ],
        "copieurs": [
            {"id": 20, "source_service_code": "copieurs", "target_service_code": "services", "is_active": True},
            {"id": 11, "source_service_code": "codes", "target_service_code": "copieurs", "is_active": True},
            {"id": 12, "source_service_code": "utilisateurs", "target_service_code": "copieurs", "is_active": True},
        ],
        "services": [
            {"id": 20, "source_service_code": "copieurs", "target_service_code": "services", "is_active": True},
            {"id": 30, "source_service_code": "utilisateurs", "target_service_code": "services", "is_active": True},
        ],
    }
    linked_records = {
        ("codes", "code_1", 11): [{"linked_record": {"id": "copier_1"}}],
        ("copieurs", "copier_1", 20): [{"linked_record": {"id": "service_1"}}],
        ("services", "service_1", 30): [{"linked_record": {"id": "agent_inherited", "values": {"status": "Actif"}}}],
        ("utilisateurs", "agent_direct", 30): [{"linked_record": {"id": "service_1"}}],
    }
    manager.get_custom_service = lambda *, code: {
        "code": code,
        "treeview_config": '{"relationship_inheritance":{"enabled":true,"relation_id":"20"}}' if code == "copieurs" else "",
    }
    manager.list_custom_service_relations = lambda *, service_code="": relations_by_service.get(service_code, [])
    manager.list_custom_service_record_relation_links = lambda *, service_code, record_id, relation_id: linked_records.get(
        (service_code, record_id, relation_id),
        [],
    )
    relation = {
        "id": 10,
        "source_service_code": "codes",
        "target_service_code": "utilisateurs",
        "filter_candidates_by_shared_relation": True,
    }

    manager._validate_relation_shared_candidate(
        relation=relation,
        source_record_id="code_1",
        target_record_id="agent_inherited",
    )

    manager._validate_relation_shared_candidate(
        relation=relation,
        source_record_id="code_1",
        target_record_id="agent_direct",
    )

    with pytest.raises(ValueError, match="compatible"):
        manager._validate_relation_shared_candidate(
            relation=relation,
            source_record_id="code_1",
            target_record_id="agent_other",
        )


def test_filtered_relation_candidate_accepts_legacy_agent_alias_for_inheritance():
    manager = _make_manager_stub()
    manager.get_sync_source_cache_entry_by_external_id = lambda **_kwargs: None
    manager._inherited_service_record_ids = lambda *, service_code, record_id: set()
    manager._inherited_agent_ids_for_record = lambda *, service_code, record_id: {"agent_inherited"} if (service_code, record_id) == ("copieurs", "copier_1") else set()
    manager.list_custom_service_relations = lambda *, service_code="": {
        "codes": [
            {"id": 10, "source_service_code": "codes", "target_service_code": "agents", "is_active": True},
            {"id": 11, "source_service_code": "codes", "target_service_code": "copieurs", "is_active": True},
        ],
        "utilisateurs": [],
    }.get(service_code, [])
    manager.list_custom_service_record_relation_links = lambda *, service_code, record_id, relation_id: (
        [{"linked_record": {"id": "copier_1"}}]
        if (service_code, record_id, relation_id) == ("codes", "code_1", 11)
        else []
    )

    manager._validate_relation_shared_candidate(
        relation={
            "id": 10,
            "source_service_code": "codes",
            "target_service_code": "agents",
            "filter_candidates_by_shared_relation": True,
        },
        source_record_id="code_1",
        target_record_id="agent_inherited",
    )


def test_relation_unique_value_is_scoped_to_the_linked_target():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {
        "code": code,
        "label": {"codes": "Codes", "copieurs": "Copieurs"}.get(code, code),
    }
    relation = {
        "id": 14,
        "source_service_code": "codes",
        "target_service_code": "copieurs",
        "unique_value_field_key": "code",
    }
    manager.list_custom_service_record_relation_links = lambda *, service_code, record_id, relation_id: (
        [{"linked_record": {"id": "code-existing", "values": {"code": "01987"}}}]
        if (service_code, record_id, relation_id) == ("copieurs", "copier-a", 14)
        else []
    )

    with pytest.raises(ValueError, match="qu'une fois pour chaque fiche « Copieurs »"):
        manager._validate_relation_unique_value(
            relation=relation,
            source_record_id="code-new",
            target_record_id="copier-a",
            source_values={"code": "01987"},
        )

    manager._validate_relation_unique_value(
        relation=relation,
        source_record_id="code-new",
        target_record_id="copier-b",
        source_values={"code": "01987"},
    )


def test_filtered_relation_candidate_error_identifies_the_missing_shared_relation():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"code": code, "label": code.title()}
    manager.list_custom_service_relations = lambda *, service_code="": {
        "codes": [
            {"id": 10, "source_service_code": "codes", "target_service_code": "agents", "is_active": True},
            {"id": 11, "source_service_code": "codes", "target_service_code": "copieurs", "is_active": True},
        ],
        "agents": [{"id": 12, "source_service_code": "agents", "target_service_code": "copieurs", "is_active": True}],
    }.get(service_code, [])
    manager.list_custom_service_record_relation_links = lambda *, service_code, record_id, relation_id: (
        [{"linked_record": {"id": "copier-a"}}]
        if (service_code, record_id, relation_id) == ("codes", "code-a", 11)
        else []
    )

    with pytest.raises(ValueError, match="ne partage aucune fiche « Copieurs »"):
        manager._validate_relation_shared_candidate(
            relation={
                "id": 10,
                "source_service_code": "codes",
                "target_service_code": "agents",
                "filter_candidates_by_shared_relation": True,
            },
            source_record_id="code-a",
            target_record_id="agent-a",
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
    assert conn.params[:6] == [
        ("copieurs", "copieurs"),
        ("copieurs", "copieurs"),
        ("copieurs",),
        ("copieurs", "copieurs"),
        ("copieurs",),
        ("copieurs",),
    ]
    assert "custom_service_relation_links" in conn.statements[0]
    assert "custom_service_record_history" in conn.statements[1]
    assert "custom_service_relations" in conn.statements[3]
    assert "DELETE FROM custom_service_records" in conn.statements[4]
    assert "DELETE FROM custom_services" in conn.statements[5]


def test_delete_local_custom_record_cleans_relation_links(monkeypatch):
    manager = _make_manager_stub()
    conn = _FakeConn(rowcounts={"UPDATE custom_service_records": 0})
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn
    monkeypatch.setattr("monitoring.storage.mariadb_manager.delete_record_index", lambda **_kwargs: None)

    deleted = manager.delete_custom_service_record(service_code="code_copieur", record_id="code-1")

    assert deleted == 1
    link_cleanup_index = next(
        index for index, statement in enumerate(conn.statements)
        if statement.startswith("DELETE l") and "custom_service_relation_links" in statement
    )
    record_delete_index = next(
        index for index, statement in enumerate(conn.statements)
        if statement.startswith("DELETE FROM custom_service_records")
    )
    assert link_cleanup_index < record_delete_index
    assert conn.params[link_cleanup_index] == ("code_copieur", "code-1", "code_copieur", "code-1")


def test_delete_target_record_keeps_a_relation_history_event_for_the_source_record(monkeypatch):
    manager = _make_manager_stub()
    conn = _FakeConn(
        fetchall_values=[[(19, "copieur-1", "site-1", "copieurs")]],
        rowcounts={"UPDATE custom_service_records": 0},
    )
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn
    monkeypatch.setattr("monitoring.storage.mariadb_manager.delete_record_index", lambda **_kwargs: None)

    deleted = manager.delete_custom_service_record(
        service_code="sites",
        record_id="site-1",
        changed_by="damien",
    )

    assert deleted == 1
    history_insert_index = next(
        index
        for index, statement in enumerate(conn.statements)
        if statement.startswith("INSERT INTO custom_service_record_history")
    )
    assert conn.params[history_insert_index] == [
        ("copieurs", "copieur-1", "__relation_19", "site-1", "damien"),
    ]


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
                                0,
                                0,
                                0,
                                "standard",
                                "",
                                "",
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
                        0,
                        0,
                        0,
                        "standard",
                        "",
                        "",
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


def test_custom_service_relation_capacity_message_uses_business_labels():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"label": "Code copieur"} if code == "code_copieur" else None

    message = manager._custom_service_relation_capacity_message(
        relation={"source_service_code": "code_copieur", "target_service_code": "utilisateurs"},
        limited_side="target",
    )

    assert "Agent" in message
    assert "Code copieur" in message
    assert "Plusieurs vers un" in message


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
                    0,
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
                    0,
                    0,
                    0,
                    "standard",
                    "",
                    "",
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


def test_replace_custom_service_relations_keeps_links_when_cardinality_changes():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"code": code}
    conn = _FakeConn(
        fetchall_values=[
            [(42, "code_copieur", "utilisateurs", "one_to_many", "out")],
            [(
                42,
                "code_copieur",
                "utilisateurs",
                "est attribue a",
                "many_to_one",
                "out",
                "Agent",
                0,
                1,
                1,
                0,
                0,
                "standard",
                "",
                "",
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

    manager.replace_custom_service_relations(
        service_code="code_copieur",
        relations=[{
            "target_service_code": "utilisateurs",
            "cardinality": "many_to_one",
            "direction": "out",
            "verb": "est attribue a",
            "display_label": "Agent",
        }],
    )

    update_params = next(
        params
        for statement, params in zip(conn.statements, conn.params)
        if statement.startswith("UPDATE custom_service_relations")
    )
    assert update_params[:2] == ("many_to_one", "out")
    assert not any("SELECT relation_id, COUNT(*)" in statement for statement in conn.statements)
    assert not any(statement.startswith("INSERT INTO custom_service_relations") for statement in conn.statements)


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


def test_replace_custom_service_relations_can_remove_linked_relation_after_explicit_confirmation():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"code": code}
    conn = _FakeConn(
        fetchall_values=[
            [(42, "copieurs", "sites", "many_to_one", "out")],
            [(42, 3)],
            [],
        ],
    )
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    manager.replace_custom_service_relations(
        service_code="copieurs",
        relations=[],
        allow_linked_relation_deletion=True,
    )

    delete_links_index = next(
        index
        for index, statement in enumerate(conn.statements)
        if statement.startswith("DELETE FROM custom_service_relation_links WHERE relation_id IN")
    )
    delete_relation_index = next(
        index
        for index, statement in enumerate(conn.statements)
        if "DELETE FROM custom_service_relations WHERE source_service_code = %s AND id IN" in statement
    )
    assert delete_links_index < delete_relation_index
    assert conn.params[delete_links_index] == [42]


def test_replace_custom_service_relations_requires_confirmation_before_removing_history():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"code": code}
    conn = _FakeConn(
        fetchall_values=[
            [(42, "copieurs", "sites", "many_to_one", "out")],
            [],
            [("__relation_42", 2)],
        ],
    )
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    with pytest.raises(ValueError, match="liens ou un historique"):
        manager.replace_custom_service_relations(service_code="copieurs", relations=[])

    assert not any("DELETE FROM custom_service_relations WHERE source_service_code = %s AND id IN" in statement for statement in conn.statements)


def test_replace_custom_service_relations_removes_history_only_after_explicit_confirmation():
    manager = _make_manager_stub()
    manager.get_custom_service = lambda *, code: {"code": code}
    conn = _FakeConn(
        fetchall_values=[
            [(42, "copieurs", "sites", "many_to_one", "out")],
            [],
            [("__relation_42", 2)],
        ],
    )
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    manager.replace_custom_service_relations(
        service_code="copieurs",
        relations=[],
        allow_linked_relation_deletion=True,
    )

    delete_history_index = next(
        index
        for index, statement in enumerate(conn.statements)
        if statement.startswith("DELETE FROM custom_service_record_history WHERE field_key IN")
    )
    delete_relation_index = next(
        index
        for index, statement in enumerate(conn.statements)
        if "DELETE FROM custom_service_relations WHERE source_service_code = %s AND id IN" in statement
    )
    assert delete_history_index < delete_relation_index
    assert conn.params[delete_history_index] == ["__relation_42"]


def test_delete_custom_service_relation_refuses_to_orphan_history():
    manager = _make_manager_stub()
    conn = _FakeConn(fetchone_values=[("copieurs",), 0, 3])
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn

    with pytest.raises(ValueError, match=r"3 entree\(s\) d'historique"):
        manager.delete_custom_service_relation(relation_id=42, source_service_code="copieurs")

    assert not any("DELETE FROM custom_service_relations" in statement for statement in conn.statements)


def test_directory_relation_uses_ad_name_when_legacy_cache_label_is_the_external_id():
    manager = _make_manager_stub()

    record = manager._system_relation_record_from_entry(
        service_code="agents",
        entry={
            "external_id": "4fc73446488647c5baca90667b400c84",
            "display_label": "4fc73446488647c5baca90667b400c84",
            "payload": {"displayName": "Damien Martin", "sAMAccountName": "dmartin"},
        },
    )

    assert record["values"]["display_name"] == "Damien Martin"
