"""Common lookup and variable rendering for all mail templates."""

from __future__ import annotations

import re

from monitoring.services.custom_service_schema import CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS


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
    values = {str(key): "" if value is None else str(value) for key, value in variables.items()}

    def replace_token(match: re.Match[str]) -> str:
        key = (match.group(1) or match.group(2)).strip()
        if key not in values:
            if strict and match.group(1) is not None:
                raise ValueError(f"Variable de modèle inconnue : {key}.")
            return match.group(0)
        return values[key]

    return MAIL_VARIABLE.sub(replace_token, str(template or ""))


MAIL_VARIABLE = re.compile(r"\{\{([^{}]+)\}\}|\{([\w.:-]+)\}")


def _template_field_labels(service):
    return {
        field["field_key"]: field["label"] for field in service.get("fields", [])
        if field["field_key"].strip().lower() not in CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS
    }


def record_template_fields(service, prefix, label):
    return [
        {"key": f"{prefix}.{key}", "label": f"{label} · {field_label}"}
        for key, field_label in _template_field_labels(service).items()
    ]


def edited_record_mail(draft, *, recipient, subject, body, approve):
    from monitoring.services.provider_requests import normalize_email_address

    if not subject.strip() or not body.strip() or re.search(r"[\r\n]", subject) or len(body.encode()) > 65535:
        raise ValueError("Vérifiez le sujet et le texte du courrier.")
    if approve and (MAIL_VARIABLE.search(subject) or MAIL_VARIABLE.search(body)):
        raise ValueError("Une variable reste à remplacer dans le courrier.")
    address = normalize_email_address(recipient) if approve or recipient.strip() else ""
    return {"target_value": draft["target_value"], "recipient": address,
            "subject": subject, "body": body}


def render_record_preview(payload, record, service, load_linked, *, allow_empty_recipient=False):
    from monitoring.services.provider_requests import normalize_email_address

    texts = (payload.subject_template, payload.body_template, payload.recipient)
    keys = {(m.group(1) or m.group(2)).strip() for text in texts for m in MAIL_VARIABLE.finditer(text)}
    values = {"record.id": record["id"], "module.code": record["service_code"]}
    sources = {"record.fields": (_template_field_labels(service), record)}
    relation_id = None
    for key in sorted(keys - values.keys()):
        prefix, _, field = key.rpartition(".")
        if prefix not in sources:
            match = re.fullmatch(r"relation\.([1-9][0-9]{0,18})", prefix)
            if not match:
                raise ValueError(f"Variable indisponible : {key}.")
            if relation_id is not None:
                raise ValueError("Choisissez une seule relation pour ce courrier.")
            relation_id = int(match[1])
            definition, linked = load_linked(relation_id)
            sources[prefix] = (_template_field_labels(definition), linked)
        labels, source = sources[prefix]
        if field not in labels:
            raise ValueError(f"Variable indisponible : {key}.")
        value = source["values"].get(field)
        if value is None or not str(value).strip():
            raise ValueError(f"Valeur vide : {key}.")
        values[key] = value
    subject, body, recipient = (render_mail_template_text(text, values, strict=True) for text in texts)
    if not subject.strip() or re.search(r"[\r\n]", subject):
        raise ValueError("Le sujet du courrier doit être renseigné sur une seule ligne.")
    address = "" if allow_empty_recipient and not recipient.strip() else normalize_email_address(recipient)
    return {"subject": subject, "body": body, "recipient": address}


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
