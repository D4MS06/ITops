"""Shared permission contract for every ITops module."""
from __future__ import annotations

from collections.abc import Iterable


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
