from __future__ import annotations

import os

SUPPORTED_STORAGE_BACKENDS = {"mariadb"}


def _is_truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def sqlite_runtime_allowed() -> bool:
    _ = _is_truthy  # keep helper used for backward-compatible imports/tests
    return False


def resolve_storage_backend() -> str:
    raw = str(os.environ.get("NMP_DB_BACKEND") or os.environ.get("NMP_STORAGE_BACKEND") or "").strip().lower()
    if raw == "sqlite":
        raise RuntimeError(
            "Le backend SQLite est retire du runtime a partir de la 1.10. "
            "Utilisez MariaDB (SQLite reste reserve a la migration des donnees)."
        )
    if raw and raw not in SUPPORTED_STORAGE_BACKENDS:
        raise RuntimeError(
            f"Backend de stockage non supporte: '{raw}'. "
            "Valeur attendue: 'mariadb'."
        )
    return "mariadb"
