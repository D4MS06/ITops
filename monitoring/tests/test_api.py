from pathlib import Path
import threading
import base64
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from monitoring.api.app import (
    _build_switch_proxy_device_locator,
    _build_switch_proxy_fallback_paths,
    _build_switch_proxy_legacy_redirect_url,
    _build_switch_proxy_request_headers,
    _normalize_switch_proxy_device_locator,
    _SWITCH_PROXY_PREFIX_COOKIE,
    _SWITCH_PROXY_TOKEN_COOKIE,
    create_app,
    _build_switch_target_url,
    _provision_local_mariadb_from_setup,
    _provision_local_mariadb_with_cli,
    _rewrite_switch_proxy_location,
    _is_switch_proxy_html_response,
    _normalize_switch_proxy_response_content_type,
    _prefix_switch_root_paths,
    _rewrite_switch_proxy_refresh,
    _rewrite_switch_proxy_html,
    _rewrite_switch_proxy_javascript,
    _rewrite_switch_proxy_xml,
    _rewrite_switch_proxy_set_cookie,
    _resolve_switch_base_url,
    _strip_proxy_token_from_query,
    _run_subprocess_checked,
    _enable_reverse_proxy_service_if_needed,
)
from monitoring.api.schemas import SetupFinalizeRequest
from monitoring.config.setup_installation import SetupInstallationState, save_setup_state
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
            switch_configs_dir=str(tmp_path / "switch_configs"),
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
        patch.dict(
            os.environ,
            {
                "NMP_SETUP_CONFIG": str(tmp_path / "setup_installation.json"),
                "NMP_SETUP_TOKEN_FILE": str(tmp_path / "setup.token"),
                "NMP_INSTALL_ENV_PATH": str(tmp_path / "itops.env"),
                "NMP_HEBERGEMENT_CONFIG": str(tmp_path / "hebergement_web.json"),
                "NMP_SETUP_SKIP_MARIADB_PROVISION": "1",
                "NMP_SETUP_SKIP_REVERSE_PROXY_SETUP": "1",
            },
            clear=False,
        ),
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.__init__", _fake_sqlite_init(tmp_path)),
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json", lambda self, conn: None),
        patch("monitoring.services.auth_service.keyring.get_password", side_effect=fake_get_password),
        patch("monitoring.services.auth_service.keyring.set_password", side_effect=fake_set_password),
        patch("monitoring.services.auth_service.keyring.delete_password", side_effect=fake_delete_password),
    )

    for patcher in patchers:
        patcher.start()

    mgr = SQLiteFileManager()
    config_versions_patcher = patch("monitoring.utils.config_files._config_versions_store", return_value=mgr)
    config_versions_patcher.start()
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
    auth = AuthService(session_store=mgr, password_store_path=tmp_path / "auth.json")
    app = create_app(
        model=model,
        auth_service=auth,
        logs_manager=mgr,
        settings_loader=lambda: settings_box["value"],
        settings_saver=lambda new_settings: settings_box.__setitem__("value", new_settings),
    )
    client = TestClient(app)

    def cleanup():
        config_versions_patcher.stop()
        for patcher in reversed(patchers):
            patcher.stop()

    return client, auth, settings_box, cleanup


