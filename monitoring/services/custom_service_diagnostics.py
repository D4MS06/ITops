"""Read-only audit for the generic custom-service configuration."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


_SENSITIVE_KEYS = frozenset({"password", "device_password", "device_login"})
_SYSTEM_RELATION_CODES = frozenset({"utilisateurs", "services"})


def _code(value: object) -> str:
    return str(value or "").strip().lower()


def _safe_values(values: object) -> dict[str, str]:
    return {
        str(key): "[masque]" if _code(key) in _SENSITIVE_KEYS else str(value or "")
        for key, value in dict(values or {}).items()
    }


def build_custom_service_diagnostic(
    *,
    services: Iterable[dict[str, Any]],
    records_by_service: dict[str, list[dict[str, Any]]],
    auth_modules: Iterable[dict[str, Any]],
    auth_roles: Iterable[dict[str, Any]],
    relations: Iterable[dict[str, Any]],
    relation_impacts: dict[int, dict[str, Any]],
    relation_links: Iterable[dict[str, Any]] = (),
    record_histories: dict[tuple[str, str], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Build a portable, secret-free configuration and record-editing report."""
    services_list = [dict(item or {}) for item in services]
    histories_by_record = dict(record_histories or {})
    module_by_code = {_code(item.get("code")): dict(item or {}) for item in auth_modules}
    custom_codes = {_code(item.get("code")) for item in services_list}
    roles_by_module: dict[str, list[str]] = {}
    for role in auth_roles:
        role_code = _code(role.get("code"))
        for module_code in role.get("module_codes") or []:
            roles_by_module.setdefault(_code(module_code), []).append(role_code)

    issues: list[dict[str, str]] = []
    report_services: list[dict[str, Any]] = []
    for service in services_list:
        code = _code(service.get("code"))
        module_code = f"service_{code}"
        module = module_by_code.get(module_code)
        fields = [dict(field or {}) for field in service.get("fields") or []]
        raw_treeview_config = str(service.get("treeview_config") or "")
        try:
            treeview_config: object = json.loads(raw_treeview_config) if raw_treeview_config else {}
        except (TypeError, ValueError):
            treeview_config = raw_treeview_config
            issues.append({"level": "error", "scope": code, "message": "Configuration de vue et d'automatisation JSON invalide."})
        field_keys = {_code(field.get("field_key")) for field in fields}
        records = [dict(row or {}) for row in records_by_service.get(code, [])]
        unknown_fields = sorted({
            _code(key)
            for row in records
            for key in dict(row.get("values") or {})
            if _code(key) and _code(key) not in field_keys
        })
        missing_required = [
            {"record_id": str(row.get("id") or ""), "field_key": _code(field.get("field_key"))}
            for row in records
            for field in fields
            if bool(field.get("required"))
            and not str(dict(row.get("values") or {}).get(str(field.get("field_key") or "")) or "").strip()
        ]
        if module is None:
            issues.append({"level": "error", "scope": code, "message": f"Tuile portail absente : {module_code}."})
        elif not bool(module.get("is_active")):
            issues.append({"level": "warning", "scope": code, "message": "Tuile portail inactive."})
        if not roles_by_module.get(module_code):
            issues.append({"level": "warning", "scope": code, "message": "Aucun role n'a acces a cette tuile."})
        if unknown_fields:
            issues.append({"level": "warning", "scope": code, "message": f"Champs de fiches non definis : {', '.join(unknown_fields)}."})
        if missing_required:
            issues.append({"level": "warning", "scope": code, "message": f"{len(missing_required)} valeur(s) obligatoire(s) manquante(s)."})
        if str(service.get("color") or "").strip():
            issues.append({"level": "warning", "scope": code, "message": "Couleur locale obsolète : la charte des tuiles est globale."})
        report_services.append({
            "code": code,
            "label": str(service.get("label") or code),
            "is_active": bool(service.get("is_active")),
            "icon": _code(service.get("icon")),
            "definition": {
                "is_technical": bool(service.get("is_technical")),
                "credentials_enabled": bool(service.get("credentials_enabled")),
                "child_enabled": bool(service.get("child_enabled")),
                "child_label": str(service.get("child_label") or ""),
                "sort_order": int(service.get("sort_order") or 0),
                "description": str(service.get("description") or ""),
                "treeview_config": treeview_config,
                "allow_export": bool(service.get("allow_export")),
                "allow_import": bool(service.get("allow_import")),
                "created_at": str(service.get("created_at") or ""),
                "updated_at": str(service.get("updated_at") or ""),
            },
            "portal_module": module,
            "granted_role_codes": sorted(roles_by_module.get(module_code, [])),
            "fields": fields,
            "record_count": len(records),
            "records": [
                {
                    "id": str(row.get("id") or ""),
                    "sync_status": str(row.get("sync_status") or "active"),
                    "created_at": str(row.get("created_at") or ""),
                    "updated_at": str(row.get("updated_at") or ""),
                    "version_token": str(row.get("version_token") or ""),
                    "values": _safe_values(row.get("values")),
                    "history": _safe_history_events(histories_by_record.get((code, str(row.get("id") or "")), [])),
                }
                for row in records
            ],
            "unknown_record_fields": unknown_fields,
            "missing_required_values": missing_required,
        })

    report_relations: list[dict[str, Any]] = []
    links_by_relation_id: dict[int, list[dict[str, Any]]] = {}
    for link in relation_links:
        row = dict(link or {})
        relation_id = int(row.get("relation_id") or 0)
        if relation_id <= 0:
            continue
        links_by_relation_id.setdefault(relation_id, []).append({
            "id": int(row.get("id") or 0),
            "source_record_id": str(row.get("source_record_id") or ""),
            "target_record_id": str(row.get("target_record_id") or ""),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
        })
    for relation in relations:
        row = dict(relation or {})
        relation_id = int(row.get("id") or 0)
        source, target = _code(row.get("source_service_code")), _code(row.get("target_service_code"))
        invalid_entities = [
            entity for entity in (source, target)
            if entity not in custom_codes and entity not in _SYSTEM_RELATION_CODES
        ]
        if invalid_entities:
            issues.append({"level": "error", "scope": f"relation:{relation_id}", "message": f"Cible relation inconnue : {', '.join(invalid_entities)}."})
        report_relations.append({
            **row,
            "impact": relation_impacts.get(relation_id, {}),
            "links": links_by_relation_id.pop(relation_id, []),
            "invalid_entities": invalid_entities,
        })

    orphan_relation_links = [
        {"relation_id": relation_id, "links": links}
        for relation_id, links in sorted(links_by_relation_id.items())
    ]
    if orphan_relation_links:
        issues.append({
            "level": "error",
            "scope": "relation-links",
            "message": f"{sum(len(item['links']) for item in orphan_relation_links)} lien(s) referencent une relation absente.",
        })

    demo_records = [
        {"service_code": service["code"], "record_id": record["id"]}
        for service in report_services
        for record in service["records"]
        if str(record.get("id") or "").startswith("demo_")
    ]
    return {
        "format": "itops-custom-services-diagnostic-v3",
        "safety": "Les mots de passe, identifiants techniques, tokens et contenu du coffre sont masques ou absents.",
        "summary": {
            "service_count": len(report_services),
            "record_count": sum(item["record_count"] for item in report_services),
            "relation_count": len(report_relations),
            "relation_link_count": sum(len(item["links"]) for item in report_relations),
            "orphan_relation_link_count": sum(len(item["links"]) for item in orphan_relation_links),
            "demo_record_count": len(demo_records),
            "issue_count": len(issues),
            "history_event_count": sum(
                len(histories_by_record.get((service["code"], record["id"]), []))
                for service in report_services
                for record in service["records"]
            ),
        },
        "services": report_services,
        "relations": report_relations,
        "orphan_relation_links": orphan_relation_links,
        "demo_records": demo_records,
        "issues": issues,
    }


