from unittest.mock import patch

from monitoring.storage.sqlite_manager import SQLiteFileManager


def _fake_sqlite_init(tmp_path, db_name="devices.db"):
    def _init(self, _db_name=db_name):
        self.data_dir = str(tmp_path)
        self.db_path = str(tmp_path / _db_name)

    return _init


def test_sqlite_write_and_read(tmp_path):
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ):
        mgr = SQLiteFileManager()
        payload = {
            "switch": [{"id": "sw1", "name": "SW1", "ip": "10.0.0.1", "description": "d", "notify": True}],
            "server": [],
        }
        mgr.write_devices_map(payload)
        expected_switch = [{**payload["switch"][0], "custom_data": {}}]
        assert mgr.read_devices_map() == {"switch": expected_switch, "server": []}


def test_sqlite_migrates_from_json_when_empty(tmp_path):
    seed = {
        "switch": [{"id": "sw1", "name": "SW1", "ip": "10.0.0.1", "description": "d", "notify": True}],
        "server": [
            {
                "id": "srv1",
                "name": "SRV1",
                "ip": "10.0.0.2",
                "description": "srv",
                "notify": False,
                "id_Teamviewer": "tv",
                "type": "Linux",
                "action_double_click": "ssh",
                "web_url": "",
                "ssh_user": "root",
            }
        ],
    }
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.json_manager.JSONFileManager.read_json_file",
        return_value=seed,
    ):
        mgr = SQLiteFileManager()
        data = mgr.read_devices_map()

    assert data["switch"][0]["id"] == "sw1"
    assert data["server"][0]["id"] == "srv1"
    assert data["server"][0]["type"] == "Linux"


def test_default_device_types_metadata_seeded(tmp_path):
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ):
        mgr = SQLiteFileManager()
        types = mgr.list_device_types()
        codes = {t["code"] for t in types}
        assert {"switch", "server"}.issubset(codes)

        server_fields = mgr.list_type_fields("server")
        field_keys = {f["field_key"] for f in server_fields}
        assert {"name", "ip", "type", "action_double_click"}.issubset(field_keys)

        server_actions = mgr.list_type_actions("server")
        action_keys = {a["action_key"] for a in server_actions}
        assert {"ssh", "web", "teamviewer", "remote_desktop"}.issubset(action_keys)


def test_status_logs_insert_and_filter(tmp_path):
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ):
        mgr = SQLiteFileManager()
        mgr.record_status_log(
            dtype="switch",
            device_id="sw1",
            device_name="SW-1",
            old_status="online",
            new_status="offline",
            event_kind="diagnostic_failure_burst",
            details="3 echecs consecutifs",
        )
        mgr.record_status_log(
            dtype="server",
            device_id="srv1",
            device_name="SRV-1",
            old_status="offline",
            new_status="online",
        )

        all_logs = mgr.list_status_logs(limit=10)
        assert len(all_logs) == 2
        sw_logs = mgr.list_status_logs(limit=10, dtype="switch", device_id="sw1")
        assert len(sw_logs) == 1
        assert sw_logs[0]["new_status"] == "offline"
        assert sw_logs[0]["event_kind"] == "diagnostic_failure_burst"
        assert sw_logs[0]["details"] == "3 echecs consecutifs"


def test_dynamic_device_type_crud(tmp_path):
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ):
        mgr = SQLiteFileManager()
        code = mgr.save_device_type(
            code="nas_dsm",
            label="NAS DSM",
            template_code="server",
            monitoring_enabled=True,
        )
        assert code == "nas_dsm"

        types = {t["code"]: t for t in mgr.list_device_types()}
        assert "nas_dsm" in types
        assert types["nas_dsm"]["icon"] == "server"

        fields = {f["field_key"] for f in mgr.list_type_fields("nas_dsm")}
        assert {"name", "ip", "type", "action_double_click"}.issubset(fields)

        deleted = mgr.delete_device_type("nas_dsm")
        assert deleted is True
        codes = {t["code"] for t in mgr.list_device_types()}
        assert "nas_dsm" not in codes


def test_replace_type_schema(tmp_path):
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ):
        mgr = SQLiteFileManager()
        mgr.save_device_type(
            code="fw",
            label="Firewall",
            template_code="switch",
            monitoring_enabled=True,
        )
        mgr.replace_type_schema(
            type_code="fw",
            fields=[
                {"field_key": "name", "label": "Nom", "field_kind": "text", "required": True},
                {"field_key": "ip", "label": "IP", "field_kind": "ip", "required": True},
                {"field_key": "description", "label": "Description", "field_kind": "text", "required": False},
                {"field_key": "type", "label": "OS", "field_kind": "choice", "required": True, "options": "Windows,Linux,Firmware,Autre"},
                {"field_key": "vendor", "label": "Constructeur", "field_kind": "choice", "options": "Cisco,Fortinet"},
            ],
            actions=[
                {
                    "action_key": "web",
                    "label": "Ouvrir Web",
                    "target_kind": "builtin",
                    "target_value": "web",
                    "is_default": True,
                }
            ],
        )

        fields = {f["field_key"] for f in mgr.list_type_fields("fw")}
        actions = {a["action_key"] for a in mgr.list_type_actions("fw")}
        assert {"name", "ip", "description", "type", "vendor"} == fields
        assert {"web"} == actions
