from __future__ import annotations

from dataclasses import dataclass


ALLOWED_CREDENTIAL_IMPORT_MODES = {
    "preserve_on_blank",
    "overwrite",
    "ignore",
}


def normalize_credential_import_mode(value: object) -> str:
    mode = str(value or "").strip().lower()
    if mode in ALLOWED_CREDENTIAL_IMPORT_MODES:
        return mode
    return "preserve_on_blank"


@dataclass(frozen=True)
class CredentialImportResolution:
    login: str | None
    password: str | None


def resolve_credential_import_values(
    *,
    mode: str,
    operation: str,
    login_present: bool,
    login_value: object,
    password_present: bool,
    password_value: object,
) -> CredentialImportResolution:
    normalized_mode = normalize_credential_import_mode(mode)
    normalized_operation = str(operation or "").strip().lower()
    is_update = normalized_operation == "update"

    if normalized_mode == "ignore":
        return CredentialImportResolution(login=None, password=None)

    raw_login = str(login_value or "").strip()
    raw_password = str(password_value or "").strip()

    def _resolve(present: bool, value: str) -> str | None:
        if not present:
            return None
        if normalized_mode == "preserve_on_blank" and is_update and not value:
            return None
        return value

    return CredentialImportResolution(
        login=_resolve(login_present, raw_login),
        password=_resolve(password_present, raw_password),
    )

