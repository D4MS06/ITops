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
) -> dict[str, Any]:
    """Build a portable, secret-free configuration report and consistency checks."""
    services_list = [dict(item or {}) for item in services]
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
                    "values": _safe_values(row.get("values")),
                }
                for row in records
            ],
            "unknown_record_fields": unknown_fields,
            "missing_required_values": missing_required,
        })

    report_relations: list[dict[str, Any]] = []
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
        report_relations.append({**row, "impact": relation_impacts.get(relation_id, {}), "invalid_entities": invalid_entities})

    demo_records = [
        {"service_code": service["code"], "record_id": record["id"]}
        for service in report_services
        for record in service["records"]
        if str(record.get("id") or "").startswith("demo_")
    ]
    return {
        "format": "itops-custom-services-diagnostic-v1",
        "safety": "Les mots de passe, identifiants techniques, tokens et contenu du coffre sont masques ou absents.",
        "summary": {
            "service_count": len(report_services),
            "record_count": sum(item["record_count"] for item in report_services),
            "relation_count": len(report_relations),
            "demo_record_count": len(demo_records),
            "issue_count": len(issues),
        },
        "services": report_services,
        "relations": report_relations,
        "demo_records": demo_records,
        "issues": issues,
    }
