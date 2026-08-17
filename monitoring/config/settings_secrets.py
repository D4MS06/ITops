from __future__ import annotations

import threading

from monitoring.config.secrets_vault import ApplicationSecretsVault


class SettingsSecretsStore:
    def __init__(self, *, keyring_impl, service_name: str, vault_directory=None) -> None:
        self._keyring = keyring_impl
        self._service_name = service_name
        self._timeout_seconds = 1.0
        self._vault = ApplicationSecretsVault(vault_directory)

    def _run_with_timeout(self, func, *args, default=None):
        result = {"value": default}
        error = {"value": None}

        def worker() -> None:
            try:
                result["value"] = func(*args)
            except Exception as exc:  # pragma: no cover - defensive timeout wrapper
                error["value"] = exc

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(self._timeout_seconds)
        if thread.is_alive() or error["value"] is not None:
            return default
        return result["value"]

    def get_password(self, account: str) -> str:
        stored = self._vault.get(account)
        if stored:
            return stored
        # One-shot lazy migration from the former OS keyring/plaintext fallback.
        # The legacy value is removed only after the encrypted write succeeds.
        if self._keyring is None:
            return ""
        try:
            legacy = self._run_with_timeout(self._keyring.get_password, self._service_name, account, default="") or ""
            if legacy:
                self._vault.set_or_delete(account, legacy)
                self._run_with_timeout(self._keyring.delete_password, self._service_name, account, default=None)
            return legacy
        except Exception:
            return ""

    def set_or_delete_password(self, account: str, value: str) -> None:
        self._vault.set_or_delete(account, value)
        if self._keyring is not None:
            try:
                # Remove a migrated legacy copy; new values are vault-only.
                self._run_with_timeout(self._keyring.delete_password, self._service_name, account, default=None)
            except Exception:
                pass

    def delete_password(self, account: str) -> None:
        self._vault.delete(account)
        if self._keyring is not None:
            try:
                self._run_with_timeout(self._keyring.delete_password, self._service_name, account, default=None)
            except Exception:
                pass

    def vault_status(self) -> dict[str, object]:
        return self._vault.status()

    def initialize_local_vault(self) -> dict[str, object]:
        return self._vault.initialize_local()

    def test_vault_access(self) -> None:
        self._vault.test_access()
