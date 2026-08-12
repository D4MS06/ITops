import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from monitoring.config import settings
from monitoring.api.app import (
    _directory_agent_service_dns,
    _directory_business_agent_service_dns,
    _directory_dn_component_value,
    _directory_dn_ou_values,
    _filter_active_directory_entries_for_profile,
)
from monitoring.api.schemas import ActiveDirectorySyncProfile
from monitoring.services.settings_service import ActiveDirectorySyncEngine


def test_save_and_load_settings(tmp_path):
    cfg = tmp_path / "cfg.json"
    test_settings = settings.NotificationSettings(
        log_level="INFO",
        monitoring_log_level="INFO",
        ui_log_level="ERROR",
        smtp_host="smtp.example.com",
        smtp_port=587,
        user="user",
        password="secret",
        use_tls=True,
        recipients="a@example.com,b@example.com",
        failures_for_offline=4,
        successes_for_online=3,
        ping_timeout_ms=2200,
        probe_interval_ms=1300,
        log_diagnostic_events=True,
        web_server_host="0.0.0.0",
        web_server_port=8100,
        web_server_autostart=True,
        web_server_public_url="https://monitoring.mvl",
        web_server_use_public_url=True,
        web_server_reverse_proxy_type="nginx",
        web_session_ttl_seconds=1800,
        web_revoke_sessions_on_startup=True,
        active_directory_sync_email_accounts=True,
    )
    memory_secrets = {"user": "secret"}
    fake_keyring = SimpleNamespace(
        get_password=lambda _service, account: memory_secrets.get(account, ""),
        set_password=lambda _service, account, value: memory_secrets.__setitem__(account, value),
        delete_password=lambda _service, account: memory_secrets.pop(account, None),
    )

    with patch.object(settings, "CONFIG_FILE", cfg), \
         patch.object(settings, "_resolve_keyring", return_value=fake_keyring):
        settings.save_settings(test_settings)
        assert cfg.exists()
        data = json.loads(cfg.read_text())
        assert data["smtp_host"] == "smtp.example.com"
        assert data["log_level"] == "INFO"
        assert data["monitoring_log_level"] == "INFO"
        assert data["ui_log_level"] == "ERROR"
        assert data["web_server_host"] == "0.0.0.0"
        assert data["web_server_port"] == 8100
        assert data["web_server_autostart"] is True
        assert data["web_server_public_url"] == "https://monitoring.mvl"
        assert data["web_server_use_public_url"] is True
        assert data["web_server_reverse_proxy_type"] == "nginx"
        assert data["web_session_ttl_seconds"] == 1800
        assert data["web_revoke_sessions_on_startup"] is True
        assert data["active_directory_sync_email_accounts"] is True
        loaded = settings.load_settings()
        assert loaded == test_settings


def test_load_settings_missing_file(tmp_path):
    cfg = tmp_path / "missing.json"
    fake_keyring = SimpleNamespace(
        get_password=lambda _service, _account: "",
        set_password=lambda _service, _account, _value: None,
        delete_password=lambda _service, _account: None,
    )
    with patch.object(settings, "CONFIG_FILE", cfg), \
         patch.object(settings, "_resolve_keyring", return_value=fake_keyring):
        loaded = settings.load_settings()
        assert loaded == settings.NotificationSettings()


def test_active_directory_settings_keep_password_out_of_json_and_restore_it(tmp_path):
    cfg = tmp_path / "ad.json"
    memory_secrets = {}
    fake_keyring = SimpleNamespace(
        get_password=lambda _service, account: memory_secrets.get(account, ""),
        set_password=lambda _service, account, value: memory_secrets.__setitem__(account, value),
        delete_password=lambda _service, account: memory_secrets.pop(account, None),
    )
    configured = settings.NotificationSettings(
        active_directory_enabled=True,
        active_directory_host="ad.example.local",
        active_directory_bind_username="svc_itops@example.local",
        active_directory_bind_password="not-in-json",
        active_directory_base_dn="DC=example,DC=local",
    )
    with patch.object(settings, "CONFIG_FILE", cfg), patch.object(settings, "_resolve_keyring", return_value=fake_keyring):
        settings.save_settings(configured)
        assert "active_directory_bind_password" not in json.loads(cfg.read_text())
        assert settings.load_settings().active_directory_bind_password == "not-in-json"


def test_active_directory_engine_rejects_incomplete_configuration():
    with pytest.raises(ValueError, match="Serveur"):
        ActiveDirectorySyncEngine().test_connection(settings.NotificationSettings())


def test_active_directory_engine_builds_upn_from_simple_bind_username():
    connection = ActiveDirectorySyncEngine.connection_from_settings(settings.NotificationSettings(
        active_directory_bind_username="svc_itops_ldap",
        active_directory_base_dn="DC=ecolesVL,DC=local",
    ))

    assert ActiveDirectorySyncEngine._bind_identity(connection) == "svc_itops_ldap@ecolesVL.local"


def test_active_directory_engine_keeps_explicit_bind_identity():
    connection = ActiveDirectorySyncEngine.connection_from_settings(settings.NotificationSettings(
        active_directory_bind_username="CN=svc_itops_ldap,CN=Users,DC=ecolesVL,DC=local",
        active_directory_base_dn="DC=ecolesVL,DC=local",
    ))

    assert ActiveDirectorySyncEngine._bind_identity(connection) == "CN=svc_itops_ldap,CN=Users,DC=ecolesVL,DC=local"