def _safe_record_snapshot(record: dict[str, Any]) -> dict[str, Any]:
    row = dict(record or {})
    return {
        "id": str(row.get("id") or ""),
        "service_code": _code(row.get("service_code")),
        "sync_status": str(row.get("sync_status") or "active"),
        "sync_source_kind": str(row.get("sync_source_kind") or ""),
        "sync_target_kind": str(row.get("sync_target_kind") or ""),
        "sync_external_id": str(row.get("sync_external_id") or ""),
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
        "values": _safe_values(row.get("values")),
        "children": [
            {
                "name": str(item.get("name") or ""),
                "code": str(item.get("code") or ""),
                "sort_order": int(item.get("sort_order") or 0),
            }
            for item in list(row.get("children") or [])
            if isinstance(item, dict)
        ],
    }


def _safe_history_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for event in events:
        row = dict(event or {})
        field_key = _code(row.get("field_key"))
        masked = field_key in _SENSITIVE_KEYS
        output.append({
            "id": int(row.get("id") or 0),
            "field_key": field_key,
            "old_value": "[masque]" if masked else str(row.get("old_value") or ""),
            "new_value": "[masque]" if masked else str(row.get("new_value") or ""),
            "changed_at": str(row.get("changed_at") or ""),
            "changed_by": str(row.get("changed_by") or ""),
            "change_source": str(row.get("change_source") or ""),
        })
    return output


