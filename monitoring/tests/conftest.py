from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _force_mariadb_backend(monkeypatch):
    monkeypatch.setenv("NMP_DB_BACKEND", "mariadb")
    monkeypatch.delenv("NMP_ALLOW_SQLITE_RUNTIME", raising=False)
