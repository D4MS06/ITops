from __future__ import annotations

from io import BytesIO
import os
import zipfile

import pytest
from fastapi import HTTPException

from monitoring.api.app import _ITOPS_BACKUP_MAGIC, _backup_fernet, _read_complete_backup


def test_complete_backup_reader_recovers_sql_and_encrypted_vault():
    archive = BytesIO()
    with zipfile.ZipFile(archive, mode="w") as bundle:
        bundle.writestr("database.sql", b"SELECT 1;")
        bundle.writestr("secrets.vault", b"encrypted-vault")
        bundle.writestr("master.key", b"master-key")
        bundle.writestr("manifest.json", "{}")
    salt = os.urandom(16)
    content = _ITOPS_BACKUP_MAGIC + salt + _backup_fernet("a-safe-backup-password", salt).encrypt(archive.getvalue())

    assert _read_complete_backup(content, backup_password="a-safe-backup-password") == (
        b"SELECT 1;", b"encrypted-vault", b"master-key"
    )
    with pytest.raises(HTTPException, match="Mot de passe incorrect"):
        _read_complete_backup(content, backup_password="wrong-password-123")
