from monitoring.services.password_inventory import build_password_inventory
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from monitoring.api.app import _register_admin_routes


def test_inventory_filters_modules_and_never_returns_passwords():
    visited = []
    def records(code):
        visited.append(code)
        return [{"id": "1", "values": {"name": "Fiche", "device_login": "alice", "device_password": "secret"}}]
    result = build_password_inventory(
        devices=[{"id": "d", "device_type": "switch", "name": "Switch"}],
        custom_services=[{"code": "allowed", "credentials_enabled": True}, {"code": "denied", "credentials_enabled": True}],
        can_view_devices=True, can_manage_devices=False,
        can_view=lambda code: code == "allowed",
        can_manage=lambda code: code == "allowed",
        device_credentials=lambda *_: {"login": "admin", "password": "device-secret"},
        custom_records=records, custom_password_exists=lambda *_: False,
    )
    assert visited == ["allowed"]
    assert len(result) == 4
    assert "device-secret" not in str(result) and "'secret'" not in str(result)
    assert all(not row["can_manage"] for row in result if row["kind"] == "device")
    assert next(row for row in result if row["kind"] == "custom")["can_manage"]


def test_inventory_route_checks_device_role_and_never_returns_secret():
    permissions = set()
    store = SimpleNamespace(
        list_custom_services=lambda: [],
        subject_has_module_permission=lambda **kw: kw["module_code"] == "network_equipment" and kw["permission"] in permissions,
    )
    service = SimpleNamespace(get_access_credentials=lambda **kw: {"login": "admin", "password": "hidden"} if kw["access"] == "web" else {"login": "", "password": ""})
    model = SimpleNamespace(list_devices=lambda: [{"device_type": "switch", "id": "1", "name": "Switch"}], _device_service=service)
    app = FastAPI()
    _register_admin_routes(app, lambda: SimpleNamespace(logs=store, model=model), lambda: SimpleNamespace(subject="user"))
    client = TestClient(app)
    assert client.get("/password-inventory").json() == []
    permissions.add("credentials_view")
    response = client.get("/password-inventory")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["can_manage"] is False
    assert "hidden" not in response.text
    permissions.add("credentials_manage")
    assert client.get("/password-inventory").json()[0]["can_manage"] is True
