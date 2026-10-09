"""Shared permission contract for every ITops module."""
from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha1


MODULE_PERMISSION_CODES = (
    "read",
    "create",
    "update",
    "delete",
    "import",
    "export",
    "credentials_view",
    "credentials_manage",
    "configure",
)

MODULE_PERMISSION_LABELS = {
    "read": "Lecture",
    "create": "Creer",
    "update": "Modifier",
    "delete": "Supprimer",
    "import": "Importer",
    "export": "Exporter",
    "credentials_view": "Voir les identifiants et mots de passe",
    "credentials_manage": "Modifier les identifiants et mots de passe",
    "configure": "Configurer le module",
}

ROLE_TEMPLATE_PERMISSIONS = {
    "administrator": MODULE_PERMISSION_CODES,
    "business_manager": ("read", "create", "update", "delete", "import", "export"),
    "technician": ("read", "create", "update", "credentials_view", "credentials_manage"),
    "reader": ("read",),
}


def custom_service_module_code(service_code: object) -> str:
    """Return the canonical RBAC module code for a custom service.

    Custom-service codes are unconstrained user data, while auth-module codes
    are bounded.  The digest keeps the resulting code stable and unique when
    two long codes share the same prefix.
    """
    normalized = str(service_code or "").strip().lower() or "service"
    if normalized == "emails":
        return "service_emails"
    digest = sha1(normalized.encode("utf-8")).hexdigest()[:8]
    safe_base = "".join(character if character.isalnum() or character == "_" else "_" for character in normalized)
    max_base_len = max(1, 64 - len("service_") - len("_") - len(digest))
    return f"service_{safe_base[:max_base_len]}_{digest}"


def normalize_module_permissions(values: Iterable[object] | None, *, legacy_grant: bool = False) -> list[str]:
    """Return supported capabilities in the stable display order.

    Existing role/module links have no capability payload.  They keep their
    historical full access until an administrator explicitly saves the role.
    """
    requested = {str(value or "").strip().lower() for value in (values or [])}
    if legacy_grant and not requested:
        requested = set(MODULE_PERMISSION_CODES)
    if "credentials_manage" in requested:
        requested.add("credentials_view")
    if requested - {"read"}:
        requested.add("read")
    return [permission for permission in MODULE_PERMISSION_CODES if permission in requested]


def permissions_allow(values: Iterable[object] | None, permission: str) -> bool:
    return str(permission or "").strip().lower() in set(normalize_module_permissions(values))
