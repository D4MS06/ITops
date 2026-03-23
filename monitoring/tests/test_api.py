from pathlib import Path
import threading
import base64
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


def test_api_serves_web_application_assets(tmp_path: Path):
    client, _auth, _settings_box, cleanup = _build_client(tmp_path)
    try:
        index = client.get("/")
        assert index.status_code == 200
        assert "text/html" in index.headers["content-type"]
        assert "Network Monitoring Web" in index.text

        script = client.get("/web/app.js")
        assert script.status_code == 200
        assert "application/javascript" in script.headers["content-type"] or "text/javascript" in script.headers["content-type"]
        assert "monitoring/ws" in script.text

        favicon = client.get("/favicon.ico")
        assert favicon.status_code == 200
        assert "image/" in favicon.headers["content-type"]
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
        with patch.object(client.app.state.services.config_storage, "local_versions_root_dir", return_value=local_versions_root):
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

        updated = client.put(
            f"/device-types/{created_code}",
            headers=headers,
            json={
                "label": "Routeur WAN",
                "monitoring_enabled": False,
                "config_backups_enabled": True,
            },
        )
        assert updated.status_code == 200
        updated_body = updated.json()
        assert updated_body["label"] == "Routeur WAN"
        assert updated_body["monitoring_enabled"] is False
        assert updated_body["config_backups_enabled"] is True

        deleted = client.delete(f"/device-types/{created_code}", headers=headers)
        assert deleted.status_code == 200

        after_delete = client.get("/device-types", headers=headers).json()
        assert all(row["code"] != created_code for row in after_delete)
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
