from monitoring.storage.mariadb_bootstrap import MariaDBBootstrapper


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []
        self.parameters = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, params=None):
        self.statements.append(statement)
        self.parameters.append(params)

    def executemany(self, statement, params):
        self.statements.append((statement, list(params)))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return (1,)


class _Connection:
    def __init__(self, rows):
        self.cursor_instance = _Cursor(rows)
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1


def test_legacy_custom_service_text_repair_restores_utf8_list_option():
    assert MariaDBBootstrapper._repair_legacy_utf8_mojibake("Mat\u00c3\u00a9riel informatique") == "Matériel informatique"


def test_legacy_custom_service_text_repair_keeps_correct_accented_text():
    assert MariaDBBootstrapper._repair_legacy_utf8_mojibake("Réception complète") == "Réception complète"


def test_legacy_custom_modules_are_assigned_to_sa_without_touching_system_modules():
    connection = _Connection([])
    calls = []
    connection.cursor_instance.execute = lambda statement, params=None: calls.append((statement, params))
    connection.cursor_instance.rowcount = 1

    MariaDBBootstrapper.backfill_legacy_custom_service_owners(
        connection, {"technical_accounts", "emails"},
    )

    statement, params = calls[1]
    assert "SET owner_subject = %s WHERE owner_subject = ''" in statement
    assert "code NOT IN (%s, %s)" in statement
    assert params == ("sa", "emails", "technical_accounts")
    connection.cursor_instance.rowcount = 0
    MariaDBBootstrapper.backfill_legacy_custom_service_owners(
        connection, {"technical_accounts", "emails"},
    )
    assert len(calls) == 3


def test_legacy_monitored_equipment_becomes_deployed_without_overwriting_explicit_status():
    connection = _Connection([
        ("switch-legacy", '{"type": "firmware"}'),
        ("switch-stored", '{"deployment_status": "Stocké"}'),
        ("switch-invalid", "not-json"),
    ])

    migrated = MariaDBBootstrapper.migrate_legacy_device_deployment_status(connection)

    assert migrated == 1
    assert connection.commits == 1
    update_statement, updates = connection.cursor_instance.statements[-1]
    assert "UPDATE devices SET custom_data" in update_statement
    assert updates == [('{"type": "firmware", "deployment_status": "Déployé"}', "switch-legacy")]


def test_existing_custom_service_table_adds_account_owner_column(monkeypatch):
    connection = _Connection([])
    monkeypatch.setattr(
        MariaDBBootstrapper, "_column_exists",
        lambda _conn, *, db_name, table_name, column_name: column_name != "owner_subject",
    )

    MariaDBBootstrapper.ensure_custom_service_columns(connection, "itops")

    assert connection.cursor_instance.statements == [
        "ALTER TABLE custom_services ADD COLUMN owner_subject VARCHAR(255) NOT NULL DEFAULT ''",
    ]


def test_auth_bootstrap_renames_only_the_legacy_module_builder_label():
    connection = _Connection([])

    MariaDBBootstrapper.ensure_auth_rbac_rows(connection)

    updates = [item for item in connection.cursor_instance.statements if isinstance(item, str) and "UPDATE auth_modules SET label = %s" in item]
    assert len(updates) == 1
    assert ("Gestion des modules personnalisés", "module_builder", "Gestion des modules personnels") in connection.cursor_instance.parameters
    assert connection.commits == 1