def _safe_relation_snapshots(snapshots: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for snapshot in snapshots:
        row = dict(snapshot or {})
        relation = dict(row.get("relation") or {})
        links = []
        for link in list(row.get("links") or []):
            link_row = dict(link or {})
            links.append({
                "id": int(link_row.get("id") or 0),
                "relation_id": int(link_row.get("relation_id") or relation.get("id") or 0),
                "source_record_id": str(link_row.get("source_record_id") or ""),
                "target_record_id": str(link_row.get("target_record_id") or ""),
                "linked_service_code": _code(link_row.get("linked_service_code")),
                "linked_record": _safe_record_snapshot(dict(link_row.get("linked_record") or {})),
                "created_at": str(link_row.get("created_at") or ""),
                "updated_at": str(link_row.get("updated_at") or ""),
            })
        output.append({
            "relation": relation,
            "impact": dict(row.get("impact") or {}),
            "links": links,
            "read_error": str(row.get("read_error") or ""),
        })
    return output


def build_custom_service_record_conflict_diagnostic(
    *,
    service: dict[str, Any],
    record: dict[str, Any],
    server_version_token: str,
    submitted_version_token: str,
    history: Iterable[dict[str, Any]],
    relation_snapshots: Iterable[dict[str, Any]],
    linked_files: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Build the minimal, secret-free evidence needed to analyse a stale-record conflict."""
    safe_files = [
        {
            "id": str(item.get("id") or ""),
            "owner_kind": str(item.get("owner_kind") or ""),
            "owner_id": str(item.get("owner_id") or ""),
            "module_code": str(item.get("module_code") or ""),
            "category": str(item.get("category") or ""),
            "filename": str(item.get("filename") or ""),
            "stored_path": str(item.get("stored_path") or ""),
            "size_bytes": int(item.get("size_bytes") or 0),
            "sha256": str(item.get("sha256") or ""),
            "sync_status": str(item.get("sync_status") or ""),
            "sync_error": str(item.get("sync_error") or ""),
            "created_at": str(item.get("created_at") or ""),
            "updated_at": str(item.get("updated_at") or ""),
        }
        for item in linked_files
    ]
    current_token = str(server_version_token or "")
    submitted_token = str(submitted_version_token or "")
    return {
        "format": "itops-custom-service-record-conflict-debug-v1",
        "safety": "Les mots de passe et identifiants techniques sont masques. Aucun secret du coffre n'est exporte.",
        "purpose": "Diagnostic d'un conflit de modification de fiche entre le navigateur et le serveur.",
        "version_check": {
            "server_version_token": current_token,
            "submitted_version_token": submitted_token,
            "tokens_match": bool(submitted_token) and submitted_token == current_token,
            "token_payload_rule": "id, service_code, valeurs hors agents_lies/services_deduits, elements lies, created_at et updated_at",
            "ignored_derived_value_keys": ["agents_lies", "services_deduits"],
        },
        "service": {
            "code": _code(service.get("code")),
            "label": str(service.get("label") or ""),
            "fields": [dict(field or {}) for field in list(service.get("fields") or [])],
            "updated_at": str(service.get("updated_at") or ""),
        },
        "record": _safe_record_snapshot(record),
        "history": _safe_history_events(history),
        "relations": _safe_relation_snapshots(relation_snapshots),
        "linked_files": safe_files,
    }
