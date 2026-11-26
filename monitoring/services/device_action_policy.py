from __future__ import annotations

import json

from monitoring.shared.action_compat import action_allows_os, normalize_platform


def _has_field(fields: list[dict], field_key: str) -> bool:
    wanted = str(field_key or "").strip().lower()
    for field in fields or []:
        key = str(field.get("field_key", "")).strip().lower()
        if key == wanted:
            return True
    return False

def allowed_action_keys(*, fields: list[dict], actions: list[dict], device_subtype: str) -> list[str]:
    # If type schema has no OS field, keep "autre" as neutral scope.
    has_os_field = _has_field(fields, "type") or _has_field(fields, "device_subtype")
    platform = normalize_platform(device_subtype if has_os_field else "autre")
    keys: list[str] = []
    for action in actions or []:
        action_key = str(action.get("action_key", "")).strip().lower()
        if not action_key:
            continue
        if not action_allows_os(str(action.get("os_scope", "")), platform):
            continue
        keys.append(action_key)
    return keys


def validate_action_double_click(*, fields: list[dict], actions: list[dict], device_subtype: str, action_double_click: str) -> None:
    action_key = str(action_double_click or "").strip().lower()
    if not action_key:
        return
    allowed = allowed_action_keys(fields=fields, actions=actions, device_subtype=device_subtype)
    if allowed and action_key not in allowed:
        raise ValueError(
            f"Action double-clic '{action_key}' non autorisee pour l'OS '{normalize_platform(device_subtype)}'."
        )


def default_device_access(*, fields: list[dict], actions: list[dict], row: dict) -> str:
    """Resolve the same configured action as shared_remote_actions.js."""
    platform = normalize_platform(row.get("device_subtype") or row.get("type") or "")
    normalized_actions = [
        {
            **action,
            "action_key": str(action.get("action_key") or "").strip().lower(),
            "target_kind": str(action.get("target_kind") or "").strip().lower(),
            "target_value": str(action.get("target_value") or action.get("action_key") or "").strip().lower(),
        }
        for action in actions
        if action_allows_os(action.get("os_scope", ""), platform)
    ]
    available = sorted(
        (action for action in normalized_actions if action["action_key"]),
        key=lambda action: (
            int(action.get("sort_order") or 0),
            str(action.get("label") or action["action_key"]).casefold(),
        ),
    )
    os_defaults = next(
        (field.get("default_value") for field in fields
         if str(field.get("field_key") or "").strip().lower() == "action_default_by_os"),
        "",
    )
    try:
        defaults = json.loads(os_defaults or "{}")
    except (TypeError, ValueError):
        defaults = {}
    preferred = [
        row.get("action_double_click"),
        defaults.get(platform) if isinstance(defaults, dict) else "",
    ]
    selected = None
    for value in preferred:
        key = str(value or "").strip().lower()
        selected = next(
            (action for action in available if key and key in (action["action_key"], action["target_value"])),
            None,
        )
        if selected is not None:
            break
    if selected is None:
        selected = next((action for action in available if action.get("is_default")), available[0] if available else {})
    if selected.get("target_kind") == "builtin":
        return selected["target_value"]
    return ""