def test_api_auth_bootstrap_login_and_protected_endpoints(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        status = client.get("/auth/status").json()
        assert status["has_admin_password"] is False
        assert status["first_start_required"] is True

        bootstrap = client.post("/auth/bootstrap", json={"password": "admin-pass"})
        assert bootstrap.status_code == 200

        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        devices = client.get("/devices", headers=headers)
        assert devices.status_code == 200
        assert len(devices.json()) == 2
        assert all("has_saved_config" in row for row in devices.json())

        filtered = client.get("/devices", params={"device_type": "server"}, headers=headers)
        assert len(filtered.json()) == 1
        assert filtered.json()[0]["device_type"] == "server"

        logs = client.get("/logs", headers=headers)
        assert logs.status_code == 200
        assert logs.json()[0]["device_id"] == "srv1"

        settings = client.get("/settings", headers=headers)
        assert settings.status_code == 200
        assert "password" not in settings.json()

        modules = client.get("/auth/me/modules", headers=headers)
        assert modules.status_code == 200
        module_rows = modules.json()
        assert module_rows
        by_code = {row["code"]: row for row in module_rows}
        assert by_code["monitoring"]["granted"] is True
        assert by_code["monitoring"]["route_path"] == "/monitoring"

        profile = client.get("/auth/me/profile", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["subject"] == "sa"
        assert profile.json()["role_code"] == "admin"

        context = client.get("/auth/me/context", headers=headers)
        assert context.status_code == 200
        context_payload = context.json()
        assert context_payload["subject"] == "sa"
        assert context_payload["role_code"] == "admin"
        assert any(str(row.get("code")) == "monitoring" for row in context_payload.get("modules", []))
    finally:
        cleanup()


def test_api_first_login_sa_requires_password_change(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        status_before = client.get("/auth/status")
        assert status_before.status_code == 200
        assert status_before.json()["has_admin_password"] is False
        assert status_before.json()["first_start_required"] is True

        blocked = client.post("/auth/login", json={"username": "sa", "password": "sa"})
        assert blocked.status_code == 428
        assert "changement du mot de passe requis" in blocked.json().get("detail", "").lower()

        changed = client.post(
            "/auth/login",
            json={"username": "sa", "password": "sa", "new_password": "Admin#2026"},
        )
        assert changed.status_code == 200
        token = changed.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        me = client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["subject"] == "sa"

        status_after = client.get("/auth/status")
        assert status_after.status_code == 200
        assert status_after.json()["has_admin_password"] is True
        assert status_after.json()["first_start_required"] is False

        user_row = client.app.state.services.logs.get_auth_user(subject="sa")
        assert user_row is not None
        assert user_row["password_hash"]
        assert user_row["password_hash"] != "sa"
        assert user_row["must_change_password"] is False
    finally:
        cleanup()


def test_api_rejects_unknown_username_even_with_admin_password(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        blocked = client.post("/auth/login", json={"username": "ghost_user", "password": "admin-pass"})
        assert blocked.status_code == 401
        assert "identifiants invalides" in blocked.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_setup_finalize_requires_token_when_present(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        token_file = tmp_path / "setup.token"
        token_file.write_text("abc123", encoding="utf-8")

        denied = client.post(
            "/setup/finalize",
            json={
                "setup_token": "bad",
                "admin_password": "Admin#2026",
                "mariadb_root_password": "Root#2026",
                "hote_ecoute": "0.0.0.0",
                "port_ecoute": 8080,
            },
        )
        assert denied.status_code == 401
        assert "token d'installation invalide" in denied.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_setup_finalize_rejects_short_mariadb_root_password(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        token_file = tmp_path / "setup.token"
        token_file.write_text("abc123", encoding="utf-8")

        denied = client.post(
            "/setup/finalize",
            json={
                "setup_token": "abc123",
                "admin_password": "Admin#2026",
                "mariadb_root_password": "short",
                "hote_ecoute": "0.0.0.0",
                "port_ecoute": 8080,
            },
        )
        assert denied.status_code == 422
        assert "detail" in denied.json()
    finally:
        cleanup()


def test_api_setup_finalize_writes_files_and_unlocks_portal(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        token_file = tmp_path / "setup.token"
        token_file.write_text("setup-ok", encoding="utf-8")

        done = client.post(
            "/setup/finalize",
            json={
                "setup_token": "setup-ok",
                "admin_password": "Admin#2026",
                "hote_ecoute": "0.0.0.0",
                "port_ecoute": 8080,
                "reverse_proxy_type": "nginx",
                "url_publique": "https://itops.local",
                "db_host": "127.0.0.1",
                "db_port": 3306,
                "db_user": "itops",
                "db_password": "Secret123!",
                "db_name": "itops",
                "mariadb_root_password": "Root#2026",
            },
        )
        assert done.status_code == 200
        assert "installation finalisee" in done.json().get("message", "").lower()
        assert done.json().get("redirect_url", "") == "https://itops.local"

        status_payload = client.get("/setup/status").json()
        assert status_payload["setup_required"] is False
        assert status_payload["setup_completed"] is True
        assert status_payload["has_admin_password"] is True
        assert status_payload["has_setup_token"] is False

        root = client.get("/")
        assert root.status_code == 200
        assert "Portail Services IT" in root.text

        env_text = (tmp_path / "itops.env").read_text(encoding="utf-8")
        assert "NMP_MARIADB_DATABASE='itops'" in env_text
        assert "NMP_MARIADB_PASSWORD='Secret123!'" in env_text
        assert "NMP_MARIADB_ROOT_PASSWORD='Root#2026'" in env_text

        hebergement_text = (tmp_path / "hebergement_web.json").read_text(encoding="utf-8")
        assert "\"reverse_proxy_type\": \"nginx\"" in hebergement_text
        assert "\"url_publique\": \"https://itops.local\"" in hebergement_text
    finally:
        cleanup()


def test_api_setup_finalize_requires_public_url_when_proxy_enabled(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        token_file = tmp_path / "setup.token"
        token_file.write_text("setup-nginx", encoding="utf-8")

        denied = client.post(
            "/setup/finalize",
            json={
                "setup_token": "setup-nginx",
                "admin_password": "Admin#2026",
                "hote_ecoute": "0.0.0.0",
                "port_ecoute": 8080,
                "reverse_proxy_type": "nginx",
                "url_publique": "",
                "mariadb_root_password": "Root#2026",
            },
        )
        assert denied.status_code == 422
        assert "url publique obligatoire" in denied.json().get("detail", "").lower()
    finally:
        cleanup()


def test_provision_local_mariadb_grants_localhost_and_loopback_even_with_127_host(tmp_path: Path):
    executed_sql = []

    class _FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql):
            executed_sql.append(str(sql))

    class _FakeConnection:
        def cursor(self):
            return _FakeCursor()

        def close(self):
            return None

    fake_pymysql = SimpleNamespace(
        connect=lambda **_kwargs: _FakeConnection(),
        cursors=SimpleNamespace(Cursor=object),
    )

    payload = SetupFinalizeRequest(
        setup_token="t",
        admin_password="Admin#2026",
        db_host="127.0.0.1",
        db_port=3306,
        db_user="itops",
        db_password="Secret123!",
        db_name="itops",
        mariadb_root_password="Root#2026",
    )

    with patch.dict(os.environ, {"NMP_SETUP_SKIP_MARIADB_PROVISION": "0"}, clear=False), \
         patch.dict(sys.modules, {"pymysql": fake_pymysql}), \
         patch("monitoring.api.app.Path.exists", return_value=False):
        _provision_local_mariadb_from_setup(payload)

    assert any("@'localhost'" in stmt for stmt in executed_sql)
    assert any("@'127.0.0.1'" in stmt for stmt in executed_sql)
    assert any("FLUSH PRIVILEGES" in stmt for stmt in executed_sql)


def test_api_serves_web_application_assets(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        portal = client.get("/")
        assert portal.status_code == 200
        assert "text/html" in portal.headers["content-type"]
        assert "Assistant de premiere installation" in portal.text

        setup_status = client.get("/setup/status")
        assert setup_status.status_code == 200
        assert setup_status.json()["setup_required"] is True

        index = client.get("/monitoring")
        assert index.status_code == 200
        assert "text/html" in index.headers["content-type"]
        assert "ITops - Monitoring Web" in index.text

        script = client.get("/web/app.js")
        assert script.status_code == 200
        assert "application/javascript" in script.headers["content-type"] or "text/javascript" in script.headers["content-type"]
        assert "monitoring/ws" in script.text
        assert "max-age=604800" in script.headers.get("cache-control", "")

        shared_auth = client.get("/web/shared_auth.js")
        assert shared_auth.status_code == 200
        assert "application/javascript" in shared_auth.headers["content-type"] or "text/javascript" in shared_auth.headers["content-type"]
        assert "fetchSessionContext" in shared_auth.text

        shared_api = client.get("/web/shared_api.js")
        assert shared_api.status_code == 200
        assert "application/javascript" in shared_api.headers["content-type"] or "text/javascript" in shared_api.headers["content-type"]
        assert "requestJson" in shared_api.text
        assert "max-age=604800" in shared_api.headers.get("cache-control", "")

        shared_ui = client.get("/web/shared_ui.js")
        assert shared_ui.status_code == 200
        assert "application/javascript" in shared_ui.headers["content-type"] or "text/javascript" in shared_ui.headers["content-type"]
        assert "createFieldMarkup" in shared_ui.text
        assert "max-age=604800" in shared_ui.headers.get("cache-control", "")

        shared_import = client.get("/web/shared_import.js")
        assert shared_import.status_code == 200
        assert "application/javascript" in shared_import.headers["content-type"] or "text/javascript" in shared_import.headers["content-type"]
        assert "postImport" in shared_import.text
        assert "downloadExport" in shared_import.text
        assert "max-age=604800" in shared_import.headers.get("cache-control", "")

        shared_download = client.get("/web/shared_download.js")
        assert shared_download.status_code == 200
        assert "application/javascript" in shared_download.headers["content-type"] or "text/javascript" in shared_download.headers["content-type"]
        assert "downloadBinary" in shared_download.text
        assert "max-age=604800" in shared_download.headers.get("cache-control", "")

        shared_admin_ui = client.get("/web/shared_admin_ui.js")
        assert shared_admin_ui.status_code == 200
        assert "application/javascript" in shared_admin_ui.headers["content-type"] or "text/javascript" in shared_admin_ui.headers["content-type"]
        assert "buildRolesModalMarkup" in shared_admin_ui.text
        assert "max-age=604800" in shared_admin_ui.headers.get("cache-control", "")

        shared_admin_store = client.get("/web/shared_admin_store.js")
        assert shared_admin_store.status_code == 200
        assert "application/javascript" in shared_admin_store.headers["content-type"] or "text/javascript" in shared_admin_store.headers["content-type"]
        assert "createAdminStore" in shared_admin_store.text
        assert "max-age=604800" in shared_admin_store.headers.get("cache-control", "")

        shared_admin_controller = client.get("/web/shared_admin_controller.js")
        assert shared_admin_controller.status_code == 200
        assert "application/javascript" in shared_admin_controller.headers["content-type"] or "text/javascript" in shared_admin_controller.headers["content-type"]
        assert "handleModalClick" in shared_admin_controller.text
        assert "max-age=604800" in shared_admin_controller.headers.get("cache-control", "")

        favicon = client.get("/favicon.ico")
        assert favicon.status_code == 200
        assert "image/" in favicon.headers["content-type"]
    finally:
        cleanup()


def test_setup_not_required_when_install_completed_even_without_admin_password(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        save_setup_state(
            SetupInstallationState(
                completed=True,
                completed_at="2026-05-04T11:30:00+00:00",
                completed_by="wizard-web",
                reverse_proxy_type="aucun",
                public_url="",
            )
        )
        status_payload = client.get("/setup/status").json()
        assert status_payload["setup_completed"] is True
        assert status_payload["has_admin_password"] is False
        assert status_payload["setup_required"] is False

        root = client.get("/")
        assert root.status_code == 200
        assert "Portail Services IT" in root.text
    finally:
        cleanup()


def test_api_download_https_root_certificate(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        def _fake_export(self, destination):
            target = Path(destination)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fake-root-cert", encoding="utf-8")
            return target

        with patch("monitoring.api.app.CaddyManager.export_root_certificate", _fake_export):
            response = client.get("/ui/https-root-certificate/download", headers=headers)

        assert response.status_code == 200
        assert response.content == b"fake-root-cert"
        assert "application/x-x509-ca-cert" in response.headers.get("content-type", "")
    finally:
        cleanup()


def test_api_download_https_root_certificate_permission_denied(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        with patch(
            "monitoring.api.app.CaddyManager.export_root_certificate",
            side_effect=PermissionError("Acces refuse"),
        ):
            response = client.get("/ui/https-root-certificate/download", headers=headers)

        assert response.status_code == 403
        assert "droits insuffisants" in response.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_network_tools_endpoints(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        tools = client.app.state.services.network_tools
        with (
            patch.object(tools, "ping", return_value=(True, "PING OK")),
            patch.object(tools, "port_check", return_value=(False, "PORT KO")),
            patch.object(tools, "traceroute", return_value=(True, "TRACE OK")),
            patch.object(tools, "dns_lookup", return_value=(True, "DNS OK")),
            patch.object(tools, "http_check", return_value=(False, "HTTP KO")),
            patch.object(tools, "snmp_check", return_value=(False, "SNMP KO")),
        ):
            ping = client.post("/network-tools/ping", json={"ip": "10.0.0.1"}, headers=headers)
            assert ping.status_code == 200
            assert ping.json() == {"ok": True, "output": "PING OK"}

            port = client.post("/network-tools/port-check", json={"ip": "10.0.0.1", "port": 22}, headers=headers)
            assert port.status_code == 200
            assert port.json()["ok"] is False

            trace = client.post("/network-tools/traceroute", json={"ip": "10.0.0.1"}, headers=headers)
            assert trace.status_code == 200
            assert trace.json()["output"] == "TRACE OK"

            dns = client.post("/network-tools/dns-lookup", json={"target": "example.com"}, headers=headers)
            assert dns.status_code == 200
            assert dns.json()["ok"] is True

            http = client.post("/network-tools/http-check", json={"url": "https://example.com"}, headers=headers)
            assert http.status_code == 200
            assert http.json()["ok"] is False

            snmp = client.post(
                "/network-tools/snmp-check",
                json={"ip": "10.0.0.1", "community": "public", "oid": "1.3.6.1.2.1.1.1.0"},
                headers=headers,
            )
            assert snmp.status_code == 200
            assert snmp.json()["output"] == "SNMP KO"
    finally:
        cleanup()


def test_api_network_tools_stream_endpoints(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        tools = client.app.state.services.network_tools

        def _emit_lines(lines):
            def _runner(_target, on_line, *args, **kwargs):
                for line in lines:
                    on_line(line)
                return True
            return _runner

        with (
            patch.object(tools, "stream_ping", side_effect=_emit_lines(["PING-1", "PING-2"])),
            patch.object(tools, "stream_traceroute", side_effect=_emit_lines(["TRACE-1", "TRACE-2"])),
            patch.object(tools, "stream_dns_lookup", side_effect=_emit_lines(["DNS-1"])),
        ):
            ping = client.post("/network-tools/ping/stream", json={"ip": "10.0.0.1"}, headers=headers)
            assert ping.status_code == 200
            ping_events = [json.loads(line) for line in ping.text.splitlines() if line.strip()]
            assert any(event.get("type") == "line" and event.get("line") == "PING-1" for event in ping_events)
            assert any(event.get("type") == "done" and event.get("ok") is True for event in ping_events)

            trace = client.post("/network-tools/traceroute/stream", json={"ip": "10.0.0.1"}, headers=headers)
            assert trace.status_code == 200
            trace_events = [json.loads(line) for line in trace.text.splitlines() if line.strip()]
            assert any(event.get("type") == "line" and event.get("line") == "TRACE-1" for event in trace_events)
            assert any(event.get("type") == "done" and event.get("ok") is True for event in trace_events)

            dns = client.post("/network-tools/dns-lookup/stream", json={"target": "example.com"}, headers=headers)
            assert dns.status_code == 200
            dns_events = [json.loads(line) for line in dns.text.splitlines() if line.strip()]
            assert any(event.get("type") == "line" and event.get("line") == "DNS-1" for event in dns_events)
            assert any(event.get("type") == "done" and event.get("ok") is True for event in dns_events)
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
        create_token = str(created_body.get("version_token") or "")
        assert create_token

        updated = client.put(
            f"/devices/switch/{created_body['id']}",
            headers=headers,
            json={
                "name": "SW2-Renamed",
                "ip": "10.0.0.11",
                "description": "edge-updated",
                "notify": False,
                "version_token": create_token,
            },
        )
        assert updated.status_code == 200
        updated_body = updated.json()
        assert updated_body["name"] == "SW2-Renamed"
        assert updated_body["notify"] is False
        updated_token = str(updated_body.get("version_token") or "")
        assert updated_token

        deleted = client.delete(
            f"/devices/switch/{created_body['id']}?version_token={updated_token}",
            headers=headers,
        )
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


def test_api_rejects_action_not_allowed_for_os(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        invalid_create = client.post(
            "/devices",
            headers=headers,
            json={
                "device_type": "server",
                "name": "SRV-LINUX",
                "ip": "10.0.1.10",
                "description": "linux host",
                "device_subtype": "Linux",
                "action_double_click": "remote_desktop",
                "notify": True,
            },
        )
        assert invalid_create.status_code == 422
        assert "non autorisee" in invalid_create.json().get("detail", "").lower()

        created = client.post(
            "/devices",
            headers=headers,
            json={
                "device_type": "server",
                "name": "SRV-WIN",
                "ip": "10.0.1.11",
                "description": "windows host",
                "device_subtype": "Windows",
                "action_double_click": "remote_desktop",
                "notify": True,
            },
        )
        assert created.status_code == 201
        created_body = created.json()
        created_token = str(created_body.get("version_token") or "")
        assert created_token

        invalid_update = client.put(
            f"/devices/server/{created_body['id']}",
            headers=headers,
            json={
                "name": "SRV-WIN",
                "ip": "10.0.1.11",
                "description": "windows host",
                "device_subtype": "Linux",
                "action_double_click": "remote_desktop",
                "notify": True,
                "version_token": created_token,
            },
        )
        assert invalid_update.status_code == 422
        assert "non autorisee" in invalid_update.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_settings_update_syncs_reverse_proxy_runtime(tmp_path: Path):
    client, _auth, settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        sync_calls = []

        def fake_sync(**kwargs):
            sync_calls.append(kwargs)
            return kwargs.get("public_url", "")

        with patch("monitoring.api.app._sync_reverse_proxy_runtime", side_effect=fake_sync):
            current = client.get("/settings", headers=headers).json()
            updated = client.put(
                "/settings",
                headers=headers,
                json={
                    **current,
                    "web_server_reverse_proxy_type": "nginx",
                    "web_server_public_url": "https://itops.domain",
                    "web_server_use_public_url": True,
                },
            )
        assert updated.status_code == 200
        assert settings_box["value"].web_server_reverse_proxy_type == "nginx"
        assert settings_box["value"].web_server_use_public_url is True
        assert settings_box["value"].web_server_public_url == "https://itops.domain"
        assert len(sync_calls) == 1
        assert sync_calls[0]["reverse_proxy"] == "nginx"
        assert sync_calls[0]["public_url"] == "https://itops.domain"
    finally:
        cleanup()


def test_api_settings_update_rejects_proxy_without_public_url(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        current = client.get("/settings", headers=headers).json()
        denied = client.put(
            "/settings",
            headers=headers,
            json={
                **current,
                "web_server_reverse_proxy_type": "caddy",
                "web_server_public_url": "",
            },
        )
        assert denied.status_code == 422
        assert "url publique obligatoire" in denied.json().get("detail", "").lower()
    finally:
        cleanup()


def test_run_subprocess_checked_accepts_zero_returncode():
    completed = SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch("monitoring.api.app.subprocess.run", return_value=completed):
        _run_subprocess_checked(["true"])


def test_enable_reverse_proxy_service_accepts_zero_returncode():
    completed = SimpleNamespace(returncode=0, stdout="", stderr="")
    with (
        patch("monitoring.api.app._is_systemctl_available", return_value=True),
        patch("monitoring.api.app._systemd_service_exists", return_value=True),
        patch("monitoring.api.app.subprocess.run", return_value=completed),
    ):
        _enable_reverse_proxy_service_if_needed("caddy")


def test_provision_local_mariadb_with_cli_accepts_zero_returncode():
    payload = SetupFinalizeRequest(
        setup_token="tok",
        admin_password="Admin#2026",
        admin_password_confirm="Admin#2026",
        hote_ecoute="0.0.0.0",
        port_ecoute=8080,
        db_host="127.0.0.1",
        db_port=3306,
        db_user="itops",
        db_password="App#2026",
        db_name="itops",
        mariadb_root_password="Root#2026",
        reverse_proxy_type="aucun",
        url_publique="",
    )
    completed = SimpleNamespace(returncode=0, stdout="", stderr="")
    with (
        patch("monitoring.api.app.shutil.which", return_value="/usr/bin/mysql"),
        patch("monitoring.api.app.subprocess.run", return_value=completed),
    ):
        ok = _provision_local_mariadb_with_cli(
            payload=payload,
            sql_statements=["SELECT 1"],
            root_password_candidates=["Root#2026", ""],
        )
    assert ok is True


def test_api_config_storage_routes(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        state = client.get("/config-storage/state", headers=headers)
        assert state.status_code == 200
        assert state.json()["mode"] == "local"
        assert state.json()["can_open_backup_folder"] is True

        with patch("monitoring.api.app.open_path_with_default_app", lambda _path: None):
            open_local = client.post("/config-storage/open-local-folder", headers=headers)
            assert open_local.status_code == 200
            assert "configuration" in open_local.json()["message"].lower()

            open_backup = client.post("/config-storage/open-backup-folder", headers=headers)
            assert open_backup.status_code == 200
            assert "sauvegarde" in open_backup.json()["message"].lower()

        sync_now = client.post("/config-storage/sync-now", headers=headers)
        assert sync_now.status_code == 200
        assert "sauvegarde terminee" in sync_now.json()["message"].lower()
    finally:
        cleanup()


def test_api_config_files_import_and_download(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        backup_root = tmp_path / "switch_configs"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_file = backup_root / "switch_SW1_10.0.0.1.cfg"
        backup_file.write_text("running-config backup", encoding="utf-8")

        downloaded = client.get(
            "/config-files/latest-download",
            params={
                "device_type": "switch",
                "device_name": "SW1",
                "device_ip": "10.0.0.1",
            },
            headers=headers,
        )
        assert downloaded.status_code == 200
        assert b"running-config backup" in downloaded.content

        local_versions_root = tmp_path / "config_versions"
        with (
            patch.object(client.app.state.services.config_storage, "local_versions_root_dir", return_value=local_versions_root),
            patch.object(client.app.state.services.device_types._config_storage, "local_versions_root_dir", return_value=local_versions_root),
        ):
            imported = client.post(
                "/config-files/import",
                json={
                    "device_type": "switch",
                    "device_name": "SW1",
                    "filename": "candidate.cfg",
                    "content_base64": base64.b64encode(b"hostname SW1").decode("ascii"),
                    "detail": "test import",
                },
                headers=headers,
            )
            assert imported.status_code == 200

            listed = client.get(
                "/config-files",
                params={
                    "device_type_label": "Switch",
                    "device_name": "SW1",
                },
                headers=headers,
            )
            assert listed.status_code == 200
            rows = listed.json()
            assert rows
            assert any("Switch_SW1" in row.get("name", "") for row in rows)

            devices = client.get("/devices", headers=headers)
            assert devices.status_code == 200
            by_name = {row.get("name"): row for row in devices.json()}
            assert by_name["SW1"]["has_saved_config"] is True
            switch_type = next((row for row in client.get("/device-types", headers=headers).json() if row.get("code") == "switch"), None)
            assert switch_type is not None
            switch_type_token = str(switch_type.get("version_token") or "")
            assert switch_type_token

            updated_type = client.put(
                "/device-types/switch",
                headers=headers,
                json={
                    "label": "Switch",
                    "monitoring_enabled": True,
                    "config_backups_enabled": False,
                    "version_token": switch_type_token,
                },
            )
            assert updated_type.status_code == 200
            assert updated_type.json()["config_backups_enabled"] is False

            listed_after_disable = client.get(
                "/config-files",
                params={
                    "device_type_label": "Switch",
                    "device_name": "SW1",
                },
                headers=headers,
            )
            assert listed_after_disable.status_code == 200
            assert listed_after_disable.json() == []
    finally:
        cleanup()


def test_api_monitoring_snapshot_and_commands(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        snapshot = client.get("/monitoring/snapshot", headers=headers)
        assert snapshot.status_code == 200
        body = snapshot.json()
        assert body["summary"]["total"] == 2
        assert sorted(body["summary"]["monitored_types"]) == ["server", "switch"]
        assert "server" in body["devices"]
        types_by_code = {str(item.get("type_code")): item for item in body.get("types", [])}
        assert types_by_code["switch"]["config_backups_enabled"] is True
        assert types_by_code["server"]["config_backups_enabled"] is False

        start = client.post("/monitoring/start/server", headers=headers)
        assert start.status_code == 200

        summary = client.get("/monitoring/summary", headers=headers)
        assert summary.status_code == 200
        assert "server" in summary.json()["running_types"]

        stop = client.post("/monitoring/stop/server", headers=headers)
        assert stop.status_code == 200
        summary_after_stop = client.get("/monitoring/summary", headers=headers)
        assert "server" not in summary_after_stop.json()["running_types"]

        start_all = client.post("/monitoring/start-all", headers=headers)
        assert start_all.status_code == 200
        running_all = client.get("/monitoring/summary", headers=headers).json()
        assert running_all["running_all"] is True

        stop_all = client.post("/monitoring/stop-all", headers=headers)
        assert stop_all.status_code == 200
        stopped = client.get("/monitoring/summary", headers=headers).json()
        assert stopped["running_any"] is False
    finally:
        cleanup()


def test_api_monitoring_commands_notify_shared_model_observers(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    notifications = []
    try:
        client.app.state.services.model.add_observer(lambda: notifications.append("changed"))
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        start = client.post("/monitoring/start/server", headers=headers)
        assert start.status_code == 200

        stop = client.post("/monitoring/stop/server", headers=headers)
        assert stop.status_code == 200

        assert len(notifications) >= 2
    finally:
        cleanup()


def test_api_monitoring_websocket_stream_requires_token_and_streams_snapshot(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        token = login.json()["access_token"]

        try:
            with client.websocket_connect("/monitoring/ws") as websocket:
                websocket.receive_json()
            assert False, "WebSocket connection without token should fail."
        except Exception:
            pass

        with client.websocket_connect(f"/monitoring/ws?token={token}&interval_ms=250") as websocket:
            payload = websocket.receive_json()
            assert payload["event"] == "monitoring.snapshot"
            assert payload["data"]["summary"]["total"] == 2
            assert sorted(payload["data"]["summary"]["monitored_types"]) == ["server", "switch"]
    finally:
        cleanup()


def test_api_monitoring_websocket_streams_runtime_changes(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        with client.websocket_connect(f"/monitoring/ws?token={token}&interval_ms=250") as websocket:
            initial = websocket.receive_json()
            assert initial["data"]["summary"]["running_any"] is False

            worker = threading.Thread(
                target=lambda: client.post("/monitoring/start/server", headers=headers),
                daemon=True,
            )
            worker.start()
            updated = websocket.receive_json()
            worker.join(timeout=2.0)

            assert updated["data"]["summary"]["running_any"] is True
            assert "server" in updated["data"]["summary"]["running_types"]
    finally:
        cleanup()


def test_api_monitoring_capabilities_endpoint(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        capabilities = client.get("/monitoring/capabilities", headers=headers)
        assert capabilities.status_code == 200
        body = capabilities.json()
        assert "websocket_supported" in body
        assert body["recommended_transport"] in {"websocket", "polling"}
    finally:
        cleanup()


def test_api_device_types_crud(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        initial = client.get("/device-types", headers=headers)
        assert initial.status_code == 200
        initial_codes = {row["code"] for row in initial.json()}

        created = client.post(
            "/device-types",
            headers=headers,
            json={
                "label": "Routeur",
                "monitoring_enabled": True,
                "config_backups_enabled": False,
            },
        )
        assert created.status_code == 201
        created_body = created.json()
        assert created_body["label"] == "Routeur"
        created_code = created_body["code"]
        assert created_code not in initial_codes
        created_token = str(created_body.get("version_token") or "")
        assert created_token

        updated = client.put(
            f"/device-types/{created_code}",
            headers=headers,
            json={
                "label": "Routeur WAN",
                "monitoring_enabled": False,
                "config_backups_enabled": True,
                "version_token": created_token,
            },
        )
        assert updated.status_code == 200
        updated_body = updated.json()
        assert updated_body["label"] == "Routeur WAN"
        assert updated_body["monitoring_enabled"] is False
        assert updated_body["config_backups_enabled"] is True
        updated_token = str(updated_body.get("version_token") or "")
        assert updated_token

        deleted = client.delete(f"/device-types/{created_code}?version_token={updated_token}", headers=headers)
        assert deleted.status_code == 200

        after_delete = client.get("/device-types", headers=headers).json()
        assert all(row["code"] != created_code for row in after_delete)
    finally:
        cleanup()


def test_api_device_type_schema_can_be_updated_from_web(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        created = client.post(
            "/device-types",
            headers=headers,
            json={
                "label": "Firewall",
                "monitoring_enabled": True,
                "config_backups_enabled": False,
            },
        )
        assert created.status_code == 201
        type_code = created.json()["code"]

        schema_before = client.get(f"/device-types/{type_code}/schema", headers=headers)
        assert schema_before.status_code == 200
        assert isinstance(schema_before.json().get("fields"), list)
        assert isinstance(schema_before.json().get("actions"), list)
        schema_token = str(schema_before.json().get("version_token") or "")
        assert schema_token

        updated_schema = client.put(
            f"/device-types/{type_code}/schema",
            headers=headers,
            json={
                "fields": [
                    {
                        "field_key": "name",
                        "label": "Nom",
                        "field_kind": "text",
                        "required": True,
                        "options": "",
                        "default_value": "",
                        "sort_order": 10,
                    },
                    {
                        "field_key": "description",
                        "label": "Description",
                        "field_kind": "text",
                        "required": False,
                        "options": "",
                        "default_value": "",
                        "sort_order": 20,
                    },
                    {
                        "field_key": "type",
                        "label": "OS",
                        "field_kind": "choice",
                        "required": True,
                        "options": "Windows,Linux,Autre",
                        "default_value": "Windows",
                        "sort_order": 30,
                    },
                    {
                        "field_key": "ip",
                        "label": "IP",
                        "field_kind": "ip",
                        "required": True,
                        "options": "",
                        "default_value": "",
                        "sort_order": 40,
                    },
                    {
                        "field_key": "id_Teamviewer",
                        "label": "ID TeamViewer",
                        "field_kind": "text",
                        "required": False,
                        "options": "",
                        "default_value": "",
                        "sort_order": 50,
                    },
                    {
                        "field_key": "action_double_click",
                        "label": "Action double-clic",
                        "field_kind": "choice",
                        "required": False,
                        "options": "teamviewer",
                        "default_value": "teamviewer",
                        "sort_order": 60,
                    },
                ],
                "actions": [
                    {
                        "action_key": "teamviewer",
                        "label": "Ouvrir TeamViewer",
                        "target_kind": "builtin",
                        "target_value": "teamviewer",
                        "os_scope": "windows,linux,autre",
                        "sort_order": 10,
                        "is_default": True,
                    }
                ],
                "version_token": schema_token,
            },
        )
        assert updated_schema.status_code == 200

        schema_after = client.get(f"/device-types/{type_code}/schema", headers=headers)
        assert schema_after.status_code == 200
        fields_by_key = {str(item.get("field_key", "")): item for item in schema_after.json()["fields"]}
        assert fields_by_key["type"]["options"] == "Windows,Linux,Autre"

        actions_by_key = {str(item.get("action_key", "")): item for item in schema_after.json()["actions"]}
        assert actions_by_key["teamviewer"]["os_scope"] == "windows,linux,autre"
        assert actions_by_key["teamviewer"]["target_value"] == "teamviewer"
    finally:
        cleanup()


def test_api_device_type_schema_supports_custom_os_scopes(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        created = client.post(
            "/device-types",
            headers=headers,
            json={
                "label": "NAS",
                "monitoring_enabled": True,
                "config_backups_enabled": False,
            },
        )
        assert created.status_code == 201
        type_code = created.json()["code"]
        schema_before = client.get(f"/device-types/{type_code}/schema", headers=headers)
        assert schema_before.status_code == 200
        schema_token = str(schema_before.json().get("version_token") or "")
        assert schema_token

        updated_schema = client.put(
            f"/device-types/{type_code}/schema",
            headers=headers,
            json={
                "fields": [
                    {
                        "field_key": "name",
                        "label": "Nom",
                        "field_kind": "text",
                        "required": True,
                        "options": "",
                        "default_value": "",
                        "sort_order": 10,
                    },
                    {
                        "field_key": "description",
                        "label": "Description",
                        "field_kind": "text",
                        "required": False,
                        "options": "",
                        "default_value": "",
                        "sort_order": 20,
                    },
                    {
                        "field_key": "type",
                        "label": "OS",
                        "field_kind": "choice",
                        "required": True,
                        "options": "Windows,Linux,Firmware,Autre,DSM",
                        "default_value": "DSM",
                        "sort_order": 30,
                    },
                    {
                        "field_key": "ip",
                        "label": "IP",
                        "field_kind": "ip",
                        "required": True,
                        "options": "",
                        "default_value": "",
                        "sort_order": 40,
                    },
                    {
                        "field_key": "action_double_click",
                        "label": "Action double-clic",
                        "field_kind": "choice",
                        "required": False,
                        "options": "dsm_web,teamviewer",
                        "default_value": "dsm_web",
                        "sort_order": 50,
                    },
                ],
                "actions": [
                    {
                        "action_key": "dsm_web",
                        "label": "DSM Web",
                        "target_kind": "builtin",
                        "target_value": "web",
                        "os_scope": "dsm",
                        "sort_order": 10,
                        "is_default": True,
                    },
                    {
                        "action_key": "teamviewer",
                        "label": "TeamViewer",
                        "target_kind": "builtin",
                        "target_value": "teamviewer",
                        "os_scope": "windows",
                        "sort_order": 20,
                        "is_default": False,
                    },
                ],
                "version_token": schema_token,
            },
        )
        assert updated_schema.status_code == 200
        actions_by_key = {str(item.get("action_key", "")): item for item in updated_schema.json()["actions"]}
        assert actions_by_key["dsm_web"]["os_scope"] == "dsm"

        valid_create = client.post(
            "/devices",
            headers=headers,
            json={
                "device_type": type_code,
                "name": "NAS-01",
                "ip": "10.10.10.10",
                "description": "NAS DSM",
                "device_subtype": "DSM",
                "action_double_click": "dsm_web",
                "notify": True,
            },
        )
        assert valid_create.status_code == 201

        invalid_create = client.post(
            "/devices",
            headers=headers,
            json={
                "device_type": type_code,
                "name": "NAS-02",
                "ip": "10.10.10.11",
                "description": "NAS DSM",
                "device_subtype": "DSM",
                "action_double_click": "teamviewer",
                "notify": True,
            },
        )
        assert invalid_create.status_code == 422
        assert "non autorisee" in invalid_create.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_disabling_monitoring_purges_type_logs(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        before = client.get("/logs", params={"device_type": "server", "limit": 20}, headers=headers)
        assert before.status_code == 200
        assert len(before.json()) >= 1
        server_type = next((row for row in client.get("/device-types", headers=headers).json() if row.get("code") == "server"), None)
        assert server_type is not None
        server_token = str(server_type.get("version_token") or "")
        assert server_token

        updated = client.put(
            "/device-types/server",
            headers=headers,
            json={
                "label": "Serveur",
                "monitoring_enabled": False,
                "config_backups_enabled": False,
                "version_token": server_token,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["monitoring_enabled"] is False

        after = client.get("/logs", params={"device_type": "server", "limit": 20}, headers=headers)
        assert after.status_code == 200
        assert after.json() == []
    finally:
        cleanup()


def test_api_ui_config_reflects_shared_settings_and_serves_watermark(tmp_path: Path):
    client, _auth, settings_box, cleanup = _build_client(tmp_path)
    try:
        watermark = tmp_path / "custom_watermark.png"
        watermark.write_bytes(b"\x89PNG\r\n\x1a\nplaceholder")
        settings = settings_box["value"]
        settings.ui_theme = "dark"
        settings.watermark_image_path = str(watermark)
        settings.watermark_opacity = 0.33

        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        ui_config = client.get("/ui/config", headers=headers)
        assert ui_config.status_code == 200
        body = ui_config.json()
        assert body["ui_theme"] == "dark"
        assert body["watermark_enabled"] is True
        assert body["watermark_url"] == "/ui/watermark-image"
        assert body["theme_colors"]["app_bg"]

        watermark_response = client.get(f"/ui/watermark-image?token={token}")
        assert watermark_response.status_code == 200
        assert watermark_response.content.startswith(b"\x89PNG")

        auth_ui_config = client.get("/ui/auth-config")
        assert auth_ui_config.status_code == 200
        assert auth_ui_config.json()["watermark_url"] == "/ui/auth-watermark-image"

        auth_watermark = client.get("/ui/auth-watermark-image")
        assert auth_watermark.status_code == 200
        assert auth_watermark.content.startswith(b"\x89PNG")
    finally:
        cleanup()


def test_api_requires_authentication_for_protected_routes(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        response = client.get("/devices")
        assert response.status_code == 401
    finally:
        cleanup()


def test_api_requires_module_grant_for_monitoring_routes(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        def _deny_monitoring_module(*, subject: str, module_code: str) -> bool:
            return False

        client.app.state.services.logs.subject_has_module = _deny_monitoring_module
        response = client.get("/devices", headers=headers)
        assert response.status_code == 403
        assert "acces refuse" in response.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_admin_can_create_monitoring_only_user(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        admin_headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}
        admin_user_row = next((row for row in client.get("/admin/users", headers=admin_headers).json() if row.get("subject") == "admin"), None)
        assert admin_user_row is not None
        admin_user_token = str(admin_user_row.get("version_token") or "")
        assert admin_user_token
        admin_account_setup = client.put(
            "/admin/users/admin",
            headers=admin_headers,
            json={
                "label": "Administrateur local",
                "password": "admin-local-pass",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["admin"],
                "version_token": admin_user_token,
            },
        )
        assert admin_account_setup.status_code == 200
        login_role_manager = client.post("/auth/login", json={"username": "admin", "password": "admin-local-pass"})
        assert login_role_manager.status_code == 200
        role_headers = {"Authorization": f"Bearer {login_role_manager.json()['access_token']}"}

        role_created = client.post(
            "/admin/roles",
            headers=role_headers,
            json={
                "code": "monitoring_only",
                "label": "Monitoring only",
                "module_codes": ["monitoring"],
                "is_system": False,
                "sort_order": 90,
            },
        )
        assert role_created.status_code == 200
        assert role_created.json()["module_codes"] == ["monitoring"]

        user_created = client.post(
            "/admin/users",
            headers=admin_headers,
            json={
                "subject": "tech1",
                "label": "Technicien 1",
                "password": "tech-pass",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["monitoring_only"],
            },
        )
        assert user_created.status_code == 200
        assert user_created.json()["role_codes"] == ["monitoring_only"]

        login_user = client.post("/auth/login", json={"username": "tech1", "password": "tech-pass"})
        assert login_user.status_code == 200
        user_headers = {"Authorization": f"Bearer {login_user.json()['access_token']}"}
        modules = client.get("/auth/me/modules", headers=user_headers)
        assert modules.status_code == 200
        rows = modules.json()
        by_code = {row["code"]: row for row in rows}
        assert by_code["monitoring"]["granted"] is True
        assert by_code["admin"]["granted"] is False
        assert by_code["interventions"]["granted"] is False
    finally:
        cleanup()


def test_api_settings_require_admin_module(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        admin_headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        role_created = client.post(
            "/admin/roles",
            headers=admin_headers,
            json={
                "code": "monitoring_only_settings_test",
                "label": "Monitoring only settings test",
                "module_codes": ["monitoring"],
                "is_system": False,
                "sort_order": 95,
            },
        )
        assert role_created.status_code == 200

        user_created = client.post(
            "/admin/users",
            headers=admin_headers,
            json={
                "subject": "viewer_settings",
                "label": "Viewer settings",
                "password": "viewer-pass",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["monitoring_only_settings_test"],
            },
        )
        assert user_created.status_code == 200

        login_user = client.post("/auth/login", json={"username": "viewer_settings", "password": "viewer-pass"})
        assert login_user.status_code == 200
        user_headers = {"Authorization": f"Bearer {login_user.json()['access_token']}"}

        settings_get = client.get("/settings", headers=user_headers)
        assert settings_get.status_code == 403
        assert "acces refuse" in settings_get.json().get("detail", "").lower()

        settings_put = client.put(
            "/settings",
            headers=user_headers,
            json={**client.get("/settings", headers=admin_headers).json(), "ui_theme": "dark"},
        )
        assert settings_put.status_code == 403
        assert "acces refuse" in settings_put.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_admin_user_update_replaces_previous_role(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        admin_headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}
        admin_user_row = next((row for row in client.get("/admin/users", headers=admin_headers).json() if row.get("subject") == "admin"), None)
        assert admin_user_row is not None
        admin_user_token = str(admin_user_row.get("version_token") or "")
        assert admin_user_token
        admin_account_setup = client.put(
            "/admin/users/admin",
            headers=admin_headers,
            json={
                "label": "Administrateur local",
                "password": "admin-local-pass",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["admin"],
                "version_token": admin_user_token,
            },
        )
        assert admin_account_setup.status_code == 200
        login_role_manager = client.post("/auth/login", json={"username": "admin", "password": "admin-local-pass"})
        assert login_role_manager.status_code == 200
        role_headers = {"Authorization": f"Bearer {login_role_manager.json()['access_token']}"}

        role_admin = client.post(
            "/admin/roles",
            headers=role_headers,
            json={
                "code": "role_admin_test",
                "label": "Role Admin Test",
                "module_codes": ["monitoring", "admin"],
                "is_system": False,
                "sort_order": 90,
            },
        )
        assert role_admin.status_code == 200

        role_tech = client.post(
            "/admin/roles",
            headers=role_headers,
            json={
                "code": "role_tech_test",
                "label": "Role Tech Test",
                "module_codes": ["monitoring"],
                "is_system": False,
                "sort_order": 95,
            },
        )
        assert role_tech.status_code == 200

        user_created = client.post(
            "/admin/users",
            headers=admin_headers,
            json={
                "subject": "admin_test",
                "label": "Admin Test",
                "password": "admin-test-pass",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["role_admin_test"],
            },
        )
        assert user_created.status_code == 200
        user_payload = user_created.json()
        assert user_payload["role_codes"] == ["role_admin_test"]
        user_token = str(user_payload.get("version_token") or "")
        assert user_token

        user_updated = client.put(
            "/admin/users/admin_test",
            headers=admin_headers,
            json={
                "label": "Admin Test Renamed",
                "password": "",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["role_tech_test"],
                "version_token": user_token,
            },
        )
        assert user_updated.status_code == 200
        assert user_updated.json()["role_codes"] == ["role_tech_test"]

        users = client.get("/admin/users", headers=admin_headers)
        assert users.status_code == 200
        updated_row = next(row for row in users.json() if row["subject"] == "admin_test")
        assert updated_row["role_codes"] == ["role_tech_test"]
    finally:
        cleanup()


def test_api_admin_role_module_changes_persist(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        admin_headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}
        admin_role_row = next((row for row in client.get("/admin/roles", headers=admin_headers).json() if row.get("code") == "admin"), None)
        assert admin_role_row is not None
        admin_role_token = str(admin_role_row.get("version_token") or "")
        assert admin_role_token

        updated = client.put(
            "/admin/roles/admin",
            headers=admin_headers,
            json={
                "code": "admin",
                "label": "Administrateur",
                "module_codes": ["monitoring", "admin"],
                "is_system": True,
                "sort_order": 10,
                "version_token": admin_role_token,
            },
        )
        assert updated.status_code == 200
        assert sorted(updated.json().get("module_codes", [])) == ["admin", "monitoring"]

        listed_once = client.get("/admin/roles", headers=admin_headers)
        assert listed_once.status_code == 200
        admin_row_once = next((row for row in listed_once.json() if row.get("code") == "admin"), None)
        assert admin_row_once is not None
        assert sorted(admin_row_once.get("module_codes", [])) == ["admin", "monitoring"]

        listed_twice = client.get("/admin/roles", headers=admin_headers)
        assert listed_twice.status_code == 200
        admin_row_twice = next((row for row in listed_twice.json() if row.get("code") == "admin"), None)
        assert admin_row_twice is not None
        assert sorted(admin_row_twice.get("module_codes", [])) == ["admin", "monitoring"]
    finally:
        cleanup()


def test_api_device_update_rejects_stale_version_token(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        devices = client.get("/devices", headers=headers)
        assert devices.status_code == 200
        device = next((row for row in devices.json() if row.get("device_type") == "switch"), None)
        assert device is not None

        base_payload = {
            "name": device["name"],
            "ip": device["ip"],
            "description": device["description"],
            "id_Teamviewer": device.get("id_Teamviewer", ""),
            "device_subtype": device.get("device_subtype", ""),
            "action_double_click": device.get("action_double_click", ""),
            "web_url": device.get("web_url", ""),
            "ssh_user": device.get("ssh_user", ""),
            "custom_data": device.get("custom_data", {}),
            "notify": device.get("notify", True),
        }

        first_update = client.put(
            f"/devices/{device['device_type']}/{device['id']}",
            headers=headers,
            json={**base_payload, "description": "updated-once", "version_token": device.get("version_token", "")},
        )
        assert first_update.status_code == 200

        stale_update = client.put(
            f"/devices/{device['device_type']}/{device['id']}",
            headers=headers,
            json={**base_payload, "description": "updated-twice", "version_token": device.get("version_token", "")},
        )
        assert stale_update.status_code == 409
        assert "conflit de modification" in stale_update.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_device_update_requires_version_token(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        devices = client.get("/devices", headers=headers)
        assert devices.status_code == 200
        device = next((row for row in devices.json() if row.get("device_type") == "switch"), None)
        assert device is not None

        missing_token_update = client.put(
            f"/devices/{device['device_type']}/{device['id']}",
            headers=headers,
            json={
                "name": device["name"],
                "ip": device["ip"],
                "description": "updated-without-token",
                "id_Teamviewer": device.get("id_Teamviewer", ""),
                "device_subtype": device.get("device_subtype", ""),
                "action_double_click": device.get("action_double_click", ""),
                "web_url": device.get("web_url", ""),
                "ssh_user": device.get("ssh_user", ""),
                "custom_data": device.get("custom_data", {}),
                "notify": device.get("notify", True),
            },
        )
        assert missing_token_update.status_code == 409
        assert "token de version manquant" in missing_token_update.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_admin_role_update_rejects_stale_version_token(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        created = client.post(
            "/admin/roles",
            headers=headers,
            json={
                "code": "stale_role_test",
                "label": "Stale Role Test",
                "module_codes": ["monitoring"],
                "is_system": False,
                "sort_order": 77,
            },
        )
        assert created.status_code == 200
        first_token = created.json().get("version_token", "")
        assert first_token

        updated = client.put(
            "/admin/roles/stale_role_test",
            headers=headers,
            json={
                "code": "stale_role_test",
                "label": "Stale Role Test v2",
                "module_codes": ["monitoring", "admin"],
                "is_system": False,
                "sort_order": 77,
                "version_token": first_token,
            },
        )
        assert updated.status_code == 200

        stale = client.put(
            "/admin/roles/stale_role_test",
            headers=headers,
            json={
                "code": "stale_role_test",
                "label": "Stale Role Test v3",
                "module_codes": ["monitoring"],
                "is_system": False,
                "sort_order": 77,
                "version_token": first_token,
            },
        )
        assert stale.status_code == 409
        assert "conflit de modification" in stale.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_custom_services_no_code_crud_and_records(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        created_service = client.post(
            "/admin/custom-services",
            headers=headers,
            json={
                "label": "Imprimante",
                "child_enabled": True,
                "child_label": "Utilisateurs",
                "sort_order": 80,
                "fields": [
                    {"label": "Marque", "field_kind": "list", "required": True, "options": "HP,Canon,Epson"},
                    {"label": "Modele", "field_kind": "text", "required": True},
                    {"label": "Adresse IP", "field_kind": "ip", "required": True},
                    {"label": "Numero de serie", "field_kind": "text", "required": True},
                    {"label": "Date installation", "field_kind": "date", "required": False},
                ],
            },
        )
        assert created_service.status_code == 200
        service_payload = created_service.json()
        assert service_payload["label"] == "Imprimante"
        assert service_payload["is_active"] is True
        assert service_payload["child_enabled"] is True
        service_code = service_payload["code"]

        listed_services = client.get("/admin/custom-services", headers=headers)
        assert listed_services.status_code == 200
        assert any(row.get("code") == service_code for row in listed_services.json())

        created_record = client.post(
            f"/admin/custom-services/{service_code}/records",
            headers=headers,
            json={
                "values": {
                    "marque": "HP",
                    "modele": "LaserJet 4100",
                    "adresse_ip": "10.20.30.40",
                    "numero_de_serie": "SN12345",
                    "date_installation": "2026-04-03",
                },
                "children": [
                    {"name": "Alice Dupont", "code": "A001"},
                    {"name": "Bob Martin", "code": "B110"},
                ],
            },
        )
        assert created_record.status_code == 200
        record_payload = created_record.json()
        assert record_payload["service_code"] == service_code
        assert record_payload["values"]["marque"] == "HP"
        assert len(record_payload["children"]) == 2
        record_id = record_payload["id"]
        record_token = str(record_payload.get("version_token") or "")
        assert record_token

        listed_records = client.get(f"/admin/custom-services/{service_code}/records", headers=headers)
        assert listed_records.status_code == 200
        assert any(row.get("id") == record_id for row in listed_records.json())

        updated_record = client.put(
            f"/admin/custom-services/{service_code}/records/{record_id}",
            headers=headers,
            json={
                "values": {
                    "marque": "Canon",
                    "modele": "IR C3326",
                    "adresse_ip": "10.20.30.41",
                    "numero_de_serie": "SN12345",
                    "date_installation": "2026-04-03",
                },
                "children": [
                    {"name": "Alice Dupont", "code": "A001"},
                ],
                "version_token": record_token,
            },
        )
        assert updated_record.status_code == 200
        updated_record_payload = updated_record.json()
        assert updated_record_payload["values"]["marque"] == "Canon"
        assert len(updated_record_payload["children"]) == 1
        updated_record_token = str(updated_record_payload.get("version_token") or "")
        assert updated_record_token

        deleted_record = client.delete(
            f"/admin/custom-services/{service_code}/records/{record_id}?version_token={updated_record_token}",
            headers=headers,
        )
        assert deleted_record.status_code == 200

        service_token = str(service_payload.get("version_token") or "")
        assert service_token
        deleted_service = client.delete(
            f"/admin/custom-services/{service_code}?version_token={service_token}",
            headers=headers,
        )
        assert deleted_service.status_code == 200
    finally:
        cleanup()


def test_api_custom_service_activation_syncs_modules_and_role_catalog(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        created_service = client.post(
            "/admin/custom-services",
            headers=headers,
            json={
                "label": "Licences",
                "is_active": True,
                "child_enabled": False,
                "fields": [
                    {"label": "Reference", "field_kind": "text", "required": True},
                ],
            },
        )
        assert created_service.status_code == 200
        service_payload = created_service.json()
        service_code = str(service_payload.get("code") or "")
        assert service_code
        assert bool(service_payload.get("is_active")) is True

        admin_modules = client.get("/admin/modules", headers=headers)
        assert admin_modules.status_code == 200
        module_row = next(
            (
                row
                for row in admin_modules.json()
                if str(row.get("route_path") or "").strip().lower() == f"/#service={service_code}"
            ),
            None,
        )
        assert module_row is not None
        assert bool(module_row.get("is_active")) is True
        module_code = str(module_row.get("code") or "")
        assert module_code

        me_modules = client.get("/auth/me/modules", headers=headers)
        assert me_modules.status_code == 200
        me_row = next(
            (
                row
                for row in me_modules.json()
                if str(row.get("route_path") or "").strip().lower() == f"/#service={service_code}"
            ),
            None,
        )
        assert me_row is not None
        assert bool(me_row.get("granted")) is True
        assert bool(me_row.get("is_active")) is True

        roles = client.get("/admin/roles", headers=headers)
        assert roles.status_code == 200
        admin_role = next((row for row in roles.json() if str(row.get("code") or "").strip().lower() == "admin"), None)
        assert admin_role is not None
        assert module_code in list(admin_role.get("module_codes") or [])

        updated_service = client.put(
            f"/admin/custom-services/{service_code}",
            headers=headers,
            json={
                "code": service_code,
                "label": str(service_payload.get("label") or "Licences"),
                "is_active": False,
                "child_enabled": bool(service_payload.get("child_enabled")),
                "child_label": str(service_payload.get("child_label") or "Elements lies"),
                "sort_order": int(service_payload.get("sort_order") or 100),
                "fields": list(service_payload.get("fields") or []),
                "version_token": str(service_payload.get("version_token") or ""),
            },
        )
        assert updated_service.status_code == 200
        assert bool(updated_service.json().get("is_active")) is False

        admin_modules_after = client.get("/admin/modules", headers=headers)
        assert admin_modules_after.status_code == 200
        module_row_after = next((row for row in admin_modules_after.json() if str(row.get("code") or "") == module_code), None)
        assert module_row_after is not None
        assert bool(module_row_after.get("is_active")) is False

        me_modules_after = client.get("/auth/me/modules", headers=headers)
        assert me_modules_after.status_code == 200
        me_row_after = next((row for row in me_modules_after.json() if str(row.get("code") or "") == module_code), None)
        assert me_row_after is not None
        assert bool(me_row_after.get("granted")) is True
        assert bool(me_row_after.get("is_active")) is False
    finally:
        cleanup()


def test_api_shared_lists_crud_and_stale_tokens(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        lists_before = client.get("/admin/shared-lists", headers=headers)
        assert lists_before.status_code == 200
        system_list = next((row for row in lists_before.json() if str(row.get("code")) == "services_mairie"), None)
        assert system_list is not None
        first_token = str(system_list.get("version_token") or "")
        assert first_token

        updated = client.put(
            "/admin/shared-lists/services_mairie",
            headers=headers,
            json={
                "code": "services_mairie",
                "label": "Services de la mairie (maj)",
                "is_system": True,
                "sort_order": 10,
                "version_token": first_token,
            },
        )
        assert updated.status_code == 200
        second_token = str(updated.json().get("version_token") or "")
        assert second_token

        stale = client.put(
            "/admin/shared-lists/services_mairie",
            headers=headers,
            json={
                "code": "services_mairie",
                "label": "Services de la mairie (stale)",
                "is_system": True,
                "sort_order": 10,
                "version_token": first_token,
            },
        )
        assert stale.status_code == 409
        assert "conflit de modification" in stale.json().get("detail", "").lower()

        created_list = client.post(
            "/admin/shared-lists",
            headers=headers,
            json={
                "code": "sites",
                "label": "Sites municipaux",
                "is_system": False,
                "sort_order": 50,
            },
        )
        assert created_list.status_code == 200
        list_token = str(created_list.json().get("version_token") or "")
        assert list_token

        created_item = client.post(
            "/admin/shared-lists/sites/items",
            headers=headers,
            json={
                "code": "hotel_ville",
                "label": "Hotel de ville",
                "is_active": True,
                "sort_order": 10,
            },
        )
        assert created_item.status_code == 200
        item_payload = created_item.json()
        item_token = str(item_payload.get("version_token") or "")
        assert item_token

        deleted_item = client.delete(
            f"/admin/shared-lists/sites/items/hotel_ville?version_token={item_token}",
            headers=headers,
        )
        assert deleted_item.status_code == 200

        deleted_list = client.delete(
            f"/admin/shared-lists/sites?version_token={list_token}",
            headers=headers,
        )
        assert deleted_list.status_code == 200
    finally:
        cleanup()


def test_api_custom_service_with_shared_list_field_validates_records(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        created_service = client.post(
            "/admin/custom-services",
            headers=headers,
            json={
                "label": "Imprimante partagee",
                "child_enabled": False,
                "fields": [
                    {
                        "label": "Service mairie",
                        "field_kind": "list",
                        "required": True,
                        "list_source_kind": "shared",
                        "shared_list_code": "services_mairie",
                    },
                    {"label": "Modele", "field_kind": "text", "required": True},
                ],
            },
        )
        assert created_service.status_code == 200
        service_payload = created_service.json()
        service_code = str(service_payload.get("code") or "")
        assert service_code

        fields_by_key = {str(row.get("field_key") or ""): row for row in service_payload.get("fields", [])}
        service_field = fields_by_key.get("service_mairie")
        assert service_field is not None
        assert service_field.get("list_source_kind") == "shared"
        assert service_field.get("shared_list_code") == "services_mairie"
        assert "Ressources humaines" in str(service_field.get("options") or "")

        valid_record = client.post(
            f"/admin/custom-services/{service_code}/records",
            headers=headers,
            json={
                "values": {
                    "service_mairie": "Ressources humaines",
                    "modele": "HP LaserJet",
                },
            },
        )
        assert valid_record.status_code == 200

        invalid_record = client.post(
            f"/admin/custom-services/{service_code}/records",
            headers=headers,
            json={
                "values": {
                    "service_mairie": "Valeur inconnue",
                    "modele": "HP LaserJet",
                },
            },
        )
        assert invalid_record.status_code == 422
        assert "valeur de la liste" in invalid_record.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_custom_service_field_import_infers_column_types(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        csv_payload = (
            "Marque;Modele;Adresse IP;Date installation\n"
            "HP;LaserJet 4100;10.20.30.40;2026-04-01\n"
            "HP;OfficeJet 9010;10.20.30.41;2026-04-02\n"
            "Canon;ImageRunner C3326;10.20.30.42;2026-04-03\n"
        ).encode("utf-8")

        imported = client.post(
            "/admin/custom-services/import/fields",
            headers=headers,
            json={
                "filename": "imprimantes.csv",
                "content_base64": base64.b64encode(csv_payload).decode("ascii"),
            },
        )
        assert imported.status_code == 200
        payload = imported.json()
        assert int(payload.get("detected_rows") or 0) == 3
        assert int(payload.get("detected_columns") or 0) == 4

        fields_by_key = {str(row.get("field_key") or ""): row for row in payload.get("fields", [])}
        assert fields_by_key["marque"]["field_kind"] == "list"
        assert fields_by_key["marque"]["options"] == "HP,Canon"
        assert fields_by_key["adresse_ip"]["field_kind"] == "ip"
        assert fields_by_key["date_installation"]["field_kind"] == "date"
    finally:
        cleanup()


def test_api_shared_list_items_import_infers_codes_and_labels(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        csv_payload = (
            "Code;Libelle\n"
            "rh;Ressources humaines\n"
            "dsi;Direction des systemes d'information\n"
            "finances;Finances\n"
        ).encode("utf-8")

        imported = client.post(
            "/admin/shared-lists/services_mairie/items/import",
            headers=headers,
            json={
                "filename": "services.csv",
                "content_base64": base64.b64encode(csv_payload).decode("ascii"),
            },
        )
        assert imported.status_code == 200
        payload = imported.json()
        assert int(payload.get("detected_rows") or 0) == 3
        assert int(payload.get("detected_columns") or 0) == 2
        rows = payload.get("items", [])
        assert rows
        first = rows[0]
        assert first.get("code") == "rh"
        assert first.get("label") == "Ressources humaines"
    finally:
        cleanup()


def test_api_devices_import_preview_apply_and_export(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        csv_payload = (
            "device_type;name;ip;description;custom:site;notify\n"
            "switch;SW1 Renamed;10.0.0.1;core updated;Datacenter;1\n"
            "server;SRV2;10.0.0.22;db node;Salle B;0\n"
        ).encode("utf-8")
        encoded = base64.b64encode(csv_payload).decode("ascii")

        preview = client.post(
            "/devices/import/preview",
            headers=headers,
            json={
                "filename": "devices.csv",
                "content_base64": encoded,
            },
        )
        assert preview.status_code == 200
        preview_payload = preview.json()
        assert int(preview_payload.get("detected_rows") or 0) == 2
        assert int(preview_payload.get("detected_columns") or 0) >= 5
        assert len(preview_payload.get("rows", [])) == 2

        applied = client.post(
            "/devices/import/apply",
            headers=headers,
            json={
                "filename": "devices.csv",
                "content_base64": encoded,
                "upsert_existing": True,
            },
        )
        assert applied.status_code == 200
        apply_payload = applied.json()
        assert int(apply_payload.get("processed") or 0) == 2
        assert int(apply_payload.get("created") or 0) >= 1
        assert int(apply_payload.get("updated") or 0) >= 1

        devices = client.get("/devices", headers=headers)
        assert devices.status_code == 200
        rows = devices.json()
        updated_sw = next((row for row in rows if row.get("ip") == "10.0.0.1"), None)
        assert updated_sw is not None
        assert updated_sw.get("name") == "SW1 Renamed"

        exported = client.get("/devices/export", headers=headers)
        assert exported.status_code == 200
        assert "text/csv" in exported.headers.get("content-type", "")
        content = exported.content.decode("utf-8-sig")
        assert "device_type;name;ip;description" in content
        assert "SW1 Renamed" in content
        assert "custom:site" in content
    finally:
        cleanup()


def test_api_devices_import_supports_manual_column_mapping(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        csv_payload = (
            "TypeX;Device Name;Addr;Site;Ignored\n"
            "switch;SW-MAPPED;10.0.3.10;HQ;foo\n"
        ).encode("utf-8")
        encoded = base64.b64encode(csv_payload).decode("ascii")
        mappings = [
            {"source_column": "TypeX", "target_field": "device_type"},
            {"source_column": "Device Name", "target_field": "name"},
            {"source_column": "Addr", "target_field": "ip"},
            {"source_column": "Site", "target_field": "custom", "custom_key": "site"},
            {"source_column": "Ignored", "target_field": "__ignore__"},
        ]

        preview = client.post(
            "/devices/import/preview",
            headers=headers,
            json={
                "filename": "devices_map.csv",
                "content_base64": encoded,
                "column_mappings": mappings,
            },
        )
        assert preview.status_code == 200
        preview_payload = preview.json()
        assert len(preview_payload.get("rows", [])) == 1
        assert "TypeX" in list(preview_payload.get("source_headers") or [])
        assert int(preview_payload.get("detected_rows") or 0) == 1
        assert int(preview_payload.get("detected_columns") or 0) == 5

        applied = client.post(
            "/devices/import/apply",
            headers=headers,
            json={
                "filename": "devices_map.csv",
                "content_base64": encoded,
                "column_mappings": mappings,
                "upsert_existing": True,
            },
        )
        assert applied.status_code == 200
        payload = applied.json()
        assert int(payload.get("created") or 0) >= 1

        devices = client.get("/devices", headers=headers)
        assert devices.status_code == 200
        rows = list(devices.json() or [])
        inserted = next((row for row in rows if row.get("ip") == "10.0.3.10"), None)
        assert inserted is not None
        assert str(inserted.get("name") or "") == "SW-MAPPED"
        custom_data = dict(inserted.get("custom_data") or {})
        assert custom_data.get("site") == "HQ"
    finally:
        cleanup()


def test_api_devices_import_preview_returns_headers_even_when_no_row_is_mappable(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        csv_payload = (
            "TYPEX;NOMX;IPX\n"
            "switch;SW1;10.0.4.10\n"
        ).encode("utf-8")
        encoded = base64.b64encode(csv_payload).decode("ascii")

        preview = client.post(
            "/devices/import/preview",
            headers=headers,
            json={
                "filename": "devices_unknown_headers.csv",
                "content_base64": encoded,
            },
        )
        assert preview.status_code == 200
        payload = preview.json()
        assert isinstance(payload.get("rows"), list)
        assert len(payload.get("rows", [])) == 0
        assert list(payload.get("source_headers") or []) == ["TYPEX", "NOMX", "IPX"]
        assert int(payload.get("detected_rows") or 0) == 1
        assert int(payload.get("detected_columns") or 0) == 3
        issues = list(payload.get("issues") or [])
        assert issues
    finally:
        cleanup()


def test_api_admin_shared_list_and_service_fields_export(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        shared_export = client.get("/admin/shared-lists/services_mairie/items/export", headers=headers)
        assert shared_export.status_code == 200
        assert "text/csv" in shared_export.headers.get("content-type", "")
        shared_content = shared_export.content.decode("utf-8-sig")
        assert "code;label;is_active;sort_order" in shared_content
        assert "Ressources humaines" in shared_content

        created_service = client.post(
            "/admin/custom-services",
            headers=headers,
            json={
                "label": "Imprimantes",
                "fields": [
                    {"label": "Modele", "field_kind": "text", "required": True},
                    {"label": "Service", "field_kind": "list", "required": True, "options": "RH,DSI"},
                ],
            },
        )
        assert created_service.status_code == 200
        service_code = str(created_service.json().get("code") or "")
        assert service_code

        fields_export = client.get(f"/admin/custom-services/{service_code}/fields/export", headers=headers)
        assert fields_export.status_code == 200
        assert "text/csv" in fields_export.headers.get("content-type", "")
        fields_content = fields_export.content.decode("utf-8-sig")
        assert "field_key;label;field_kind" in fields_content
        assert "modele;Modele;text" in fields_content
    finally:
        cleanup()


def test_api_custom_service_records_import_preview_apply_and_export(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        created_service = client.post(
            "/admin/custom-services",
            headers=headers,
            json={
                "label": "Imprimantes",
                "child_enabled": False,
                "fields": [
                    {"label": "Marque", "field_kind": "list", "required": True, "options": "HP,Canon"},
                    {"label": "Modele", "field_kind": "text", "required": True},
                    {"label": "Numero de serie", "field_kind": "text", "required": False},
                ],
            },
        )
        assert created_service.status_code == 200
        service_code = str(created_service.json().get("code") or "")
        assert service_code

        csv_payload = (
            "record_id;Marque;Modele;Numero de serie\n"
            "printer_001;HP;LaserJet 4100;SN-001\n"
            ";Canon;ImageRunner C3326;SN-002\n"
        ).encode("utf-8")
        encoded = base64.b64encode(csv_payload).decode("ascii")

        preview = client.post(
            f"/admin/custom-services/{service_code}/records/import/preview",
            headers=headers,
            json={
                "filename": "imprimantes.csv",
                "content_base64": encoded,
            },
        )
        assert preview.status_code == 200
        preview_payload = preview.json()
        assert int(preview_payload.get("detected_rows") or 0) == 2
        assert int(preview_payload.get("detected_columns") or 0) == 4
        assert len(preview_payload.get("rows", [])) == 2

        applied = client.post(
            f"/admin/custom-services/{service_code}/records/import/apply",
            headers=headers,
            json={
                "filename": "imprimantes.csv",
                "content_base64": encoded,
                "upsert_existing": True,
            },
        )
        assert applied.status_code == 200
        apply_payload = applied.json()
        assert int(apply_payload.get("processed") or 0) == 2
        assert int(apply_payload.get("created") or 0) == 2
        assert int(apply_payload.get("updated") or 0) == 0

        records = client.get(f"/admin/custom-services/{service_code}/records", headers=headers)
        assert records.status_code == 200
        rows = records.json()
        assert len(rows) == 2
        printer_001 = next((row for row in rows if str(row.get("id") or "") == "printer_001"), None)
        assert printer_001 is not None
        assert printer_001.get("values", {}).get("marque") == "HP"
        assert printer_001.get("values", {}).get("modele") == "LaserJet 4100"

        exported = client.get(f"/admin/custom-services/{service_code}/records/export", headers=headers)
        assert exported.status_code == 200
        assert "text/csv" in exported.headers.get("content-type", "")
        content = exported.content.decode("utf-8-sig")
        assert "record_id;Marque;Modele" in content
        assert "printer_001;HP;LaserJet 4100" in content
    finally:
        cleanup()


def test_api_admin_user_update_with_unknown_role_returns_422(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login_admin = client.post("/auth/login", json={"username": "sa", "password": "admin-pass"})
        assert login_admin.status_code == 200
        admin_headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        user_created = client.post(
            "/admin/users",
            headers=admin_headers,
            json={
                "subject": "tech_bad_role",
                "label": "Tech Bad Role",
                "password": "tech-pass",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["technician"],
            },
        )
        assert user_created.status_code == 200
        user_token = str(user_created.json().get("version_token") or "")
        assert user_token

        updated = client.put(
            "/admin/users/tech_bad_role",
            headers=admin_headers,
            json={
                "label": "Tech Bad Role",
                "password": "",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["role_inexistant_123"],
                "version_token": user_token,
            },
        )
        assert updated.status_code == 422
        assert "role introuvable" in updated.json().get("detail", "").lower()
    finally:
        cleanup()


def test_api_login_with_admin_account_uses_admin_credentials(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "sa-pass"})
        login_sa = client.post("/auth/login", json={"username": "sa", "password": "sa-pass"})
        assert login_sa.status_code == 200
        headers_sa = {"Authorization": f"Bearer {login_sa.json()['access_token']}"}
        admin_user_row = next((row for row in client.get("/admin/users", headers=headers_sa).json() if row.get("subject") == "admin"), None)
        assert admin_user_row is not None
        admin_user_token = str(admin_user_row.get("version_token") or "")
        assert admin_user_token

        update_admin = client.put(
            "/admin/users/admin",
            headers=headers_sa,
            json={
                "label": "Administrateur local",
                "password": "admin-local-pass",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["admin"],
                "version_token": admin_user_token,
            },
        )
        assert update_admin.status_code == 200

        login_admin = client.post("/auth/login", json={"username": "admin", "password": "admin-local-pass"})
        assert login_admin.status_code == 200
        headers_admin = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}
        me_admin = client.get("/auth/me", headers=headers_admin)
        assert me_admin.status_code == 200
        assert me_admin.json()["subject"] == "admin"
    finally:
        cleanup()


def test_api_only_admin_role_can_modify_roles(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "sa-pass"})
        login_sa = client.post("/auth/login", json={"username": "sa", "password": "sa-pass"})
        assert login_sa.status_code == 200
        headers_sa = {"Authorization": f"Bearer {login_sa.json()['access_token']}"}

        role_created = client.post(
            "/admin/roles",
            headers=headers_sa,
            json={
                "code": "user_manager",
                "label": "User Manager",
                "module_codes": ["users_admin"],
                "is_system": False,
                "sort_order": 90,
            },
        )
        assert role_created.status_code == 200

        user_created = client.post(
            "/admin/users",
            headers=headers_sa,
            json={
                "subject": "manager1",
                "label": "Manager 1",
                "password": "manager-pass",
                "is_active": True,
                "must_change_password": False,
                "role_codes": ["user_manager"],
            },
        )
        assert user_created.status_code == 200

        login_manager = client.post("/auth/login", json={"username": "manager1", "password": "manager-pass"})
        assert login_manager.status_code == 200
        headers_manager = {"Authorization": f"Bearer {login_manager.json()['access_token']}"}

        roles_list = client.get("/admin/roles", headers=headers_manager)
        assert roles_list.status_code == 200

        forbidden = client.post(
            "/admin/roles",
            headers=headers_manager,
            json={
                "code": "blocked_role",
                "label": "Blocked role",
                "module_codes": ["monitoring"],
                "is_system": False,
                "sort_order": 99,
            },
        )
        assert forbidden.status_code == 403
        assert "seul le role admin" in forbidden.json().get("detail", "").lower()
    finally:
        cleanup()


def test_switch_proxy_helpers_build_and_rewrite():
    device = {"ip": "192.168.0.40", "web_url": "http://192.168.0.40"}
    base = _resolve_switch_base_url(device)
    assert _build_switch_target_url(base=base, proxy_path="", query_string="") == "http://192.168.0.40/"
    assert _build_switch_target_url(base=base, proxy_path="status", query_string="a=1") == "http://192.168.0.40/status?a=1"

    location = _rewrite_switch_proxy_location(
        location="http://192.168.0.40/login?x=1",
        base=base,
        proxy_prefix="/devices/switch/sw1/web-ui",
    )
    assert location == "/devices/switch/sw1/web-ui/login?x=1"

    cookie = _rewrite_switch_proxy_set_cookie(
        value="sid=abc; Domain=192.168.0.40; Path=/; HttpOnly",
        proxy_prefix="/devices/switch/sw1/web-ui",
    )
    assert "Domain=" not in cookie
    assert "Path=/devices/switch/sw1/web-ui/" in cookie
    cookie_scoped = _rewrite_switch_proxy_set_cookie(
        value='sid=abc; Path="/wcn"; HttpOnly',
        proxy_prefix="/devices/switch/sw1/web-ui",
    )
    assert "Path=/devices/switch/sw1/web-ui/" in cookie_scoped
    cookie_non_session_scoped = _rewrite_switch_proxy_set_cookie(
        value='prefs=abc; Path="/wcn"; HttpOnly',
        proxy_prefix="/devices/switch/sw1/web-ui",
    )
    assert "Path=/devices/switch/sw1/web-ui/" in cookie_non_session_scoped

    refresh = _rewrite_switch_proxy_refresh(
        value="0; url=/web/device/login?lang=0",
        base=base,
        proxy_prefix="/devices/switch/sw1/web-ui",
    )
    assert refresh == "0; url=/devices/switch/sw1/web-ui/web/device/login?lang=0"


def test_switch_proxy_fallback_paths_for_legacy_device_xml():
    assert _build_switch_proxy_fallback_paths("csced39dd/device/dictionarylist.xml") == [
        "csced39dd/hpe/device/dictionarylist.xml",
        "hpe/device/dictionarylist.xml",
    ]
    assert _build_switch_proxy_fallback_paths("csced39dd/device/labeldb.xml") == [
        "csced39dd/hpe/device/labeldb.xml",
        "hpe/device/labeldb.xml",
    ]
    assert _build_switch_proxy_fallback_paths("device/dictionarylist.xml") == [
        "hpe/device/dictionarylist.xml",
    ]
    assert _build_switch_proxy_fallback_paths("csced39dd/english/dictionary1.xml") == [
        "csced39dd/hpe/english/dictionary1.xml",
        "hpe/english/dictionary1.xml",
    ]
    assert _build_switch_proxy_fallback_paths("csced39dd/js/out/pages1.js") == [
        "csced39dd/hpe/js/out/pages1.js",
        "hpe/js/out/pages1.js",
    ]
    assert _build_switch_proxy_fallback_paths("csced39dd/setup/dashboard.htm") == [
        "csced39dd/hpe/setup/dashboard.htm",
        "hpe/setup/dashboard.htm",
    ]
    assert _build_switch_proxy_fallback_paths("status") == []


def test_switch_proxy_rewrites_absolute_html_urls_for_same_switch_host():
    base = _resolve_switch_base_url({"ip": "192.168.0.40", "web_url": "http://192.168.0.40"})
    html_in = (
        '<html><body>'
        '<form action="http://192.168.0.40/login.cgi" method="post"></form>'
        '<a href="http://192.168.0.40/status?x=1">status</a>'
        '<img src="http://10.0.0.1/other.png">'
        "</body></html>"
    ).encode("utf-8")
    html_out = _rewrite_switch_proxy_html(
        body=html_in,
        proxy_prefix="/devices/switch/sw1/web-ui",
        base=base,
    ).decode("utf-8")
    assert 'action="/devices/switch/sw1/web-ui/login.cgi"' in html_out
    assert 'href="/devices/switch/sw1/web-ui/status?x=1"' in html_out
    assert 'src="http://10.0.0.1/other.png"' in html_out
    assert 'data-itops-switch-proxy-runtime="1"' in html_out
    assert 'XMLHttpRequest.prototype.open' in html_out
    assert "HTMLFormElement.prototype.submit" in html_out
    assert "legacy switch firmware POST flows (password validation)." in html_out
    assert "input = rewriteUrl(input.url);" in html_out
    assert "var currentHref = window.location.href;" in html_out
    assert "new URL(value, currentHref)" in html_out
    assert 'parsedPath.startsWith(PROXY_PREFIX + "/")' in html_out


def test_switch_proxy_rewrites_javascript_root_paths_and_absolute_host_urls():
    base = _resolve_switch_base_url({"ip": "192.168.0.21", "web_url": "http://192.168.0.21"})
    js_in = (
        'window.location="/web/device/login?lang=0";'
        'fetch("/htdocs/login/login.lua",{method:"POST"});'
        'var u="http://192.168.0.21/device/wcd?x=1";'
    ).encode("utf-8")
    js_out = _rewrite_switch_proxy_javascript(
        body=js_in,
        proxy_prefix="/devices/switch/2/web-ui",
        base=base,
    ).decode("utf-8")
    assert '"/devices/switch/2/web-ui/web/device/login?lang=0"' in js_out
    assert '"/devices/switch/2/web-ui/htdocs/login/login.lua"' in js_out
    assert '"/devices/switch/2/web-ui/device/wcd?x=1"' in js_out


def test_switch_proxy_prefixes_inline_html_script_root_paths():
    html_in = '<html><body><script>window.top.location="/web/device/login?lang=0";</script></body></html>'
    html_out = _prefix_switch_root_paths(text=html_in, proxy_prefix="/devices/switch/sw1/web-ui")
    assert '"/devices/switch/sw1/web-ui/web/device/login?lang=0"' in html_out


def test_switch_proxy_content_type_detection_and_normalization():
    assert _is_switch_proxy_html_response(content_type="text/html; charset=utf-8", proxy_path="") is True
    assert _is_switch_proxy_html_response(content_type="application/cgi", proxy_path="index.htm") is True
    assert _is_switch_proxy_html_response(content_type="application/octet-stream", proxy_path="file.bin") is False
    assert _is_switch_proxy_html_response(content_type="text/html", proxy_path="libs/app.js") is False

    assert (
        _normalize_switch_proxy_response_content_type(content_type="application/cgi", proxy_path="libs/app.js")
        == "application/javascript"
    )
    assert (
        _normalize_switch_proxy_response_content_type(content_type="application/cgi", proxy_path="index.htm")
        == "text/html"
    )
    assert (
        _normalize_switch_proxy_response_content_type(content_type="application/cgi", proxy_path="Web/login")
        == "text/xml"
    )


def test_switch_proxy_rewrites_xml_stylesheet_and_root_paths():
    xml_in = (
        '<?xml version="1.0" encoding="iso-8859-1"?>'
        '<?xml-stylesheet type="text/xsl" href="/xsl/xmlerror.xsl"?>'
        '<ROOT><Next href="/web/device/login?lang=0"/><Goto href="/wcn/ABC/xsl/redirect.xsl"/></ROOT>'
    ).encode("latin-1")
    xml_out = _rewrite_switch_proxy_xml(
        body=xml_in,
        proxy_prefix="/devices/switch/2/web-ui",
    ).decode("latin-1")
    assert 'href="/devices/switch/2/web-ui/xsl/xmlerror.xsl"' in xml_out
    assert "/devices/switch/2/web-ui/web/device/login?lang=0" in xml_out
    assert "/devices/switch/2/web-ui/wcn/ABC/xsl/redirect.xsl" in xml_out


def test_switch_proxy_rewrites_connected_user_session_type_for_https_proxy():
    xml_in = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<ResponseData>"
        "<ConnectedUserList type=\"section\">"
        "<Entry><userName>admin</userName><sessionType>2</sessionType><level>15</level></Entry>"
        "<Entry><userName>admin</userName><sessionType>4</sessionType><level>15</level></Entry>"
        "</ConnectedUserList>"
        "</ResponseData>"
    ).encode("utf-8")
    xml_out = _rewrite_switch_proxy_xml(
        body=xml_in,
        proxy_prefix="/devices/switch/sw1/web-ui",
        client_scheme="https",
    ).decode("utf-8")
    assert "<sessionType>2</sessionType>" not in xml_out
    assert xml_out.count("<sessionType>4</sessionType>") == 2


def test_switch_proxy_device_locator_prefers_name_and_underscores_spaces():
    locator = _build_switch_proxy_device_locator({"id": "sw26", "name": "Administration Gymnase"})
    assert locator == "Administration_Gymnase"


def test_switch_proxy_device_locator_normalizes_accents_and_symbols():
    locator = _normalize_switch_proxy_device_locator("Bâtiment A (RDC)")
    assert locator == "Batiment_A_RDC"


def test_api_switch_web_ui_proxy_works_with_query_token(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            assert method == "GET"
            assert "10.0.0.1" in str(url)
            assert "token=" not in str(url)
            req = httpx.Request(method, url)
            return httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                content=b'<html><body><a href="/status">Status</a></body></html>',
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(f"/devices/switch/sw1/web-ui?token={token}")
        assert response.status_code == 200
        assert '/devices/switch/sw1/web-ui/status' in response.text
        assert _SWITCH_PROXY_TOKEN_COOKIE in response.headers.get("set-cookie", "")
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_works_with_name_locator(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            assert method == "GET"
            assert "10.0.0.1" in str(url)
            req = httpx.Request(method, url)
            return httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                content=b'<html><body><a href="/status">Status</a></body></html>',
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(f"/devices/switch/SW1/web-ui?token={token}")
        assert response.status_code == 200
        assert '/devices/switch/SW1/web-ui/status' in response.text
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_preserves_non_standard_query_shape(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            url_text = str(url)
            assert "%7BEncryptionSetting%7D=" not in url_text
            assert url_text.endswith("%7BEncryptionSetting%7D") or url_text.endswith("{EncryptionSetting}")
            req = httpx.Request(method, url)
            return httpx.Response(
                200,
                headers={"content-type": "text/plain; charset=utf-8"},
                content=b"ok",
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(f"/devices/switch/sw1/web-ui/device/wcd?token={token}&{{EncryptionSetting}}")
        assert response.status_code == 200
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_fallbacks_legacy_device_xml_after_404(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        calls = {"count": 0}

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            calls["count"] += 1
            url_text = str(url)
            req = httpx.Request(method, url)
            if calls["count"] == 1:
                assert url_text.endswith("/csced39dd/device/dictionarylist.xml")
                return httpx.Response(
                    404,
                    headers={"content-type": "text/html"},
                    content=b"not found",
                    request=req,
                )
            assert calls["count"] == 2
            assert url_text.endswith("/csced39dd/hpe/device/dictionarylist.xml")
            return httpx.Response(
                200,
                headers={"content-type": "text/xml"},
                content=b"<root/>",
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(
                f"/devices/switch/sw1/web-ui/csced39dd/device/dictionarylist.xml?token={token}"
            )
        assert response.status_code == 200
        assert response.text == "<root/>"
        assert calls["count"] == 2
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_fallbacks_csced_hpe_path_after_404(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        calls = {"count": 0}

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            calls["count"] += 1
            url_text = str(url)
            req = httpx.Request(method, url)
            if calls["count"] == 1:
                assert url_text.endswith("/csced39dd/js/out/pages1.js")
                return httpx.Response(
                    404,
                    headers={"content-type": "text/html"},
                    content=b"not found",
                    request=req,
                )
            assert calls["count"] == 2
            assert url_text.endswith("/csced39dd/hpe/js/out/pages1.js")
            return httpx.Response(
                200,
                headers={"content-type": "application/javascript"},
                content=b"console.log('ok');",
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(
                f"/devices/switch/sw1/web-ui/csced39dd/js/out/pages1.js?token={token}"
            )
        assert response.status_code == 200
        assert response.text == "console.log('ok');"
        assert calls["count"] == 2
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_retries_get_on_request_error(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        calls = {"count": 0}

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            calls["count"] += 1
            req = httpx.Request(method, url)
            if calls["count"] == 1:
                raise httpx.ConnectTimeout("timed out", request=req)
            return httpx.Response(
                200,
                headers={"content-type": "text/plain; charset=utf-8"},
                content=b"ok",
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(f"/devices/switch/sw1/web-ui?token={token}")
        assert response.status_code == 200
        assert calls["count"] == 2
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_rewrites_refresh_header(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            req = httpx.Request(method, url)
            return httpx.Response(
                200,
                headers={
                    "content-type": "text/html; charset=utf-8",
                    "refresh": "0;url=/web/device/login?lang=0",
                },
                content=b"<html><body>refreshing</body></html>",
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(f"/devices/switch/sw1/web-ui?token={token}")
        assert response.status_code == 200
        assert response.headers.get("refresh", "") == "0; url=/devices/switch/sw1/web-ui/web/device/login?lang=0"
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_converts_permanent_redirect_to_temporary(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            req = httpx.Request(method, url)
            return httpx.Response(
                301,
                headers={"location": "/web/device/login?lang=0"},
                content=b"",
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(f"/devices/switch/sw1/web-ui?token={token}", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers.get("cache-control") == "no-store"
        assert response.headers.get("location") == "/devices/switch/sw1/web-ui/web/device/login?lang=0"
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_rewrites_html_even_with_non_html_content_type(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            req = httpx.Request(method, url)
            return httpx.Response(
                200,
                headers={"content-type": "application/cgi"},
                content=b'<html><body><a href="/web/device/login?lang=0">go</a></body></html>',
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(f"/devices/switch/sw1/web-ui/index.htm?token={token}")
        assert response.status_code == 200
        assert response.headers.get("content-type", "").lower().startswith("text/html")
        assert "/devices/switch/sw1/web-ui/web/device/login?lang=0" in response.text
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_does_not_treat_js_as_html_when_content_type_is_text_html(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            req = httpx.Request(method, url)
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=b'window.location="/web/device/login?lang=0";',
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(f"/devices/switch/sw1/web-ui/libs/MulPlatAPI.js?token={token}")
        assert response.status_code == 200
        assert response.headers.get("content-type", "").lower().startswith("application/javascript")
        assert "data-itops-switch-proxy-runtime" not in response.text
        assert "/devices/switch/sw1/web-ui/web/device/login?lang=0" in response.text
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_redirects_logout_to_login_page(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        client.post("/auth/bootstrap", json={"password": "admin-pass"})
        login = client.post("/auth/login", json={"password": "admin-pass"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        async def fake_request(self, method, url, headers=None, content=None, **kwargs):
            req = httpx.Request(method, url)
            return httpx.Response(
                200,
                headers={"content-type": "application/cgi"},
                content=b"<html><script>top.location='/'</script></html>",
                request=req,
            )

        with patch("monitoring.api.app.httpx.AsyncClient.request", new=fake_request):
            response = client.get(f"/devices/switch/sw1/web-ui/wcn/logout?uid=abc&token={token}", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers.get("location") == "/devices/switch/sw1/web-ui/web/device/login?lang=0"
        assert response.headers.get("cache-control") == "no-store"
    finally:
        cleanup()


def test_switch_proxy_legacy_redirect_url_uses_cookie_prefix():
    from fastapi import FastAPI, Request

    app = FastAPI()

    @app.get("/probe")
    def _probe(request: Request):
        return {
            "url": _build_switch_proxy_legacy_redirect_url(
                request=request,
                root="web",
                proxy_path="device/login",
            )
        }

    client = TestClient(app)
    client.cookies.set(_SWITCH_PROXY_PREFIX_COOKIE, "/devices/switch/21/web-ui")
    response = client.get("/probe?a=1")
    assert response.status_code == 200
    assert (
        response.json()["url"]
        == "/devices/switch/21/web-ui/web/device/login?a=1"
    )


def test_web_static_legacy_proxy_redirects_using_prefix_cookie(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        response = client.get(
            "/web/device/login?lang=0",
            follow_redirects=False,
            headers={"Cookie": f"{_SWITCH_PROXY_PREFIX_COOKIE}=/devices/switch/2/web-ui"},
        )
        assert response.status_code == 307
        assert response.headers.get("location") == "/devices/switch/2/web-ui/web/device/login?lang=0"
    finally:
        cleanup()


def test_web_static_legacy_proxy_redirects_xsl_using_prefix_cookie(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        response = client.get(
            "/xsl/xmlerror.xsl",
            follow_redirects=False,
            headers={"Cookie": f"{_SWITCH_PROXY_PREFIX_COOKIE}=/devices/switch/2/web-ui"},
        )
        assert response.status_code == 307
        assert response.headers.get("location") == "/devices/switch/2/web-ui/xsl/xmlerror.xsl"
    finally:
        cleanup()


def test_web_static_legacy_proxy_redirects_wcn_using_prefix_cookie(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        response = client.get(
            "/wcn/ABC/xsl/redirect.xsl",
            follow_redirects=False,
            headers={"Cookie": f"{_SWITCH_PROXY_PREFIX_COOKIE}=/devices/switch/2/web-ui"},
        )
        assert response.status_code == 307
        assert response.headers.get("location") == "/devices/switch/2/web-ui/wcn/ABC/xsl/redirect.xsl"
    finally:
        cleanup()


def test_root_redirects_to_wcn_frame_when_referer_points_to_wcn_tree(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        response = client.get(
            "/",
            follow_redirects=False,
            headers={
                "Cookie": f"{_SWITCH_PROXY_PREFIX_COOKIE}=/devices/switch/2/web-ui",
                "Referer": "https://itops.mvl/devices/switch/2/web-ui/wcn/frame/tree?uid=abc",
            },
        )
        assert response.status_code == 307
        assert response.headers.get("location") == "/devices/switch/2/web-ui/wcn/frame/.x"
    finally:
        cleanup()


def test_root_redirects_to_switch_login_when_proxy_cookie_without_matching_referer(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        response = client.get(
            "/",
            follow_redirects=False,
            headers={
                "Cookie": f"{_SWITCH_PROXY_PREFIX_COOKIE}=/devices/switch/2/web-ui",
                "Referer": "https://itops.mvl/portal",
            },
        )
        assert response.status_code == 307
        assert response.headers.get("location") == "/devices/switch/2/web-ui/web/device/login?lang=0"
    finally:
        cleanup()


def test_root_ignores_logout_referer_and_redirects_to_switch_login(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        response = client.get(
            "/",
            follow_redirects=False,
            headers={
                "Cookie": f"{_SWITCH_PROXY_PREFIX_COOKIE}=/devices/switch/2/web-ui",
                "Referer": "https://itops.mvl/devices/switch/2/web-ui/wcn/logout?uid=abc",
            },
        )
        assert response.status_code == 307
        assert response.headers.get("location") == "/devices/switch/2/web-ui/web/device/login?lang=0"
    finally:
        cleanup()


def test_api_switch_web_ui_proxy_requires_session(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        response = client.get("/devices/switch/sw1/web-ui")
        assert response.status_code == 401
    finally:
        cleanup()


def test_switch_proxy_token_query_removed_from_upstream_query():
    assert _strip_proxy_token_from_query("token=abc") == ""
    assert _strip_proxy_token_from_query("a=1&token=abc&b=2") == "a=1&b=2"
    assert _strip_proxy_token_from_query("{EncryptionSetting}") == "{EncryptionSetting}"
    assert _strip_proxy_token_from_query("{EncryptionSetting}&token=abc") == "{EncryptionSetting}"


def test_switch_proxy_rewrites_origin_and_referer_headers():
    from fastapi import FastAPI, Request

    app = FastAPI()

    @app.get("/probe")
    async def probe(request: Request):
        base = _resolve_switch_base_url({"ip": "192.168.0.40", "web_url": "http://192.168.0.40"})
        headers = _build_switch_proxy_request_headers(
            request=request,
            base=base,
            target_url="http://192.168.0.40/login.htm",
            proxy_prefix="/devices/switch/sw1/web-ui",
        )
        return headers

    client = TestClient(app)
    response = client.get(
        "/probe",
        headers={
            "Origin": "https://itops.mvl",
            "Referer": "https://itops.mvl/devices/switch/sw1/web-ui",
            "Cookie": 'foo=1; itops_switch_proxy_token=abc; itops_switch_proxy_prefix="/devices/switch/sw1/web-ui"; bar=2',
            "X-Test": "ok",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("Origin") == "http://192.168.0.40"
    assert payload.get("Referer") == "http://192.168.0.40/"
    assert payload.get("Host") == "192.168.0.40"
    assert payload.get("cookie") == "foo=1; bar=2"
    assert payload.get("x-test") == "ok"
