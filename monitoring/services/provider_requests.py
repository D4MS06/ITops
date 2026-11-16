"""Shared provider request lifecycle and the Mail module's field adapter."""

from __future__ import annotations

import re
from datetime import datetime

from monitoring.services.mail_templates import render_mail_template_text, resolve_exact_mail_template


MAIL_ACTIONS = {
    "create": "Création d'un compte mail",
    "delete": "Suppression d'un compte mail",
    "reset_password": "Réinitialisation du mot de passe",
    "add_alias": "Création d'un alias",
}


class ProviderRequestError(ValueError):
    def __init__(self, detail: str, kind: str = "invalid") -> None:
        super().__init__(detail)
        self.kind = kind


def prepare_mail_provider_request(*, store, settings, action_code: str, record_id: str = "",
                                  target_value: str = "", account_type: str = "nominatif",
                                  note: str = "", reminder_due_at: str = "", requester: str = "") -> dict:
    """Prepare a Mail request without sending it or changing a record."""
    action = str(action_code or "").strip().lower()
    if action not in MAIL_ACTIONS:
        raise ProviderRequestError("Action prestataire indisponible pour ce module.")
    records_lister = getattr(store, "list_custom_service_records", None)
    if not callable(records_lister) or not (callable(getattr(store, "find_notification_template_exact", None)) or callable(getattr(store, "list_notification_templates", None))):
        raise ProviderRequestError("Service de demandes indisponible.", "unavailable")
    records = list(records_lister(service_code="emails") or [])
    record_id = str(record_id or "").strip()
    record = next((row for row in records if str(row.get("id") or "") == record_id), None) if record_id else None
    if action != "create" and not record:
        raise ProviderRequestError("Compte mail introuvable.", "not_found")
    if action == "create" and record_id:
        raise ProviderRequestError("La création ne cible pas un compte existant.")
    try:
        target = mail_request_target(action=action, record=record, target_value=target_value)
    except ValueError as exc:
        raise ProviderRequestError(str(exc)) from exc
    if action in {"create", "add_alias"} and any(
        target == str((row.get("values") or {}).get("address") or "").strip().lower()
        or target in {part.strip().lower() for part in re.split(r"[,;\n]+", str((row.get("values") or {}).get("alias") or ""))}
        for row in records
    ):
        raise ProviderRequestError("Cette adresse ou cet alias existe déjà dans Emails.", "conflict")
    requests_lister = getattr(store, "list_provider_requests", None)
    if callable(requests_lister) and any(
        str(row.get("action_code") or "") == action
        and str(row.get("target_value") or "").lower() == target
        and str(row.get("record_id") or "") == record_id
        and str(row.get("status") or "") in {"pending", "sent", "partial"}
        for row in requests_lister(module_code="emails", record_id=record_id, limit=1000)
    ):
        raise ProviderRequestError("Une demande identique est déjà en cours.", "conflict")
    if action == "delete" and str((record.get("values") or {}).get("status") or "").strip().lower() in {"a supprimer", "supprime"}:
        raise ProviderRequestError("Ce compte est déjà en cours de suppression ou supprimé.", "conflict")
    due_at = str(reminder_due_at or "").strip() if action == "delete" else ""
    if due_at:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", due_at):
            due_at = f"{due_at} 09:00:00"
        else:
            try:
                due_at = datetime.fromisoformat(due_at.replace("T", " ")).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError as exc:
                raise ProviderRequestError("Date de rappel notification invalide.") from exc
        try:
            datetime.fromisoformat(due_at)
        except ValueError as exc:
            raise ProviderRequestError("Date de rappel invalide.") from exc
    template = resolve_exact_mail_template(store, module_code="emails", task_type=f"provider:{action}")
    if not template:
        raise ProviderRequestError(f"Configurez le modèle de demande « {MAIL_ACTIONS[action]} » avant l'envoi.", "conflict")
    try:
        recipient = normalize_email_address(str(template.get("recipient") or getattr(settings, "provider_recipient", "") or ""))
    except ValueError as exc:
        raise ProviderRequestError("Configurez une adresse prestataire dans les paramètres d'envoi ou sur le modèle.", "conflict") from exc
    address = target if action == "create" else str((record.get("values") or {}).get("address") or "").strip()
    variables = {"address": address, "account_type": str(account_type or "").strip().lower() if action == "create" else "",
                 "alias": target if action == "add_alias" else "", "note": str(note or ""),
                 "requester": str(requester or ""), "reminder_date": due_at[:10]}
    try:
        subject, body = render_provider_template(template, variables)
    except ValueError as exc:
        raise ProviderRequestError(str(exc), "conflict") from exc
    if not subject or not body or len(subject) > 255 or "\n" in subject or "\r" in subject:
        raise ProviderRequestError("Le modèle produit un objet ou un message invalide.", "conflict")
    try:
        expected, confirmed = mail_request_changes(action=action, record=record, target_value=target, account_type=str(account_type or "").strip().lower())
    except ValueError as exc:
        raise ProviderRequestError(str(exc)) from exc
    return {"module_code": "emails", "record_id": record_id, "action_code": action, "target_value": target,
            "recipient": recipient, "subject": subject, "body": body, "expected_values": expected,
            "confirmed_values": confirmed, "reminder_due_at": due_at}


