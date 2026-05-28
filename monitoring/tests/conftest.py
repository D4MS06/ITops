from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _force_mariadb_runtime(monkeypatch):
    monkeypatch.delenv("NMP_ALLOW_SQLITE_RUNTIME", raising=False)
