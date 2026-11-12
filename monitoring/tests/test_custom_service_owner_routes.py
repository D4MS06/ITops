import base64
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api.app import _custom_service_version_token, _register_admin_routes
from monitoring.services.module_permissions import custom_service_module_code
from monitoring.storage.mariadb_manager import CustomServiceAlreadyExistsError


class _Services:
    def __init__(self):
        self.rows = {
            "existing": {"code": "existing", "label": "Original", "owner_subject": "alice", "fields": []},
        }
        self.grants = {
            "alice": {"creator": ["read", "create", "update", "delete"]},
            "bob": {"creator": ["read", "create", "update", "delete"]},
        }
        self.admins = {"admin-user"}

    def get_custom_service(self, *, code):
        return self.rows.get(code)

    def list_custom_services(self):
        return list(self.rows.values())

    def subject_module_grants(self, *, subject, module_code):
        return self.grants.get(subject, {}) if module_code == "module_builder" else {}

    def subject_has_module_permission(self, *, subject, module_code, permission):
        return subject == "carol" and module_code == custom_service_module_code("existing") and permission == "import"

    def subject_has_auth_role(self, *, subject, role_code):
        return role_code == "admin" and subject in self.admins

    def save_custom_service(self, **values):
        code = values["code"]
        if values.get("create_only") and code in self.rows:
            raise CustomServiceAlreadyExistsError("Un module utilise deja ce code.")
        row = {**self.rows.get(code, {}), **values}
        row.pop("create_only", None)
        self.rows[code] = row
        return row

    def delete_custom_service(self, *, code):
        return int(self.rows.pop(code, None) is not None)


def _client():
    store = _Services()
    actor = {"subject": "alice"}
    app = FastAPI()
    _register_admin_routes(
        app,
        lambda: SimpleNamespace(logs=store),
        lambda: SimpleNamespace(subject=actor["subject"]),
    )
    return TestClient(app), store, actor


def test_create_rejects_existing_code_without_changing_its_definition():
    client, store, _actor = _client()

    response = client.post("/admin/custom-services", json={"code": "existing", "label": "Ecrasement"})

    assert response.status_code == 409
    assert store.rows["existing"]["label"] == "Original"


def test_creator_can_create_and_update_own_module_but_same_role_cannot():
    client, store, actor = _client()
    created = client.post("/admin/custom-services", json={"code": "new", "label": "Nouveau"})
    assert created.status_code == 200
    assert store.rows["new"]["owner_subject"] == "alice"
    token = created.json()["version_token"]

    actor["subject"] = "bob"
    denied = client.put("/admin/custom-services/new", json={"code": "new", "label": "Modifie", "version_token": token})
    assert denied.status_code == 403

    actor["subject"] = "alice"
    allowed = client.put("/admin/custom-services/new", json={"code": "new", "label": "Modifie", "version_token": token})
    assert allowed.status_code == 200
    assert store.rows["new"]["label"] == "Modifie"
    token = allowed.json()["version_token"]

    actor["subject"] = "bob"
    assert client.delete(f"/admin/custom-services/new?version_token={token}").status_code == 403
    actor["subject"] = "alice"
    assert client.delete(f"/admin/custom-services/new?version_token={token}").status_code == 200


def test_revoked_create_right_blocks_owner_and_admin_can_delete():
    client, store, actor = _client()
    token = _custom_service_version_token(store.rows["existing"])
    store.grants["alice"]["creator"].remove("create")
    assert client.post("/admin/custom-services", json={"code": "another", "label": "Autre"}).status_code == 403

    denied = client.delete(f"/admin/custom-services/existing?version_token={token}")
    assert denied.status_code == 403

    actor["subject"] = "admin-user"
    updated = client.put("/admin/custom-services/existing", json={"code": "existing", "label": "Admin", "version_token": token})
    assert updated.status_code == 200
    token = updated.json()["version_token"]
    allowed = client.delete(f"/admin/custom-services/existing?version_token={token}")
    assert allowed.status_code == 200
    assert "existing" not in store.rows


def test_module_owner_or_import_grant_can_preview_but_other_user_cannot():
    client, store, actor = _client()
    store.rows["existing"]["fields"] = [{"field_key": "nom", "label": "Nom", "field_kind": "text"}]
    payload = {
        "filename": "fiches.csv",
        "content_base64": base64.b64encode(b"Nom\nAlice\n").decode("ascii"),
    }

    allowed = client.post("/admin/custom-services/existing/records/import/preview", json=payload)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["source_headers"] == ["Nom"]

    unmapped = client.post("/admin/custom-services/existing/records/import/preview", json={
        "filename": "fiches.csv",
        "content_base64": base64.b64encode(b"Colonne inconnue\nAlice\n").decode("ascii"),
        "column_mappings": [{"source_column": "Colonne inconnue", "target_field": "__ignore__"}],
    })
    assert unmapped.status_code == 200, unmapped.text
    assert unmapped.json()["rows"] == []
    assert unmapped.json()["source_headers"] == ["Colonne inconnue"]

    actor["subject"] = "carol"
    assert client.post("/admin/custom-services/existing/records/import/preview", json=payload).status_code == 200

    actor["subject"] = "bob"
    denied = client.post("/admin/custom-services/existing/records/import/preview", json=payload)
    assert denied.status_code == 403
