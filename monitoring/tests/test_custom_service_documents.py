from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api.app import _register_config_routes
from monitoring.services.custom_service_documents import list_record_documents, validate_document_sources, resolve_document_folder
from monitoring.services.module_permissions import custom_service_module_code


def document_store():
    relation = {"id": 53, "is_active": True, "source_service_code": "requests", "target_service_code": "orders"}
    source = {"relation_id": "53", "field_key": "quote"}
    services = {
        "requests": {"code": "requests", "label": "Demandes", "tile_config": {"documents": {
            "enabled": True, "entries": [{"field_key": "quote", "storage_root_id": "source-root"}],
        }}},
        "orders": {"code": "orders", "label": "Commandes", "tile_config": {"documents": {
            "enabled": True, "entries": [{"field_key": "quote", "storage_root_id": "order-root",
                                        "related_sources": [source]}],
        }}},
    }
    files = [
        {"id": "local", "owner_id": "direct", "module_code": "orders", "filename": "local.pdf",
         "metadata": {"root_id": "order-root", "path": "local.pdf"}},
        {"id": "inherited", "owner_id": "request", "module_code": "requests", "filename": "received.pdf",
         "metadata": {"root_id": "source-root", "path": "received.pdf"}},
    ]
    store = SimpleNamespace(
        get_custom_service=lambda *, code: services.get(code),
        list_custom_service_relations=lambda **kwargs: [relation],
        related_custom_service_record_ids=lambda **kwargs: {
            record: ["request"] if record == "linked" else [] for record in kwargs["record_ids"]
        },
        list_linked_files_for_owners=lambda **kwargs: [
            row for row in files if row["owner_id"] in kwargs["owner_ids"] and row["module_code"] == kwargs["module_code"]
        ],
    )
    return store, services, relation, files


def test_direct_and_related_documents_keep_their_owner_and_live_metadata():
    store, services, relation, files = document_store()
    query = dict(service=services["orders"], record_ids=["linked", "direct", "empty"],
                 field_key="quote", can_read=lambda code: True)
    result = list_record_documents(store, **query)
    assert result["empty"] == []
    assert result["direct"][0]["id"] == "local"
    assert "document_source" not in result["direct"][0]
    inherited = result["linked"][0]
    assert inherited["owner_id"] == "request"
    assert inherited["metadata"]["root_id"] == "source-root"
    assert inherited["document_source"]["readonly"]
    assert inherited["document_source"]["record_id"] == "request"
    files[1]["filename"] = "replacement.pdf"
    assert list_record_documents(store, **query)["linked"][0]["filename"] == "replacement.pdf"
    relation["is_active"] = False
    assert list_record_documents(store, **query)["linked"] == []


def test_related_documents_require_source_read_access_and_do_not_recurse():
    store, services, _, _ = document_store()
    services["requests"]["tile_config"]["documents"]["entries"][0]["related_sources"] = [
        {"relation_id": "53", "field_key": "quote"},
    ]
    result = list_record_documents(store, service=services["orders"], record_ids=["linked", "direct"],
                                   field_key="quote", can_read=lambda code: False)
    assert result["linked"] == [] and len(result["direct"]) == 1
    result = list_record_documents(store, service=services["orders"], record_ids=["linked"],
                                   field_key="quote", can_read=lambda code: True)
    assert len(result["linked"]) == 1


def test_order_can_combine_its_own_quote_and_its_request_quote():
    store, services, _, files = document_store()
    files.append({"id": "additional", "owner_id": "linked", "module_code": "orders", "filename": "additional.pdf"})
    result = list_record_documents(store, service=services["orders"], record_ids=["linked"],
                                   field_key="quote", can_read=lambda code: True)
    assert [row["id"] for row in result["linked"]] == ["additional", "inherited"]


