"""Common lookup and variable rendering for all mail templates."""

from __future__ import annotations

import re


def select_active_mail_template(rows: list[dict], *, module_code: str, task_type: str) -> dict | None:
    """Choose the default active template for one exact module and event."""
    matches = [
        row for row in rows
        if bool(row.get("is_active"))
        and str(row.get("module_code") or "").strip().lower() == module_code
        and str(row.get("task_type") or "").strip().lower() == task_type
    ]
    matches.sort(key=lambda row: (not bool(row.get("is_default")), str(row.get("code") or "")))
    return matches[0] if matches else None


def resolve_exact_mail_template(store, *, module_code: str, task_type: str, include_inactive: bool = False) -> dict | None:
    finder = getattr(store, "find_notification_template_exact", None)
    if callable(finder):
        return finder(module_code=module_code, task_type=task_type, include_inactive=include_inactive)
    lister = getattr(store, "list_notification_templates", None)
    if not callable(lister):
        return None
    rows = list(lister(limit=1000) or [])
    if include_inactive:
        matches = [row for row in rows
                   if str(row.get("module_code") or "").strip().lower() == module_code
                   and str(row.get("task_type") or "").strip().lower() == task_type]
        matches.sort(key=lambda row: (not bool(row.get("is_active")), not bool(row.get("is_default")), str(row.get("code") or "")))
        return matches[0] if matches else None
    return select_active_mail_template(rows, module_code=module_code, task_type=task_type)


def render_mail_template_text(template: str, variables: dict[str, str], *, strict: bool = False) -> str:
    """Render both legacy {key} and current {{key}} tokens."""
    values = {str(key): str(value or "") for key, value in variables.items()}

    def replace_double(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key not in values:
            if strict:
                raise ValueError(f"Variable de modèle inconnue : {key}.")
            return match.group(0)
        return values[key]

    output = re.sub(r"\{\{([^{}]+)\}\}", replace_double, str(template or ""))
    for key, value in values.items():
        output = output.replace("{" + key + "}", value)
    return output


def ensure_monitoring_mail_template(store, settings) -> None:
    """Copy the former Monitoring settings once into the shared template catalog."""
    saver = getattr(store, "save_notification_template", None)
    if not callable(saver) or not (callable(getattr(store, "list_notification_templates", None)) or callable(getattr(store, "find_notification_template_exact", None))):
        return
    if resolve_exact_mail_template(store, module_code="monitoring", task_type="monitoring:status_change", include_inactive=True):
        return
    saver(
        code="monitoring-status-change",
        label="Monitoring - changement d'état",
        module_code="monitoring",
        task_type="monitoring:status_change",
        subject_template=str(getattr(settings, "monitoring_notification_subject_template", "") or "").strip()
        or "[Monitoring] {device_type} {device_name}: {old_status} -> {new_status}",
        body_template=str(getattr(settings, "monitoring_notification_body_template", "") or "").strip()
        or "Equipement: {device_name}\nType: {device_type}\nIP: {device_ip}\nStatut: {old_status} -> {new_status}",
        is_active=True,
        is_default=True,
    )
