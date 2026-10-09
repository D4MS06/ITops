from __future__ import annotations

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
