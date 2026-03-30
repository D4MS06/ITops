from __future__ import annotations

import os

SUPPORTED_STORAGE_BACKENDS = {"sqlite", "mariadb"}


def resolve_storage_backend() -> str:
    raw = str(os.environ.get("NMP_DB_BACKEND") or os.environ.get("NMP_STORAGE_BACKEND") or "").strip().lower()
    if raw in SUPPORTED_STORAGE_BACKENDS:
        return raw
    return "sqlite"
