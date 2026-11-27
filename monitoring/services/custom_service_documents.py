"""Read local documents and documents exposed through configured record relations."""

import json
import re
from collections.abc import Callable

from monitoring.services.custom_service_schema import CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS

_RESERVED_FOLDER_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{index}" for prefix in ("COM", "LPT") for index in range(1, 10)
}


def document_entries(service: dict) -> list[dict]:
    try:
        config = json.loads(service.get("treeview_config") or "{}")
    except (TypeError, ValueError):
        config = {}
    if not isinstance(config, dict):
        config = {}
    tile = service.get("tile_config") or config.get("tile") or {}
    if not isinstance(tile, dict):
        return []
    documents = tile.get("documents") or {}
    if not isinstance(documents, dict) or not documents.get("enabled"):
        return []
    entries = documents.get("entries") or []
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def document_category(field_key: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", str(field_key or "").strip().lower()).strip("_")
    return f"document_{normalized or 'attachment'}"


def document_record_label(service: dict, record: dict) -> str:
    values = record.get("values") or {}
    fields = service.get("fields") or [{"field_key": key} for key in values]
    preferred = {"label", "name", "nom", "title", "libelle", "designation", "objet"}
    fields = sorted(fields, key=lambda field: field.get("field_key") not in preferred)
    for field in fields:
        key = field.get("field_key")
        value = str(values.get(key) or "").strip()
        if field.get("show_in_list", True) and key not in CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS and value and value != record.get("id"):
            return value
    return ""


def resolve_document_folder(store, *, service: dict, record: dict, entry: dict, authorize: Callable) -> str:
    """Derive a readable folder from persisted values for every user role."""
    kind = entry.get("folder_source_kind")
    if kind == "relation" or entry.get("folder_relation_id"):
        relation = next((row for row in store.list_custom_service_relations(service_code=service["code"])
                         if str(row["id"]) == str(entry.get("folder_relation_id")) and row.get("is_active")), None)
        if not relation:
            raise ValueError("Configurez une relation active pour nommer le dossier documentaire.")
        source, target = relation["source_service_code"], relation["target_service_code"]
        linked_code = target if source == service["code"] else source
        linked = store.list_custom_service_record_relation_links(
            service_code=service["code"], record_id=record["id"], relation_id=relation["id"],
        )
        value = ""
        if linked:
            authorize(linked_code)
            linked_service = store.get_custom_service(code=linked_code)
            names = [document_record_label(linked_service or {}, row["linked_record"]) for row in linked]
            value = " - ".join(sorted(set(names) - {""}, key=str.casefold))
        label = relation.get("display_label") or "la fiche liée"
    elif kind == "record":
        value = document_record_label(service, record)
        label = "le nom de la fiche"
    else:
        key = entry.get("folder_field_key") or entry.get("field_key")
        value = str((record.get("values") or {}).get(key) or "").strip()
        label = next((field.get("label") or key for field in service.get("fields") or [] if field.get("field_key") == key), key)
    if (not value or value == record.get("id")) and entry.get("folder_fallback_kind", "record") == "record":
        value = document_record_label(service, record)
        if value:
            label = "le nom de la fiche"
    if not value or value == record.get("id"):
        raise ValueError(f"Renseignez « {label} » avant d'ajouter ou de rechercher un document.")
    folder = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip(" .")
    if not folder or folder.upper().split(".")[0] in _RESERVED_FOLDER_NAMES:
        raise ValueError(f"Le nom renseigné dans « {label} » ne permet pas de créer un dossier.")
    return folder


def validate_document_sources(store, *, service_code: str, tile_config: dict) -> None:
    documents = (tile_config or {}).get("documents") or {}
    if not isinstance(documents, dict) or not isinstance(documents.get("entries", []), list):
        raise ValueError("Configuration documentaire invalide.")
    sources = []
    for entry in documents.get("entries", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("related_sources", []), list):
            raise ValueError("Sources documentaires liées invalides.")
        if entry.get("folder_fallback_kind", "record") not in {"record", "error"}:
            raise ValueError("Choisissez le comportement lorsque la source du dossier est vide.")
        sources.extend(entry.get("related_sources", []))
    if not sources:
        return
    relations = {str(row["id"]): row for row in store.list_custom_service_relations(service_code=service_code)}
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Source documentaire liée invalide.")
        if not isinstance(source.get("field_key"), str) or not source["field_key"].strip():
            raise ValueError("Choisissez une rubrique documentaire du module lié.")
        relation = relations.get(str(source.get("relation_id") or ""))
        if not relation or not relation.get("is_active"):
            raise ValueError("Choisissez une relation enregistrée et active pour les documents liés.")
        endpoints = (relation["source_service_code"], relation["target_service_code"])
        if service_code not in endpoints:
            raise ValueError("Cette relation ne concerne pas le module.")
        code = endpoints[1] if endpoints[0] == service_code else endpoints[0]
        linked = store.get_custom_service(code=code)
        if not linked or not any(
            (entry.get("field_key") or entry.get("folder_field_key")) == source.get("field_key")
            for entry in document_entries(linked)
        ):
            raise ValueError("Choisissez une rubrique documentaire du module lié.")


def list_record_documents(
    store, *, service: dict, record_ids: list[str], field_key: str,
    can_read: Callable[[str], bool],
) -> dict[str, list[dict]]:
    """One-hop projection. Original owners, permissions and file metadata are preserved."""
    code = service["code"]
    result = {record_id: [] for record_id in record_ids}

    def files(module, owners, field):
        if not owners:
            return []
        return store.list_linked_files_for_owners(
            owner_kind="custom_service_record", owner_ids=sorted(owners),
            module_code=module, category=document_category(field), limit=10000,
        )

    for row in files(code, record_ids, field_key):
        owner = row.get("owner_id")
        if owner in result:
            result[owner].append(dict(row))
    entry = next((item for item in document_entries(service)
                  if (item.get("field_key") or item.get("folder_field_key")) == field_key), {})
    sources = entry.get("related_sources") or []
    if not isinstance(sources, list) or not sources:
        return result
    relations = {str(row["id"]): row for row in store.list_custom_service_relations(service_code=code)}
    related_ids = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        relation = relations.get(str(source.get("relation_id") or ""))
        if not relation or not relation.get("is_active"):
            continue
        endpoints = (relation["source_service_code"], relation["target_service_code"])
        if code not in endpoints:
            continue
        linked_code = endpoints[1] if endpoints[0] == code else endpoints[0]
        if not can_read(linked_code):
            continue
        linked_service = store.get_custom_service(code=linked_code)
        linked_field = str(source.get("field_key") or "")
        if not linked_service or not linked_service.get("is_active", True) or not any(
            (item.get("field_key") or item.get("folder_field_key")) == linked_field
            for item in document_entries(linked_service)
        ):
            continue
        relation_id = str(relation["id"])
        if relation_id not in related_ids:
            related_ids[relation_id] = store.related_custom_service_record_ids(
                service_code=code, record_ids=record_ids, relation=relation,
            )
        linked_ids = related_ids[relation_id]
        owners = {owner for ids in linked_ids.values() for owner in ids}
        documents = {}
        for row in files(linked_code, owners, linked_field):
            documents.setdefault(row["owner_id"], []).append(row)
        for record_id, ids in linked_ids.items():
            seen = {row["id"] for row in result[record_id]}
            for owner in ids:
                for row in documents.get(owner, []):
                    if row["id"] in seen:
                        continue
                    seen.add(row["id"])
                    result[record_id].append({
                        **row,
                        "document_source": {
                            "module_code": linked_code, "module_label": linked_service.get("label") or linked_code,
                            "record_id": owner, "relation_id": relation["id"], "field_key": linked_field,
                            "readonly": True,
                        },
                    })
    return result
