import base64
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from monitoring.api.app import _register_devices_routes
from monitoring.config import settings
from monitoring.services.device_service import DeviceService
from monitoring.services.device_action_policy import default_device_access


def test_access_credentials_permissions_and_action_scope(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "CONFIG_FILE", tmp_path / "settings.json")
    service = DeviceService(object())
    grants = {"read", "credentials_view"}
    row = {"id": "1", "name": "Test", "ip": "192.0.2.1", "description": "", "notify": True, "device_type": "switch", "device_subtype": "Linux", "device_login": "ancien", "device_password": "ancien-secret"}
    fields = [{"field_key": key} for key in ("device_login", "device_password", "device_subtype")]
    actions = [{"action_key": "ssh", "target_kind": "builtin", "target_value": "ssh", "os_scope": "Linux"}]
    api = SimpleNamespace(
        model=SimpleNamespace(get_device_row=lambda *_: row, is_config_download_type=lambda *_: False, _device_service=service),
        device_types=SimpleNamespace(load_schema=lambda *_: (fields, actions)),
        auth=SimpleNamespace(verify_user_password=lambda subject, password: password == "session"),
    )
    def permission(*, api, session, permission):
        if permission not in grants:
            raise HTTPException(status_code=403, detail="Interdit")
    app = FastAPI()
    _register_devices_routes(app, lambda: api, lambda: SimpleNamespace(subject="alice"), lambda *_: None, permission)
    client = TestClient(app)
    url = "/devices/switch/1/access-credentials"
    assert client.get(url).status_code == 200
    assert "teamviewer" not in [entry["access"] for entry in client.get(url).json()["items"]]
    assert client.put(url + "/ssh", json={"login": "admin", "password": "secret"}).status_code == 403
    grants.add("credentials_manage")
    assert client.put(url + "/teamviewer", json={"login": "x"}).status_code == 422
    assert client.put(url + "/web", json={"login": "admin", "password": "secret"}).status_code == 422
    assert client.post(url + "/ssh/copy-legacy", json={"session_password": "incorrect"}).status_code == 403
    assert client.post(url + "/ssh/copy-legacy", json={"session_password": "session"}).status_code == 200
    assert client.post(url + "/ssh/copy-legacy", json={"session_password": "session"}).status_code == 409
    assert client.put(url + "/ssh", json={"login": "admin", "password": "secret"}).status_code == 200
    device = client.get("/devices/switch/1")
    assert device.json()["device_login"] == "admin"
    assert device.json()["has_device_password"] is True
    assert "secret" not in device.text
    grants.remove("credentials_view")
    assert client.get("/devices/switch/1").json()["device_login"] == ""
    grants.add("credentials_view")
    response = client.get(url)
    assert "secret" not in response.text
    assert client.post(url + "/ssh/reveal", json={"session_password": "invalid"}).status_code == 403
    assert client.post(url + "/ssh/reveal", json={"session_password": "session"}).json()["device_password"] == "secret"
    row["device_subtype"] = "Windows"
    assert client.put(url + "/ssh", json={"login": "other"}).status_code == 422
    assert client.post(url + "/ssh/reveal", json={"session_password": "session"}).status_code == 200
    grants.clear()
    assert client.get(url).status_code == 403


def test_switch_import_writes_web_credentials_and_requires_permission(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "CONFIG_FILE", tmp_path / "settings.json")
    service = DeviceService(object())
    calls = []
    grants = {"import"}
    model = SimpleNamespace(type_definitions={"switch": {}}, list_devices=lambda: [], _device_service=service,
                            add_device=lambda **kwargs: calls.append(kwargs) or "sw-1")
    fields = [{"field_key": "device_login"}, {"field_key": "device_password"}]
    api = SimpleNamespace(model=model, device_types=SimpleNamespace(load_schema=lambda *_: (fields, [])))
    def permission(*, api, session, permission):
        if permission not in grants:
            raise HTTPException(status_code=403, detail="Interdit")
    app = FastAPI()
    _register_devices_routes(app, lambda: api, lambda: SimpleNamespace(subject="alice"), lambda *_: None, permission)
    client = TestClient(app)
    payload = {"filename": "devices.csv", "content_base64": base64.b64encode(b"name,ip,device_login,device_password\nSwitch,192.0.2.1,admin,secret\n").decode(), "default_device_type": "switch"}
    assert client.post("/devices/import/apply", json=payload).status_code == 403
    assert calls == []
    grants.add("credentials_manage")
    response = client.post("/devices/import/apply", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 1
    assert calls[0]["device_login"] is None and calls[0]["device_password"] is None
    assert service.get_access_credentials(dtype="switch", device_id="sw-1", access="web") == {"login": "admin", "password": "secret"}


def test_legacy_device_password_update_requires_manage_permission():
    changes = []
    permissions = set()
    model = SimpleNamespace(get_device_row=lambda *_: {"id": "1"}, _device_service=object(),
                            update_legacy_credential_password=lambda *args: changes.append(args) or True)
    fields = [{"field_key": "device_login"}, {"field_key": "device_password"}]
    api = SimpleNamespace(model=model, device_types=SimpleNamespace(load_schema=lambda *_: (fields, [])))
    def permission(*, api, session, permission):
        if permission not in permissions:
            raise HTTPException(status_code=403, detail="Interdit")
    app = FastAPI()
    _register_devices_routes(app, lambda: api, lambda: SimpleNamespace(subject="alice"), lambda *_: None, permission)
    client = TestClient(app)
    url = "/devices/server/1/credentials/password"
    assert client.put(url, json={"password": "secret"}).status_code == 403
    permissions.add("credentials_manage")
    assert client.put(url, json={"password": ""}).status_code == 409
    assert changes == []
    assert client.put("/devices/switch/1/credentials/password", json={"password": "secret"}).status_code == 409


def test_default_credentials_follow_normalized_action_and_platform_defaults():
    fields = [{"field_key": "action_default_by_os", "default_value": '{"linux":"SECURE_SHELL"}'}]
    actions = [
        {"action_key": "WEB", "target_kind": "BUILTIN", "is_default": True, "sort_order": 1},
        {"action_key": "Secure_Shell", "target_kind": "BUILTIN", "target_value": "SSH", "os_scope": "linux"},
    ]
    assert default_device_access(fields=fields, actions=actions, row={"device_subtype": "Linux"}) == "ssh"
    assert default_device_access(fields=fields, actions=actions, row={"device_subtype": "Linux", "action_double_click": " WEB "}) == "web"
    assert default_device_access(fields=fields, actions=actions, row={"device_subtype": "Windows"}) == "web"
    assert default_device_access(fields=fields, actions=actions, row={"device_subtype": "Linux", "action_double_click": "absent"}) == "ssh"
