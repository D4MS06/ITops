from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from monitoring.config import settings
from monitoring.config.secrets_vault import ApplicationSecretsVault
from monitoring.services.device_service import DeviceService
import pytest


def test_portable_vault_encrypts_secret_at_rest(tmp_path):
    vault = ApplicationSecretsVault(tmp_path)

    vault.set_or_delete("smtp:primary", "not-visible-in-file")

    assert vault.get("smtp:primary") == "not-visible-in-file"
    assert "not-visible-in-file" not in (tmp_path / "secrets.vault").read_text(encoding="utf-8", errors="ignore")
    assert (tmp_path / "secrets.key").is_file()


def test_vault_concurrent_modules_keep_each_others_secrets(tmp_path):
    def save(index):
        vault = ApplicationSecretsVault(tmp_path)
        vault.set_or_delete(f"module-{index}", f"secret-{index}")

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(save, range(16)))
    vault = ApplicationSecretsVault(tmp_path)
    assert all(vault.get(f"module-{index}") == f"secret-{index}" for index in range(16))


def test_device_password_is_migrated_from_database_to_shared_vault(monkeypatch, tmp_path):
    class Manager:
        def __init__(self):
            self.cleared_ids: list[str] = []

        def read_devices_map(self):
            return {"switch": [{"id": "sw-1", "device_password": "legacy-cleartext"}]}

        def clear_device_password(self, *, device_id: str):
            self.cleared_ids.append(device_id)
            return 1

        def clear_switch_legacy_credentials(self, *, device_id: str):
            self.cleared_ids.append(f"switch:{device_id}")

    monkeypatch.setattr(settings, "CONFIG_FILE", tmp_path / "settings.json")
    manager = Manager()

    rows = DeviceService(manager).load_devices()

    assert rows["switch"][0]["device_password"] == ""
    assert manager.cleared_ids == ["sw-1", "switch:sw-1"]
    vault = ApplicationSecretsVault(tmp_path)
    assert vault.get("__device_credential__switch__sw-1") == ""
    assert DeviceService(manager).get_access_credentials(dtype="switch", device_id="sw-1", access="web")["password"] == "legacy-cleartext"


def test_device_default_credential_keeps_legacy_vault_key_and_allows_future_profiles():
    assert DeviceService._device_secret_account("Switch", "sw-1") == "__device_credential__switch__sw-1"
    assert DeviceService._device_secret_account("Switch", "sw-1", "default") == "__device_credential__switch__sw-1"
    assert (
        DeviceService._device_secret_account("Switch", "sw-1", "admin-web")
        == "__device_credential__switch__sw-1__admin-web"
    )


def test_switch_migration_keeps_source_when_database_cleanup_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "CONFIG_FILE", tmp_path / "settings.json")
    store = settings._secrets_store()
    account = DeviceService._device_secret_account("switch", "one")
    store.set_or_delete_password(account, "secret")
    class Manager:
        def read_devices_map(self):
            return {"switch": [{"id": "one", "device_login": "admin"}]}
        def clear_switch_legacy_credentials(self, *, device_id):
            raise RuntimeError("database unavailable")
    service = DeviceService(Manager())
    with pytest.raises(RuntimeError, match="database unavailable"):
        service.load_devices()
    assert store.get_password(account) == "secret"
    assert service.get_access_credentials(dtype="switch", device_id="one", access="web") == {"login": "admin", "password": "secret"}


def test_device_access_credentials_are_separate_and_preserve_legacy(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "CONFIG_FILE", tmp_path / "settings.json")
    service = DeviceService(object())
    store = settings._secrets_store()
    legacy = service._device_secret_account("switch", "sw-1")
    store.set_or_delete_password(legacy, "ancien")
    service.set_access_credentials(dtype="switch", device_id="sw-1", access="web", login="web-admin", password="web-secret")
    service.set_access_credentials(dtype="switch", device_id="sw-1", access="ssh", login="ssh-admin", password="ssh-secret")
    service.set_access_credentials(dtype="switch", device_id="sw-1", access="web", login="new-web")
    assert service.get_access_credentials(dtype="switch", device_id="sw-1", access="web") == {"login": "new-web", "password": "web-secret"}
    assert service.get_access_credentials(dtype="switch", device_id="sw-1", access="ssh")["password"] == "ssh-secret"
    assert store.get_password(legacy) == "ancien"
    with pytest.raises(ValueError):
        service.get_access_credentials(dtype="switch", device_id="sw-1", access="default")
    service.delete_vault_credentials(dtype="switch", device_id="sw-1")
    assert store.get_password(legacy) == ""
    assert service.get_access_credentials(dtype="switch", device_id="sw-1", access="web")["password"] == ""


def test_switch_web_migration_preserves_existing_values_and_runs_once(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "CONFIG_FILE", tmp_path / "settings.json")
    service = DeviceService(object())
    service._migrate_switch_web_credentials(device_id="one", login="ancien", password="ancien-secret")
    assert service.get_access_credentials(dtype="switch", device_id="one", access="web") == {"login": "ancien", "password": "ancien-secret"}
    service.set_access_credentials(dtype="switch", device_id="one", access="web", login="nouveau", password="nouveau-secret")
    service._migrate_switch_web_credentials(device_id="one", login="ancien", password="ancien-secret")
    assert service.get_access_credentials(dtype="switch", device_id="one", access="web") == {"login": "nouveau", "password": "nouveau-secret"}
    service.set_access_credentials(dtype="switch", device_id="two", access="web", login="existant", password="secret")
    service._migrate_switch_web_credentials(device_id="two", login="ancien", password="ancien-secret")
    assert service.get_access_credentials(dtype="switch", device_id="two", access="web") == {"login": "existant", "password": "secret"}