def normalize_email_address(value: str) -> str:
    address = str(value or "").strip().lower()
    if len(address) > 254 or not re.fullmatch(r"[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+", address):
        raise ValueError("Adresse e-mail invalide.")
    return address


def mail_request_target(*, action: str, record: dict | None, target_value: str) -> str:
    if action not in MAIL_ACTIONS:
        raise ValueError("Type de demande inconnu.")
    if action == "create":
        if record:
            raise ValueError("La création d'un compte ne doit pas cibler une fiche existante.")
        return normalize_email_address(target_value)
    if not record:
        raise ValueError("Sélectionnez un compte mail existant.")
    values = dict(record.get("values") or {})
    if action == "add_alias":
        alias = normalize_email_address(target_value)
        existing = {item.strip().lower() for item in re.split(r"[,;\n]+", str(values.get("alias") or "")) if item.strip()}
        if alias == str(values.get("address") or "").strip().lower() or alias in existing:
            raise ValueError("Cet alias est déjà présent sur le compte.")
        return alias
    return normalize_email_address(str(values.get("address") or ""))


def mail_request_changes(*, action: str, record: dict | None, target_value: str, account_type: str = "nominatif") -> tuple[dict[str, str], dict[str, str]]:
    """Return (expected values, changes after confirmation)."""
    if action == "create":
        if account_type not in {"nominatif", "generique", "technique", "partage"}:
            raise ValueError("Type de compte mail invalide.")
        return {}, {"address": target_value, "type_compte": account_type, "status": "Actif"}
    values = dict((record or {}).get("values") or {})
    if action == "delete":
        return {"status": str(values.get("status") or "")}, {"status": "Supprime"}
    if action == "add_alias":
        current = str(values.get("alias") or "")
        aliases = [part.strip() for part in re.split(r"[,;\n]+", current) if part.strip()]
        return {"alias": current}, {"alias": ", ".join([*aliases, target_value])}
    return {}, {}


def confirmed_mail_changes(*, action: str, target_value: str, expected: dict[str, str], confirmed: dict[str, str], current: dict[str, str], accept_current: bool = False) -> dict[str, str]:
    """Validate a provider response against the latest Mail record values."""
    for key, previous in expected.items():
        if str(current.get(key) or "") != str(previous or "") and not accept_current:
            raise ValueError(f"Le champ {key} a changé depuis la demande. Vérifiez la fiche avant validation.")
    if action == "add_alias":
        if target_value.lower() == str(current.get("address") or "").strip().lower():
            raise ValueError("Cet alias est devenu l'adresse principale du compte.")
        aliases = [part.strip() for part in re.split(r"[,;\n]+", str(current.get("alias") or "")) if part.strip()]
        if target_value.lower() in {item.lower() for item in aliases}:
            return {}
        return {"alias": ", ".join([*aliases, target_value])}
    return {key: str(value) for key, value in confirmed.items() if str(current.get(key) or "") != str(value)}


def rejected_mail_changes(*, action: str, current: dict[str, str], expected: dict[str, str], original: dict[str, str]) -> dict[str, str]:
    if action != "delete":
        return {}
    if str(current.get("status") or "") != str(expected.get("status") or ""):
        raise ValueError("Le statut du compte a changé depuis la demande. Vérifiez la fiche avant de refuser.")
    return {"status": str(original.get("status") or "Actif")}


def render_provider_template(template: dict, variables: dict[str, str]) -> tuple[str, str]:
    details = str(variables.get("note") or "")
    template_variables = {**variables, "note": ""}
    body_template = str(template.get("body_template") or "")
    # Older starter templates embedded this label and token on a dedicated line.
    body_template, removed_legacy_note_lines = re.subn(
        r"(?im)^[ \t]*(?:(?:consignes|détails)\s*:\s*)?(?:\{\{\s*note\s*\}\}|\{note\})[ \t]*(?:\r?\n|$)",
        "",
        body_template,
    )
    body_template, removed_date_line = re.subn(
        r"(?im)^[ \t]*date (?:souhaitée|de rappel|prévue)[ \t]*:[ \t]*(?:\{\{\s*reminder_date\s*\}\}|\{reminder_date\})[ \t]*(?:\r?\n|$)",
        "",
        body_template,
    )
    template_variables["reminder_date"] = ""
    if removed_legacy_note_lines or removed_date_line:
        body_template = re.sub(r"(?:\r?\n){3,}", "\n\n", body_template)
    body = render_mail_template_text(body_template, template_variables, strict=True).strip()
    if details.strip():
        body = f"{body}\n\n{details}" if body else details
    return (
        render_mail_template_text(str(template.get("subject_template") or ""), template_variables, strict=True).strip(),
        body,
    )
