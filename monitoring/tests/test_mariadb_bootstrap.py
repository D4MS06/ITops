from monitoring.storage.mariadb_bootstrap import MariaDBBootstrapper


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, _params=None):
        self.statements.append(statement)

    def executemany(self, statement, params):
        self.statements.append((statement, list(params)))

    def fetchall(self):
        return self.rows


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
