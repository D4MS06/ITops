from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from monitoring.api.app import create_app
from monitoring.config.settings import NotificationSettings
from monitoring.models.devices_model import DevicesModel
from monitoring.services.auth_service import AuthService
from monitoring.storage.sqlite_manager import SQLiteFileManager


def _fake_sqlite_init(tmp_path, db_name="devices.db"):
    def _init(self, _db_name=db_name):
        self.data_dir = str(tmp_path)
        self.db_path = str(tmp_path / _db_name)

    return _init


def _build_client(tmp_path: Path):
    settings_box = {
        "value": NotificationSettings(
            smtp_host="smtp.example.com",
            smtp_port=25,
            recipients="ops@example.com",
            ui_theme="light",
            config_storage_mode="local",
        )
    }
    secrets = {}

    def fake_get_password(_service, account):
        return secrets.get(account, "")

    def fake_set_password(_service, account, value):
        secrets[account] = value

    def fake_delete_password(_service, account):
        secrets.pop(account, None)

    patchers = (
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.__init__", _fake_sqlite_init(tmp_path)),
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json", lambda self, conn: None),
        patch("monitoring.services.auth_service.keyring.get_password", side_effect=fake_get_password),
        patch("monitoring.services.auth_service.keyring.set_password", side_effect=fake_set_password),
        patch("monitoring.services.auth_service.keyring.delete_password", side_effect=fake_delete_password),
    )

    for patcher in patchers:
        patcher.start()

    mgr = SQLiteFileManager()
    mgr.write_devices_map(
        {
            "switch": [{"id": "sw1", "name": "SW1", "ip": "10.0.0.1", "description": "core", "notify": True}],
            "server": [{"id": "srv1", "name": "SRV1", "ip": "10.0.0.2", "description": "app", "notify": False}],
        }
    )
    mgr.record_status_log(
        dtype="server",
        device_id="srv1",
        device_name="SRV1",
        old_status="online",
        new_status="offline",
    )

    model = DevicesModel(manager=mgr)
    auth = AuthService()
    app = create_app(
        model=model,
        auth_service=auth,
        logs_manager=mgr,
        settings_loader=lambda: settings_box["value"],
        settings_saver=lambda new_settings: settings_box.__setitem__("value", new_settings),
    )
    client = TestClient(app)

    def cleanup():
        for patcher in reversed(patchers):
            patcher.stop()

    return client, auth, settings_box, cleanup


def test_api_auth_bootstrap_login_and_protected_endpoints(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        assert client.get("/auth/status").json() == {"has_admin_password": False}

        bootstrap = client.post("/auth/bootstrap", json={"password": "admin-pass"})
        assert bootstrap.status_code == 200

        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        devices = client.get("/devices", headers=headers)
        assert devices.status_code == 200
        assert len(devices.json()) == 2

        filtered = client.get("/devices", params={"device_type": "server"}, headers=headers)
        assert len(filtered.json()) == 1
        assert filtered.json()[0]["device_type"] == "server"

        logs = client.get("/logs", headers=headers)
        assert logs.status_code == 200
        assert logs.json()[0]["device_id"] == "srv1"

        settings = client.get("/settings", headers=headers)
        assert settings.status_code == 200
        assert "password" not in settings.json()
    finally:
        cleanup()


def test_api_device_crud_and_settings_update(tmp_path: Path):
    client, _auth, settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        created = client.post(
            "/devices",
            headers=headers,
            json={
                "device_type": "switch",
                "name": "SW2",
                "ip": "10.0.0.10",
                "description": "edge",
                "notify": True,
            },
        )
        assert created.status_code == 201
        created_body = created.json()

        updated = client.put(
            f"/devices/switch/{created_body['id']}",
            headers=headers,
            json={
                "name": "SW2-Renamed",
                "ip": "10.0.0.11",
                "description": "edge-updated",
                "notify": False,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "SW2-Renamed"
        assert updated.json()["notify"] is False

        deleted = client.delete(f"/devices/switch/{created_body['id']}", headers=headers)
        assert deleted.status_code == 200

        settings_update = client.put(
            "/settings",
            headers=headers,
            json={
                **client.get("/settings", headers=headers).json(),
                "ui_theme": "dark",
                "probe_interval_ms": 2000,
            },
        )
        assert settings_update.status_code == 200
        assert settings_box["value"].ui_theme == "dark"
        assert settings_box["value"].probe_interval_ms == 2000
    finally:
        cleanup()


def test_api_requires_authentication_for_protected_routes(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        response = client.get("/devices")
        assert response.status_code == 401
    finally:
        cleanup()
