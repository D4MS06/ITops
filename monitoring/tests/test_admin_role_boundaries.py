from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api.app import _register_admin_routes, _register_settings_routes
from monitoring.services.module_permissions import custom_service_module_code, FOLLOWUP_NOTIFICATION_PERMISSION


class _Store:
    def __init__(self):
        self.changed = False
        self.roles = []

    def subject_has_auth_role(self, *, subject, role_code):
        return subject == "root-admin" and role_code == "admin"

    def subject_has_module(self, *, subject, module_code):
        return subject == "user-manager" and module_code in {"users_admin", "admin"}

    def list_auth_users(self):
        return [{
            "subject": "existing-admin", "label": "Admin", "is_active": True,
            "must_change_password": False, "role_codes": ["admin"],
        }]

    def get_auth_user(self, *, subject):
        return {"subject": subject, "label": subject, "password_hash": "hash"}

    def upsert_auth_user(self, **_values):
        self.changed = True

    def set_auth_user_roles(self, **_values):
        self.changed = True

    def set_auth_user_password(self, **_values):
        self.changed = True

    def delete_auth_user(self, **_values):
        self.changed = True
        return 1

    def list_auth_roles(self):
        return self.roles

    def save_auth_role(self, **values):
        self.changed = True
        self.roles.append(values)

    def list_shared_feedback_notes(self, **_values):
        return []


def _client():
    store = _Store()
    actor = {"subject": "user-manager"}
    app = FastAPI()
    _register_admin_routes(
        app, lambda: SimpleNamespace(logs=store),
        lambda: SimpleNamespace(subject=actor["subject"]),
    )
    return TestClient(app), store, actor


def test_admin_module_access_does_not_grant_admin_role_powers():
    client, store, _actor = _client()

    assert client.post("/admin/roles", json={"code": "new-role", "label": "Role"}).status_code == 403
    assert client.post("/admin/users", json={
        "subject": "new-admin", "password": "secret", "role_codes": ["admin"],
    }).status_code == 403
    assert client.delete("/admin/users/existing-admin").status_code == 403
    assert not store.changed


def test_actual_admin_role_can_manage_roles():
    client, store, actor = _client()
    actor["subject"] = "root-admin"

    response = client.post("/admin/roles", json={"code": "new-role", "label": "Role"})

    assert response.status_code == 200
    assert store.changed


def test_followup_subscription_adds_source_read_but_never_subscribes_related_modules():
    client, store, actor = _client()
    actor["subject"] = "root-admin"
    source, target = custom_service_module_code("quotes"), custom_service_module_code("orders")
    store.list_auth_modules = lambda: [
        {"code": source, "route_path": "/#service=quotes"},
        {"code": target, "route_path": "/#service=orders"},
    ]
    store.list_custom_service_relations = lambda: [
        {"source_service_code": "quotes", "target_service_code": "orders", "is_active": True},
    ]
    response = client.post("/admin/roles", json={
        "code": "followup", "label": "Suivi devis", "module_codes": [source],
        "module_permissions": {source: [FOLLOWUP_NOTIFICATION_PERMISSION]},
    })
    assert response.status_code == 200
    rights = response.json()["module_permissions"]
    assert set(rights[source]) == {"read", FOLLOWUP_NOTIFICATION_PERMISSION}
    assert rights[target] == ["read"]


def test_feedback_notes_export_registers_and_requires_the_admin_role():
    store = _Store()
    actor = {"subject": "user-manager"}
    app = FastAPI()
    session = lambda: SimpleNamespace(subject=actor["subject"])
    _register_settings_routes(app, lambda: SimpleNamespace(logs=store), session, session)
    client = TestClient(app)

    assert client.get("/admin/database/feedback-notes/export").status_code == 403
    actor["subject"] = "root-admin"
    assert client.get("/admin/database/feedback-notes/export").status_code == 200
