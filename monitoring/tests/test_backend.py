from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from monitoring.api.app import create_app
from monitoring.backend.app_backend import build_application_backend
from monitoring.config.settings import NotificationSettings
from monitoring.storage.sqlite_manager import SQLiteFileManager


def _fake_sqlite_init(tmp_path, db_name="devices.db"):
    def _init(self, _db_name=db_name):
        self.data_dir = str(tmp_path)
        self.db_path = str(tmp_path / _db_name)

    return _init


def test_build_application_backend_shares_services_and_manager(tmp_path: Path):
    settings_box = {"value": NotificationSettings()}
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ):
        manager = SQLiteFileManager()
        backend = build_application_backend(
            manager=manager,
            settings_loader=lambda: settings_box["value"],
            settings_saver=lambda new_settings: settings_box.__setitem__("value", new_settings),
        )

    assert backend.model._mgr is backend.manager
    assert backend.device_service._mgr is backend.manager
    assert backend.device_type_service._mgr is backend.manager
    assert backend.monitoring_service._logs_store is backend.manager
    assert backend.monitoring_runtime_service.model is backend.model
    assert backend.monitoring_runtime_service.monitoring_service is backend.monitoring_service


def test_api_can_use_shared_backend_instance(tmp_path: Path):
    settings_box = {"value": NotificationSettings()}
    secrets = {}

    def fake_get_password(_service, account):
        return secrets.get(account, "")

    def fake_set_password(_service, account, value):
        secrets[account] = value

    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ), patch(
        "monitoring.services.auth_service.keyring.get_password",
        side_effect=fake_get_password,
    ), patch(
        "monitoring.services.auth_service.keyring.set_password",
        side_effect=fake_set_password,
    ):
        manager = SQLiteFileManager()
        backend = build_application_backend(
            manager=manager,
            settings_loader=lambda: settings_box["value"],
            settings_saver=lambda new_settings: settings_box.__setitem__("value", new_settings),
        )
        backend.manager.write_devices_map({"switch": [], "server": []})
        app = create_app(backend=backend)
        client = TestClient(app)

        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = client.post(
            "/devices",
            headers=headers,
            json={
                "device_type": "switch",
                "name": "SW1",
                "ip": "10.0.0.1",
                "description": "core",
            },
        )

        assert created.status_code == 201
        assert "switch" in backend.model.device_data
        assert len(backend.model.device_data["switch"]) == 1


def test_embedded_api_shutdown_does_not_stop_shared_runtime_when_disabled(tmp_path: Path):
    settings_box = {"value": NotificationSettings()}
    secrets = {}

    def fake_get_password(_service, account):
        return secrets.get(account, "")

    def fake_set_password(_service, account, value):
        secrets[account] = value

    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ), patch(
        "monitoring.services.auth_service.keyring.get_password",
        side_effect=fake_get_password,
    ), patch(
        "monitoring.services.auth_service.keyring.set_password",
        side_effect=fake_set_password,
    ):
        manager = SQLiteFileManager()
        backend = build_application_backend(
            manager=manager,
            settings_loader=lambda: settings_box["value"],
            settings_saver=lambda new_settings: settings_box.__setitem__("value", new_settings),
        )
        backend.manager.write_devices_map({"switch": [], "server": []})
        backend.monitoring_runtime_service.monitoring_service.start_monitoring("server")
        assert backend.model.do_run["server"] is True

        app = create_app(backend=backend, stop_runtime_on_shutdown=False)
        with TestClient(app):
            pass

        assert backend.model.do_run["server"] is True
