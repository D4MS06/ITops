from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api.app import _register_admin_routes
from monitoring.services.module_permissions import custom_service_module_code


@pytest.fixture
def relation_api():
    grants = set()
    writes = []
    relation = {"id": 10, "source_service_code": "copieur", "target_service_code": "utilisateurs"}

    def save_link(**kwargs):
        writes.append(("link", kwargs))
        return {"relation_id": kwargs["relation_id"]}

    def remove_link(**kwargs):
        writes.append(("unlink", kwargs))
        return 1

    def save_record(**kwargs):
        writes.append(("record", kwargs))
        return {"id": "new", "service_code": kwargs["service_code"], "values": {}}

    logs = SimpleNamespace(
        subject_has_auth_role=lambda **kwargs: False,
        replace_custom_service_relations=lambda **kwargs: writes.append(("definition", kwargs)),
        save_custom_service_relation=lambda **kwargs: writes.append(("definition", kwargs)),
        delete_custom_service_relation=lambda **kwargs: writes.append(("definition", kwargs)),
        subject_has_module_permission=lambda subject, module_code, permission: (module_code, permission) in grants,
        get_custom_service=lambda code: {"code": code, "fields": []},
        list_custom_service_relations=lambda service_code: [relation] if service_code in
        (relation["source_service_code"], relation["target_service_code"]) else [],
        save_custom_service_record_relation_link=save_link,
        delete_custom_service_record_relation_link=remove_link,
        save_custom_service_record=save_record,
    )
    app = FastAPI()
    _register_admin_routes(app, lambda: SimpleNamespace(logs=logs), lambda: SimpleNamespace(subject="tech"))
    return TestClient(app), grants, writes


@pytest.mark.parametrize("service,reverse", [("copieur", False), ("agents", True)])
def test_link_and_unlink_follow_permissions_of_open_record(relation_api, service, reverse):
    client, grants, writes = relation_api
    current, linked = custom_service_module_code("copieur"), "directory_agents"
    if reverse:
        current, linked = linked, current
    path = f"/admin/custom-services/{service}/records/r/relations/10/links"

    def post():
        return client.post(path, json={"linked_record_id": "other"})

    def delete():
        return client.delete(path + "/other")

    for insufficient in [{(current, "read"), (linked, "read")}, {(current, "update")}]:
        grants.update(insufficient)
        assert post().status_code == delete().status_code == 403
        grants.clear()
    assert not writes
    grants.update({(current, "update"), (linked, "read")})
    assert post().status_code == delete().status_code == 200
    assert [(action, args["changed_by"]) for action, args in writes] == [("link", "tech"), ("unlink", "tech")]


def test_create_with_links_checks_target_before_writing_record(relation_api):
    client, grants, writes = relation_api
    grants.add((custom_service_module_code("copieur"), "create"))
    path = "/admin/custom-services/copieur/records"
    payload = {"relation_links": {"10": ["agent"]}}
    assert client.post(path, json=payload).status_code == 403
    assert not writes
    grants.add(("directory_agents", "read"))
    assert client.post(path, json={"relation_links": {"999": ["agent"]}}).status_code == 404
    assert not writes
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    assert [action for action, _ in writes] == ["record", "link"]


def test_delegated_configure_cannot_change_relation_definitions(relation_api):
    client, grants, writes = relation_api
    grants.add((custom_service_module_code("copieur"), "configure"))
    path = "/admin/custom-services/copieur/relations"
    assert client.put(path, json={"relations": []}).status_code == 403
    assert client.post(path, json={"target_service_code": "utilisateurs"}).status_code == 403
    assert client.delete(path + "/10").status_code == 403
    assert not writes
