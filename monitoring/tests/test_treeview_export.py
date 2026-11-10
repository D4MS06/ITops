from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api.app import _register_treeview_export_routes
from monitoring.services.module_permissions import custom_service_module_code


def test_treeview_export_authorization_requires_module_export_right():
    grants = set()

    class Logs:
        def get_custom_service(self, *, code):
            return {"code": code} if code == "copieurs" else None

        def subject_has_module_permission(self, *, subject, module_code, permission):
            assert subject == "alice"
            assert permission == "export"
            return module_code in grants

    app = FastAPI()
    _register_treeview_export_routes(
        app,
        lambda: SimpleNamespace(logs=Logs()),
        lambda: SimpleNamespace(subject="alice"),
    )
    client = TestClient(app)
    endpoint = "/exports/treeview/authorize"
    assert client.get(endpoint, params={"resource_code": "copieurs"}).status_code == 403
    grants.add(custom_service_module_code("copieurs"))
    response = client.get(endpoint, params={"resource_code": "copieurs"})
    assert response.status_code == 200
    assert response.json() == {"authorized": True}
    assert client.get(endpoint, params={"resource_code": "unknown"}).status_code == 404
    assert client.get(endpoint, params={"resource_code": "utilisateurs"}).status_code == 403
    grants.add("directory_agents")
    assert client.get(endpoint, params={"resource_code": "utilisateurs"}).status_code == 200


def test_treeview_export_accepts_the_shared_device_inventory_right():
    class Logs:
        def subject_has_module_permission(self, *, subject, module_code, permission):
            return subject == "alice" and module_code == "monitoring" and permission == "export"

    app = FastAPI()
    _register_treeview_export_routes(
        app,
        lambda: SimpleNamespace(logs=Logs()),
        lambda: SimpleNamespace(subject="alice"),
    )
    response = TestClient(app).get("/exports/treeview/authorize", params={"resource_code": "devices"})

    assert response.status_code == 200
