from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api import app as api_app
from monitoring.api.app import ApiServices
from monitoring.config.settings import NotificationSettings
from monitoring.config.setup_installation import SetupInstallationState
from monitoring.services.settings_service import SettingsService


class _FakeAuth:
    def __init__(self) -> None:
        self.admin_password = ""

    def has_admin_password(self) -> bool:
        return bool(self.admin_password)

    def set_admin_password(self, password: str) -> None:
        self.admin_password = str(password or "")


class _FakeMonitoring:
    def __init__(self) -> None:
        self.applied_settings = None

    def apply_notification_settings(self, settings: NotificationSettings) -> None:
        self.applied_settings = settings


def test_setup_finalize_aligns_database_settings_runtime_and_setup_state(monkeypatch):
    saved_settings: list[NotificationSettings] = []
    saved_env: list[dict[str, str]] = []
    saved_setup_states: list[SetupInstallationState] = []
    saved_hebergement = []
    removed_tokens: list[bool] = []

    settings_service = SettingsService(
        loader=lambda: NotificationSettings(),
        saver=lambda settings: saved_settings.append(settings),
    )
    auth = _FakeAuth()
    monitoring = _FakeMonitoring()
    monkeypatch.delenv("NMP_DEV_SKIP_SETUP_WIZARD", raising=False)
    services = ApiServices(
        model=SimpleNamespace(),
        auth=auth,
        device_types=SimpleNamespace(),
        monitoring=monitoring,
        monitoring_runtime=SimpleNamespace(),
        config_storage=SimpleNamespace(),
        linked_files=SimpleNamespace(),
        device_config_files=SimpleNamespace(),
        network_tools=SimpleNamespace(),
        logs=SimpleNamespace(),
        storage_targets=SimpleNamespace(),
        settings_service=settings_service,
        settings_loader=settings_service.get,
        settings_saver=settings_service.save,
    )

    monkeypatch.setattr(api_app, "load_setup_state", lambda: SetupInstallationState(completed=False))
    monkeypatch.setattr(api_app, "read_setup_token", lambda: "setup-token")
    monkeypatch.setattr(api_app, "_provision_local_mariadb_from_setup", lambda _payload: None)
    monkeypatch.setattr(api_app, "_verify_mariadb_application_login", lambda _payload, timeout_seconds=20: None)
    monkeypatch.setattr(api_app, "_configure_reverse_proxy_from_setup", lambda **_kwargs: "/portal")
    monkeypatch.setattr(api_app, "save_hebergement_web_config", lambda config: saved_hebergement.append(config))
    monkeypatch.setattr(api_app, "update_install_env", lambda values: saved_env.append(dict(values)))
    monkeypatch.setattr(api_app, "save_setup_state", lambda state: saved_setup_states.append(state))
    monkeypatch.setattr(api_app, "remove_setup_token", lambda: removed_tokens.append(True))

    app = FastAPI()
    api_app._register_setup_routes(app, lambda: services)

    response = TestClient(app).post(
        "/setup/finalize",
        json={
            "setup_token": "setup-token",
            "admin_password": "admin-secret",
            "hote_ecoute": "0.0.0.0",
            "port_ecoute": 8080,
            "reverse_proxy_type": "caddy",
            "url_publique": "https://itops.mvl",
            "db_host": "127.0.0.1",
            "db_port": 3306,
            "db_user": "itops",
            "db_password": "db-secret",
            "db_name": "itops",
            "mariadb_root_password": "root-secret",
        },
    )

    assert response.status_code == 200
    assert response.json()["redirect_url"] == "/portal"
    assert auth.admin_password == "admin-secret"
    assert saved_hebergement
    assert saved_settings
    assert saved_settings[-1].web_server_host == "0.0.0.0"
    assert saved_settings[-1].web_server_port == 8080
    assert saved_settings[-1].web_server_reverse_proxy_type == "caddy"
    assert saved_settings[-1].web_server_public_url == "https://itops.mvl"
    assert monitoring.applied_settings == saved_settings[-1]
    assert saved_env and saved_env[-1]["NMP_MARIADB_DATABASE"] == "itops"
    assert saved_setup_states and saved_setup_states[-1].completed is True
    assert saved_setup_states[-1].reverse_proxy_type == "caddy"
    assert removed_tokens == [True]
