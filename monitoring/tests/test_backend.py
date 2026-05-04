from pathlib import Path
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from monitoring.api.app import create_app
from monitoring.backend.app_backend import build_application_backend, _resolve_auth_store_path
from monitoring.config.settings import NotificationSettings
from monitoring.config.setup_installation import SetupInstallationState
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


def test_build_application_backend_falls_back_to_sqlite_during_setup_if_mariadb_unavailable(tmp_path: Path):
    settings_box = {"value": NotificationSettings()}
    with patch(
        "monitoring.backend.app_backend.MariaDBFileManager",
        side_effect=RuntimeError("mariadb unavailable"),
    ), patch(
        "monitoring.backend.app_backend.load_setup_state",
        return_value=SetupInstallationState(completed=False),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ):
        backend = build_application_backend(
            settings_loader=lambda: settings_box["value"],
            settings_saver=lambda new_settings: settings_box.__setitem__("value", new_settings),
        )
    assert isinstance(backend.manager, SQLiteFileManager)


def test_build_application_backend_keeps_failure_after_setup_when_mariadb_unavailable():
    with patch(
        "monitoring.backend.app_backend.MariaDBFileManager",
        side_effect=RuntimeError("mariadb unavailable"),
    ), patch(
        "monitoring.backend.app_backend.load_setup_state",
        return_value=SetupInstallationState(completed=True),
    ):
        try:
            build_application_backend()
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "mariadb unavailable" in str(exc).lower()


def test_resolve_auth_store_path_defaults_to_manager_data_dir_parent(tmp_path: Path):
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ), patch.dict(
        "monitoring.backend.app_backend.os.environ",
        {},
        clear=False,
    ):
        manager = SQLiteFileManager()
        resolved = _resolve_auth_store_path(manager)
    if os.name != "nt":
        assert str(resolved) == "/etc/itops/auth.json"
    else:
        expected = Path(str(tmp_path)).parent / "config" / "auth.json"
        assert Path(resolved) == expected


def test_resolve_auth_store_path_prefers_env_override(tmp_path: Path):
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        _fake_sqlite_init(tmp_path),
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ), patch.dict(
        "monitoring.backend.app_backend.os.environ",
        {"NMP_AUTH_STORE_PATH": "itops-auth.json"},
        clear=False,
    ):
        manager = SQLiteFileManager()
        resolved = _resolve_auth_store_path(manager)
    assert str(resolved).endswith("itops-auth.json")