def test_multiple_document_sources_resolve_their_shared_relation_once():
    store, services, _, files = document_store()
    services["requests"]["tile_config"]["documents"]["entries"].append({"field_key": "attachment"})
    services["orders"]["tile_config"]["documents"]["entries"][0]["related_sources"].append(
        {"relation_id": "53", "field_key": "attachment"},
    )
    resolve_ids = store.related_custom_service_record_ids
    calls = []

    def counted_ids(**kwargs):
        calls.append(kwargs)
        return resolve_ids(**kwargs)

    store.related_custom_service_record_ids = counted_ids
    result = list_record_documents(store, service=services["orders"], record_ids=["linked"],
                                   field_key="quote", can_read=lambda code: True)
    assert len(calls) == 1
    assert [row["id"] for row in result["linked"]] == [files[1]["id"]]


def test_document_configuration_rejects_unknown_relations_and_categories():
    store, services, relation, _ = document_store()
    tile = services["orders"]["tile_config"]
    validate_document_sources(store, service_code="orders", tile_config=tile)
    relation["is_active"] = False
    with pytest.raises(ValueError, match="active"):
        validate_document_sources(store, service_code="orders", tile_config=tile)
    relation["is_active"] = True
    tile["documents"]["entries"][0]["related_sources"][0]["field_key"] = "missing"
    with pytest.raises(ValueError, match="rubrique"):
        validate_document_sources(store, service_code="orders", tile_config=tile)


def test_document_list_and_inventory_summary_apply_the_same_source_permissions():
    store, _, _, files = document_store()
    grants = {custom_service_module_code("orders")}
    store.subject_has_module_permission = lambda **kwargs: kwargs["module_code"] in grants
    app = FastAPI()
    _register_config_routes(app, lambda: SimpleNamespace(logs=store),
                            lambda: SimpleNamespace(subject="reader"), lambda: None)
    client = TestClient(app)
    single = "/admin/custom-services/orders/records/linked/document-links"
    batch = "/admin/custom-services/orders/records/document-links"
    assert client.get(single, params={"document_field_key": "quote"}).json() == []
    grants.add(custom_service_module_code("requests"))
    response = client.get(single, params={"document_field_key": "quote"})
    assert response.status_code == 200
    assert response.json()[0]["document_source"]["module_code"] == "requests"
    assert client.get(batch, params={"record_ids": "linked", "document_field_key": "quote"}).json()["linked"] == response.json()
    store.get_linked_file = lambda **kwargs: {**files[1], "owner_kind": "custom_service_record"}
    assert client.delete(single + "/inherited").status_code == 404
    grants.clear()
    assert client.get(single, params={"document_field_key": "quote"}).status_code == 403


def test_relation_folder_uses_supplier_names_and_never_their_record_identifiers():
    store, services, relation, _ = document_store()
    authorized = []
    store.list_custom_service_record_relation_links = lambda **kwargs: [
        {"linked_record": {"id": "opaque-z", "values": {"nom": "Xerox"}}},
        {"linked_record": {"id": "opaque-a", "values": {"nom": "Acme"}}},
    ]
    entry = {"folder_source_kind": "relation", "folder_relation_id": "53"}
    assert resolve_document_folder(
        store, service=services["orders"], record={"id": "order"}, entry=entry,
        authorize=authorized.append,
    ) == "Acme - Xerox"
    assert authorized == ["requests"]
    store.list_custom_service_record_relation_links = lambda **kwargs: []
    with pytest.raises(ValueError, match="Renseignez"):
        resolve_document_folder(store, service=services["orders"], record={"id": "order"},
                                entry=entry, authorize=authorized.append)


def test_missing_optional_supplier_uses_the_readable_request_title():
    store, services, _, _ = document_store()
    store.list_custom_service_record_relation_links = lambda **kwargs: []
    record = {"id": "opaque-id", "values": {"objet": "Demande de matériel pour le service technique"}}
    entry = {"folder_source_kind": "relation", "folder_relation_id": "53"}
    authorized = []
    assert resolve_document_folder(store, service=services["orders"], record=record, entry=entry,
                                   authorize=authorized.append) == record["values"]["objet"]
    assert authorized == []
    entry["folder_fallback_kind"] = "error"
    with pytest.raises(ValueError, match="Renseignez"):
        resolve_document_folder(store, service=services["orders"], record=record, entry=entry, authorize=authorized.append)
