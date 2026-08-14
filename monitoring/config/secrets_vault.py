"""Portable encrypted vault for application secrets.

The vault deliberately lives outside MariaDB: a database dump must never be
enough to recover a password.  Production instances should inject the master
key through ``NMP_SECRETS_MASTER_KEY`` (a Fernet key).  A local installation
gets a generated key stored with owner-only permissions, which keeps the
application usable while retaining the same data format as the server.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


ENV_MASTER_KEY = "NMP_SECRETS_MASTER_KEY"


def default_secrets_directory() -> Path:
    configured = str(os.environ.get("NMP_SECRETS_DIR", "") or "").strip()
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA") or str(Path.home()))
        return root / "NetworkMonitoringProject" / "config"
    root = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return root / "network-monitoring-project"


class ApplicationSecretsVault:
    """Small encrypted key/value vault shared by every application module."""

    def __init__(self, directory: str | Path | None = None) -> None:
        self.directory = Path(directory) if directory else default_secrets_directory()
        self.data_path = self.directory / "secrets.vault"
        self.key_path = self.directory / "secrets.key"
        self._lock = threading.RLock()

    def get(self, account: str) -> str:
        key = str(account or "").strip()
        if not key:
            return ""
        with self._lock:
            return str(self._read_payload().get(key, "") or "")

    def set_or_delete(self, account: str, value: str) -> None:
        key = str(account or "").strip()
        if not key:
            return
        with self._lock:
            payload = self._read_payload()
            normalized = str(value or "")
            if normalized:
                payload[key] = normalized
            else:
                payload.pop(key, None)
            self._write_payload(payload)

    def delete(self, account: str) -> None:
        self.set_or_delete(account, "")

    def export_recovery_material(self) -> dict[str, bytes]:
        """Return encrypted vault data and its key for an *outer encrypted* backup."""
        with self._lock:
            key = self._master_key()
            vault_data = self.data_path.read_bytes() if self.data_path.is_file() else Fernet(key).encrypt(b"{}")
            return {"vault": vault_data, "master_key": key}

    def validate_recovery_material(self, *, vault_data: bytes, master_key: bytes) -> None:
        try:
            decoded = Fernet(master_key).decrypt(vault_data)
            if not isinstance(json.loads(decoded.decode("utf-8")), dict):
                raise ValueError("payload")
        except (InvalidToken, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Le coffre inclus dans la sauvegarde est invalide.") from exc

    def restore_recovery_material(self, *, vault_data: bytes, master_key: bytes) -> None:
        self.validate_recovery_material(vault_data=vault_data, master_key=master_key)
        configured = str(os.environ.get(ENV_MASTER_KEY, "") or "").strip()
        if configured and configured.encode("ascii") != master_key:
            raise RuntimeError(f"La cle {ENV_MASTER_KEY} du serveur ne correspond pas a la sauvegarde.")
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            if not configured:
                self._write_raw(self.key_path, master_key)
            self._write_raw(self.data_path, vault_data)

    def _fernet(self) -> Fernet:
        return Fernet(self._master_key())

    def _master_key(self) -> bytes:
        configured_key = str(os.environ.get(ENV_MASTER_KEY, "") or "").strip()
        try:
            raw_key = configured_key.encode("ascii")
        except UnicodeEncodeError as exc:
            raise RuntimeError(f"{ENV_MASTER_KEY} doit contenir une cle Fernet URL-safe Base64 valide.") from exc
        if not raw_key:
            raw_key = self._load_or_create_local_key()
        try:
            Fernet(raw_key)
            return raw_key
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"{ENV_MASTER_KEY} doit contenir une cle Fernet URL-safe Base64 valide."
            ) from exc

    def _load_or_create_local_key(self) -> bytes:
        if self.key_path.is_file():
            return self.key_path.read_bytes().strip()
        self.directory.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        # Exclusive create avoids replacing an existing key in a concurrent start.
        try:
            with self.key_path.open("xb") as handle:
                handle.write(key)
            self._restrict_permissions(self.key_path)
            return key
        except FileExistsError:
            return self.key_path.read_bytes().strip()

    def _read_payload(self) -> dict[str, str]:
        if not self.data_path.is_file():
            return {}
        try:
            encrypted = self.data_path.read_bytes()
            decoded = self._fernet().decrypt(encrypted)
            payload = json.loads(decoded.decode("utf-8"))
        except InvalidToken as exc:
            raise RuntimeError("Le coffre de secrets ne peut pas etre dechiffre avec la cle maitre actuelle.") from exc
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Le coffre de secrets est illisible ou corrompu.") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Le format du coffre de secrets est invalide.")
        return {str(key): str(value or "") for key, value in payload.items()}

    def _write_payload(self, payload: dict[str, str]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        encrypted = self._fernet().encrypt(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        descriptor, temporary_name = tempfile.mkstemp(prefix=".secrets-", dir=str(self.directory))
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encrypted)
                handle.flush()
                os.fsync(handle.fileno())
            self._restrict_permissions(temporary_path)
            os.replace(temporary_path, self.data_path)
            self._restrict_permissions(self.data_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def _write_raw(self, path: Path, content: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".secrets-", dir=str(self.directory))
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            self._restrict_permissions(temporary_path)
            os.replace(temporary_path, path)
            self._restrict_permissions(path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _restrict_permissions(path: Path) -> None:
        if os.name != "nt":
            os.chmod(path, 0o600)