def test_directory_dn_helpers_extract_agent_identity_and_services():
    dn = "CN=Dupont Jean,OU=Administratif,OU=CTM,OU=MairieVL,DC=mairieVL,DC=local"

    assert _directory_dn_component_value(dn, "CN") == "Dupont Jean"
    assert _directory_dn_ou_values(dn) == ["Administratif", "CTM", "MairieVL"]
    assert _directory_agent_service_dns(dn) == [
        "OU=Administratif,OU=CTM,OU=MairieVL,DC=mairieVL,DC=local",
        "OU=CTM,OU=MairieVL,DC=mairieVL,DC=local",
        "OU=MairieVL,DC=mairieVL,DC=local",
    ]


def test_directory_business_service_dns_skip_technical_ou_names():
    dn = "CN=Agent X,OU=Ordinateur,OU=Dev Durable,OU=CTM,OU=MairieVL,DC=mairieVL,DC=local"

    assert _directory_business_agent_service_dns(dn)[0] == "OU=Dev Durable,OU=CTM,OU=MairieVL,DC=mairieVL,DC=local"


def test_active_directory_ou_profile_filters_by_root_depth_and_name_exclusions():
    profile = ActiveDirectorySyncProfile(
        id="profile-ou",
        target_kind="organizational_units",
        selected_attributes=["ou", "distinguishedName"],
        options={
            "ou_root_dn": "OU=MairieVL,DC=mairieVL,DC=local",
            "ou_max_depth": 1,
            "excluded_ou_names": ["Ordinateurs", "Profil", "Prets"],
        },
    )
    entries = [
        {"ou": "MairieVL", "distinguishedName": "OU=MairieVL,DC=mairieVL,DC=local"},
        {"ou": "CTM", "distinguishedName": "OU=CTM,OU=MairieVL,DC=mairieVL,DC=local"},
        {"ou": "Utilisateurs", "distinguishedName": "OU=Utilisateurs,OU=CTM,OU=MairieVL,DC=mairieVL,DC=local"},
        {"ou": "Administratif", "distinguishedName": "OU=Administratif,OU=CTM,OU=MairieVL,DC=mairieVL,DC=local"},
        {"ou": "Ordinateurs", "distinguishedName": "OU=Ordinateurs,OU=MairieVL,DC=mairieVL,DC=local"},
        {"ou": "Administratif", "distinguishedName": "OU=Administratif,OU=IPF,DC=mairieVL,DC=local"},
    ]

    filtered = _filter_active_directory_entries_for_profile(entries, profile, "organizational_units")

    assert [row["ou"] for row in filtered] == ["MairieVL", "CTM"]


def test_load_settings_migrates_legacy_monitoring_defaults(tmp_path):
    cfg = tmp_path / "legacy.json"
    cfg.write_text(json.dumps({
        "offline_delay_seconds": 5,
        "online_recovery_delay_seconds": 5,
        "failures_for_offline": 3,
        "successes_for_online": 2,
        "ping_timeout_ms": 1500,
        "probe_interval_ms": 1000,
    }))

    with patch.object(settings, "CONFIG_FILE", cfg):
        loaded = settings.load_settings()

    assert loaded.offline_delay_seconds == 20
    assert loaded.online_recovery_delay_seconds == 10
    assert loaded.failures_for_offline == 5
    assert loaded.successes_for_online == 3
    assert loaded.ping_timeout_ms == 2500
    assert loaded.probe_interval_ms == 2000


def test_load_settings_preserves_custom_monitoring_values(tmp_path):
    cfg = tmp_path / "custom.json"
    cfg.write_text(json.dumps({
        "offline_delay_seconds": 7,
        "online_recovery_delay_seconds": 5,
        "failures_for_offline": 3,
        "successes_for_online": 2,
        "ping_timeout_ms": 1500,
        "probe_interval_ms": 1000,
    }))

    with patch.object(settings, "CONFIG_FILE", cfg):
        loaded = settings.load_settings()

    assert loaded.offline_delay_seconds == 7
    assert loaded.online_recovery_delay_seconds == 5
    assert loaded.failures_for_offline == 3
    assert loaded.successes_for_online == 2
    assert loaded.ping_timeout_ms == 1500
    assert loaded.probe_interval_ms == 1000


def test_save_settings_empty_password_deletes_keyring_secret(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"user": "user@example.com"}))
    test_settings = settings.NotificationSettings(
        smtp_host="smtp.example.com",
        smtp_port=25,
        user="user@example.com",
        password="",
        use_tls=False,
        recipients="a@example.com",
    )
    fake_keyring = SimpleNamespace(
        get_password=lambda _service, _account: "",
        set_password=lambda _service, _account, _value: None,
        delete_password=lambda _service, _account: None,
    )
    with patch.object(settings, "CONFIG_FILE", cfg), \
         patch.object(settings, "_resolve_keyring", return_value=fake_keyring), \
         patch.object(fake_keyring, "delete_password") as dpw:
        settings.save_settings(test_settings)
        calls = [args for args, _kwargs in dpw.call_args_list]
        assert (settings.KEYRING_SERVICE, "user@example.com") in calls
        assert (settings.KEYRING_SERVICE, settings.UPDATER_TOKEN_ACCOUNT) in calls
        assert (settings.KEYRING_SERVICE, settings.ACTIVE_DIRECTORY_PASSWORD_ACCOUNT) not in calls


def test_default_config_file_prefers_localappdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    expected = tmp_path / "NetworkMonitoringProject" / "config" / "settings.json"
    assert settings.default_config_file() == expected


def test_dummy_keyring_persists_local_fallback_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    first = settings._DummyKeyring()
    first.set_password("svc", "account", "secret")

    second = settings._DummyKeyring()

    assert second.get_password("svc", "account") == "secret"

