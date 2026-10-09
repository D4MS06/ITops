from __future__ import annotations

from monitoring.config import settings
from monitoring.config.secrets_vault import ApplicationSecretsVault
from monitoring.services.device_service import DeviceService


def test_portable_vault_encrypts_secret_at_rest(tmp_path):
    vault = ApplicationSecretsVault(tmp_path)

    vault.set_or_delete("smtp:primary", "not-visible-in-file")

    assert vault.get("smtp:primary") == "not-visible-in-file"
    assert "not-visible-in-file" not in (tmp_path / "secrets.vault").read_text(encoding="utf-8", errors="ignore")
    assert (tmp_path / "secrets.key").is_file()


def test_device_password_is_migrated_from_database_to_shared_vault(monkeypatch, tmp_path):
    class Manager:
        def __init__(self):
            self.cleared_ids: list[str] = []

        def read_devices_map(self):
            return {"switch": [{"id": "sw-1", "device_password": "legacy-cleartext"}]}

        def clear_device_password(self, *, device_id: str):
            self.cleared_ids.append(device_id)
            return 1

    monkeypatch.setattr(settings, "CONFIG_FILE", tmp_path / "settings.json")
    manager = Manager()

    rows = DeviceService(manager).load_devices()

    assert rows["switch"][0]["device_password"] == "legacy-cleartext"
    assert manager.cleared_ids == ["sw-1"]
    vault = ApplicationSecretsVault(tmp_path)
    assert vault.get("__device_credential__switch__sw-1") == "legacy-cleartext"
