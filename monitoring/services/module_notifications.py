"""Resolve explicit module-followup subscriptions without widening access."""

import re

from monitoring.services.module_permissions import relation_entity_module_code
from monitoring.services.provider_requests import normalize_email_address


class ModuleNotificationBlocked(ValueError):
    """A notification must remain unsent until its routing is corrected."""


def automation_task_spec(task: dict) -> tuple[str, str, str]:
    """Read legacy task keys, including colons inside a template or recipient."""
    if task.get("trigger_field_key") != "automation":
        return "", "", ""
    match = re.fullmatch(r"[^:]*:(.*):(notify|email|create_task):([^:]*):(.*)", str(task.get("trigger_value") or ""))
    if not match:
        return "", "", ""
    template, _, kind, value = match.groups()
    return template.strip(), kind.strip().lower(), value.strip()


def module_followup_recipients(store, *, service_code: str, record_id: str) -> list[str]:
    """Resolve live RBAC subscriptions against canonical AD/manual contacts.

    No directory relation grants, owner elevation, arbitrary module values or
    global SMTP recipient list are used to choose subscribers or their address.
    """
    service = store.get_custom_service(code=service_code)
    if not service or not service.get("is_active", True):
        raise ModuleNotificationBlocked("Le module du suivi est indisponible ou désactivé.")
    if not store.list_custom_service_records(service_code=service_code, record_id=record_id):
        raise ModuleNotificationBlocked("La fiche du suivi est indisponible ou archivée.")
    subjects = set(store.list_module_followup_subjects(module_code=relation_entity_module_code(service_code)))
    if not subjects:
        raise ModuleNotificationBlocked("Aucun utilisateur actif n’est abonné au suivi de ce module.")
    contacts = {subject: set() for subject in subjects}

    def add(identifiers, address):
        matches = subjects.intersection(str(value or "").strip().lower() for value in identifiers)
        if not matches or not address:
            return
        try:
            address = normalize_email_address(str(address)).lower()
        except ValueError:
            return
        for subject in matches:
            contacts[subject].add(address)

    for contact in store.list_directory_notification_contacts():
        add(contact.get("identifiers") or [], contact.get("email"))
    if any(len(addresses) != 1 for addresses in contacts.values()):
        raise ModuleNotificationBlocked("Chaque utilisateur abonné doit avoir une adresse e-mail unique et valide dans l’annuaire Agents.")
    return sorted({address for addresses in contacts.values() for address in addresses})
