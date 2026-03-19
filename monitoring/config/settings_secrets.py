from __future__ import annotations

import threading


class SettingsSecretsStore:
    def __init__(self, *, keyring_impl, service_name: str) -> None:
        self._keyring = keyring_impl
        self._service_name = service_name
        self._timeout_seconds = 1.0

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
        if self._keyring is None:
            return ""
        try:
            return self._run_with_timeout(self._keyring.get_password, self._service_name, account, default="") or ""
        except Exception:
            return ""

    def set_or_delete_password(self, account: str, value: str) -> None:
        if self._keyring is None:
            return
        try:
            if value:
                self._run_with_timeout(self._keyring.set_password, self._service_name, account, value, default=None)
            else:
                self._run_with_timeout(self._keyring.delete_password, self._service_name, account, default=None)
        except Exception:
            return

    def delete_password(self, account: str) -> None:
        if self._keyring is None:
            return
        try:
            self._run_with_timeout(self._keyring.delete_password, self._service_name, account, default=None)
        except Exception:
            return
