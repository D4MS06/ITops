import json
from pathlib import Path
from unittest.mock import patch

from monitoring.config import settings


def test_save_and_load_settings(tmp_path):
    cfg = tmp_path / "cfg.json"
    test_settings = settings.NotificationSettings(
        smtp_host="smtp.example.com",
        smtp_port=587,
        user="user",
        password="secret",
        use_tls=True,
        recipients="a@example.com,b@example.com",
    )
    with patch.object(settings, "CONFIG_FILE", cfg), \
         patch("keyring.set_password") as spw, \
         patch("keyring.get_password", return_value="secret"):
        settings.save_settings(test_settings)
        assert cfg.exists()
        data = json.loads(cfg.read_text())
        assert data["smtp_host"] == "smtp.example.com"
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
        dpw.assert_called_once_with(settings.KEYRING_SERVICE, "user@example.com")

