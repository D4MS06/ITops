import json
from unittest.mock import patch

from monitoring.config import settings


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
    )
    def fake_get_password(_service, account):
        return "secret" if account == "user" else ""

    with patch.object(settings, "CONFIG_FILE", cfg), \
         patch("keyring.set_password") as spw, \
         patch("keyring.get_password", side_effect=fake_get_password):
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
        spw.assert_called_once_with(settings.KEYRING_SERVICE, "user", "secret")
        loaded = settings.load_settings()
        assert loaded == test_settings


def test_load_settings_missing_file(tmp_path):
    cfg = tmp_path / "missing.json"
    with patch.object(settings, "CONFIG_FILE", cfg):
        loaded = settings.load_settings()
        assert loaded == settings.NotificationSettings()


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
    with patch.object(settings, "CONFIG_FILE", cfg), \
         patch("keyring.delete_password") as dpw:
        settings.save_settings(test_settings)
        calls = [args for args, _kwargs in dpw.call_args_list]
        assert (settings.KEYRING_SERVICE, "user@example.com") in calls
        assert (settings.KEYRING_SERVICE, settings.UPDATER_TOKEN_ACCOUNT) in calls


def test_default_config_file_prefers_localappdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    expected = tmp_path / "NetworkMonitoringProject" / "config" / "settings.json"
    assert settings.default_config_file() == expected

