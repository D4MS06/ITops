from __future__ import annotations

from typing import Iterable

BASE_REQUIRED_FIELD_KEYS = ("name", "description", "type")
DEFAULT_TABLE_FIELD_KEYS = {"name", "ip", "device_login", "device_password"}


def normalize_type_schema_payload(
    *,
    fields: Iterable[dict],
    actions: Iterable[dict],
) -> tuple[list[dict], list[dict], set[str]]:
    cleaned_fields: list[dict] = []
    seen_field_keys: set[str] = set()
    for idx, field in enumerate(fields or []):
        field_key = str(field.get("field_key", "")).strip()
        label = str(field.get("label", "")).strip()
        field_kind = str(field.get("field_kind", "text")).strip().lower() or "text"
        options = str(field.get("options", "") or "")
        default_value = str(field.get("default_value", "") or "")
        required = 1 if bool(field.get("required", False)) else 0
        show_default = field_key in DEFAULT_TABLE_FIELD_KEYS
        show_in_table = 1 if bool(field.get("show_in_table", show_default)) else 0
        sort_order = int(field.get("sort_order", (idx + 1) * 10) or (idx + 1) * 10)

        if not field_key or not label:
            continue
        if field_key in seen_field_keys:
            raise ValueError(f"Champ duplique: {field_key}")
        seen_field_keys.add(field_key)
        cleaned_fields.append(
            {
                "field_key": field_key,
                "label": label,
                "field_kind": field_kind,
                "required": required,
                "options": options,
                "default_value": default_value,
                "show_in_table": show_in_table,
                "sort_order": sort_order,
            }
        )

    cleaned_actions: list[dict] = []
    seen_action_keys: set[str] = set()
    default_seen = False
    for idx, action in enumerate(actions or []):
        action_key = str(action.get("action_key", "")).strip().lower()
        label = str(action.get("label", "")).strip()
        target_kind = str(action.get("target_kind", "builtin")).strip().lower() or "builtin"
        target_value = str(action.get("target_value", "") or "")
        os_scope = str(action.get("os_scope", "") or "")
        sort_order = int(action.get("sort_order", (idx + 1) * 10) or (idx + 1) * 10)
        is_default = bool(action.get("is_default", False))

        if not action_key or not label:
            continue
        if action_key in seen_action_keys:
            raise ValueError(f"Action dupliquee: {action_key}")
        if is_default and default_seen:
            is_default = False
        if is_default:
            default_seen = True
        seen_action_keys.add(action_key)
        cleaned_actions.append(
            {
                "action_key": action_key,
                "label": label,
                "target_kind": target_kind,
                "target_value": target_value,
                "os_scope": os_scope,
                "sort_order": sort_order,
                "is_default": 1 if is_default else 0,
            }
        )

    return cleaned_fields, cleaned_actions, seen_field_keys


def ensure_required_schema_fields(*, seen_field_keys: set[str], monitoring_enabled: bool) -> None:
    required = list(BASE_REQUIRED_FIELD_KEYS)
    if monitoring_enabled:
        required.append("ip")
    missing_required = [key for key in required if key not in seen_field_keys]
    if missing_required:
        raise ValueError("Champs obligatoires manquants dans le schema: " + ", ".join(missing_required))
