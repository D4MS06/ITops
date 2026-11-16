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
        self.module_grants = {"carol": {"import"}}
        self.group_codes = ["existing"]

    def get_custom_service(self, *, code):
        return self.rows.get(code)

    def list_custom_services(self):
        return list(self.rows.values())

    def subject_module_grants(self, *, subject, module_code):
        return self.grants.get(subject, {}) if module_code == "module_builder" else {}

    def subject_has_module_permission(self, *, subject, module_code, permission):
        if subject in self.admins:
            return True
        if module_code == "module_builder":
            return any(permission in values for values in self.grants.get(subject, {}).values())
        if module_code == custom_service_module_code("existing") and subject == "alice":
            return True
        return module_code == custom_service_module_code("existing") and permission in self.module_grants.get(subject, set())

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

    def custom_service_dependency_group(self, *, code):
        return self.group_codes if code == "existing" else [code]


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


def test_revoked_builder_create_blocks_new_modules_but_owner_keeps_own_definition():
    client, store, actor = _client()
    token = _custom_service_version_token(store.rows["existing"])
    store.grants["alice"]["creator"].remove("create")
    assert client.post("/admin/custom-services", json={"code": "another", "label": "Autre"}).status_code == 403

    updated = client.put("/admin/custom-services/existing", json={"code": "existing", "label": "Proprietaire", "version_token": token})
    assert updated.status_code == 200
    token = updated.json()["version_token"]

    actor["subject"] = "admin-user"
    allowed = client.delete(f"/admin/custom-services/existing?version_token={token}")
    assert allowed.status_code == 200
    assert "existing" not in store.rows


def test_role_configure_can_edit_a_definition_without_becoming_owner():
    client, store, actor = _client()
    store.module_grants["carol"].add("configure")
    actor["subject"] = "carol"
    token = _custom_service_version_token(store.rows["existing"])

    updated = client.put("/admin/custom-services/existing", json={
        "code": "existing", "label": "Configuration partagee", "version_token": token,
    })

    assert updated.status_code == 200
    assert store.rows["existing"]["owner_subject"] == "alice"
    token = updated.json()["version_token"]
    assert client.delete(f"/admin/custom-services/existing?version_token={token}").status_code == 403


def test_owner_cannot_deactivate_a_related_module_owned_by_someone_else():
    client, store, _actor = _client()
    store.rows["other"] = {"code": "other", "label": "Autre", "owner_subject": "bob", "fields": []}
    store.group_codes = ["existing", "other"]
    token = _custom_service_version_token(store.rows["existing"])

    response = client.put("/admin/custom-services/existing", json={
        "code": "existing", "label": "Original", "is_active": False, "version_token": token,
    })

    assert response.status_code == 403
    assert "tous les modules lies" in response.json()["detail"]
    assert store.rows["existing"]["label"] == "Original"


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


def test_import_required_fields_and_configuration_permissions():
    client, store, actor = _client()
    store.rows["existing"]["fields"] = [
        {"field_key": "nom", "label": "Nom", "field_kind": "text", "required": True},
        {"field_key": "code", "label": "Code", "field_kind": "text", "required": True},
    ]
    saved = []
    store.list_custom_service_records = lambda **kwargs: []
    def save_record(**kwargs):
        saved.append(kwargs)
        return {"id": "1", "values": kwargs["values"]}
    store.save_custom_service_record = save_record
    payload = {
        "filename": "fiches.csv",
        "content_base64": base64.b64encode(b"Nom\nAlice\n").decode("ascii"),
        "column_mappings": [{"source_column": "Nom", "target_field": "nom"}],
        "relaxed_validation": True,
    }
    url = "/admin/custom-services/existing/records/import/"
    preview = client.post(url + "preview", json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["missing_required_fields"] == [{"field_key": "code", "label": "Code"}]
    assert client.post(url + "apply", json=payload).status_code == 409
    assert client.post(url + "apply", json={**payload, "make_missing_required_optional": True, "confirmed_optional_field_keys": ["nom"]}).status_code == 409
    assert not saved
    assert store.rows["existing"]["fields"][1]["required"] is True

    confirmed = {**payload, "make_missing_required_optional": True, "confirmed_optional_field_keys": ["code"]}
    actor["subject"] = "carol"
    assert client.post(url + "apply", json=confirmed).status_code == 403
    assert not saved
    actor["subject"] = "alice"
    store.is_system_custom_service_code = lambda code: True
    assert client.post(url + "apply", json=confirmed).status_code == 422
    assert not saved
    store.is_system_custom_service_code = lambda code: False
    response = client.post(url + "apply", json=confirmed)
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 1
    assert saved[0]["values"]["nom"] == "Alice"
    assert store.rows["existing"]["fields"][1]["required"] is False


def test_import_ignores_required_values_on_skipped_duplicate_rows():
    client, store, _actor = _client()
    store.rows["existing"]["fields"] = [
        {"field_key": "code", "label": "Code", "required": True},
        {"field_key": "nom", "label": "Nom", "required": True},
    ]
    store.list_custom_service_records = lambda **kwargs: [{"id": "1", "values": {"code": "A", "nom": "Alice"}}]
    store.save_custom_service_record = lambda **kwargs: {"id": "2", "values": kwargs["values"]}
    payload = {
        "filename": "fiches.csv", "content_base64": base64.b64encode(b"Code,Nom\nA,\nB,Bob\n").decode("ascii"),
        "duplicate_policy": "skip", "duplicate_field_key": "code", "relaxed_validation": True,
    }
    url = "/admin/custom-services/existing/records/import/"
    preview = client.post(url + "preview", json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["missing_required_fields"] == []
    applied = client.post(url + "apply", json=payload)
    assert applied.status_code == 200, applied.text
    assert applied.json()["created"] == 1
    assert applied.json()["skipped"] == 1
