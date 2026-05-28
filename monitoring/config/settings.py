from __future__ import annotations

import json
import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from monitoring.config.settings_codec import build_notification_settings_kwargs, build_settings_payload
from monitoring.config.settings_secrets import SettingsSecretsStore


class _DummyKeyring:
    def get_password(self, *_, **__):
        return ""

    def set_password(self, *_, **__):
        pass

    def delete_password(self, *_, **__):
        pass


class _LazyKeyringProxy:
    def __getattr__(self, item: str):
        return getattr(_resolve_keyring(), item)


def default_config_file() -> Path:
    app_data_root = Path(os.environ.get("LOCALAPPDATA") or str(Path.home()))
    return app_data_root / "NetworkMonitoringProject" / "config" / "settings.json"


CONFIG_FILE = default_config_file()
KEYRING_SERVICE = "NetworkMonitoringProject"
UPDATER_TOKEN_ACCOUNT = "__github_updates_token__"
CONFIG_SMB_PASSWORD_ACCOUNT = "__config_smb_password__"
ADMIN_PASSWORD_HASH_ACCOUNT = "__admin_password_hash__"

_KEYRING_IMPL = None
keyring = _LazyKeyringProxy()


def _resolve_keyring():
    global _KEYRING_IMPL
    if _KEYRING_IMPL is not None:
        return _KEYRING_IMPL
    # Some Windows environments block on keyring backend discovery.
    # Keep startup deterministic and allow opt-in with NMP_ENABLE_KEYRING=1.
    enable_keyring = str(os.environ.get("NMP_ENABLE_KEYRING", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not enable_keyring:
        _KEYRING_IMPL = _DummyKeyring()
        sys.modules["keyring"] = _KEYRING_IMPL
        return _KEYRING_IMPL
    try:
        _KEYRING_IMPL = importlib.import_module("keyring")  # type: ignore[assignment]
    except Exception:  # pragma: no cover - keyring may be absent or broken
        _KEYRING_IMPL = _DummyKeyring()
        sys.modules["keyring"] = _KEYRING_IMPL
    return _KEYRING_IMPL


def _secrets_store() -> SettingsSecretsStore:
    return SettingsSecretsStore(keyring_impl=_resolve_keyring(), service_name=KEYRING_SERVICE)


@dataclass
class NotificationSettings:
    log_level: str = "INFO"
    monitoring_log_level: str = "INFO"
    ui_log_level: str = "ERROR"
    smtp_host: str = ""
    smtp_port: int = 0
    user: str = ""
    password: str = ""
    use_tls: bool = False
    recipients: str = ""
    offline_delay_seconds: int = 5
    online_recovery_delay_seconds: int = 5
    notification_cooldown_seconds: int = 120
    failures_for_offline: int = 3
    successes_for_online: int = 2
    ping_timeout_ms: int = 1500
    probe_interval_ms: int = 1000
    credential_reveal_unlock_seconds: int = 300
    log_diagnostic_events: bool = False
    show_status_popup: bool = True
    updates_enabled: bool = False
    github_owner: str = "D4MS06"
    github_repo: str = "NetworkMonitoringProject"
    github_token: str = ""
    include_prerelease: bool = False
    update_target_tag: str = "latest"
    updates_connection_validated: bool = False
    watermark_image_path: str = ""
    watermark_source_path: str = ""
    watermark_opacity: float = 0.16
    watermark_offset_x: int = 0
    watermark_offset_y: int = 0
    watermark_zoom_percent: int = 100
    ui_theme: str = "light"
    theme_overrides_json: str = ""
    status_indicator_style: str = "badge"
    switch_configs_dir: str = ""
    config_storage_mode: str = "local"
    config_smb_unc_path: str = ""
    config_smb_username: str = ""
    config_smb_password: str = ""
    config_auto_sync_enabled: bool = False
    config_auto_sync_interval_seconds: int = 3600
    dashboard_cards_order_json: str = ""
    dashboard_hidden_cards_json: str = ""
    web_server_host: str = "127.0.0.1"
    web_server_port: int = 8000
    web_server_autostart: bool = False
    web_server_public_url: str = ""
    web_server_use_public_url: bool = False
    web_server_reverse_proxy_type: str = "aucun"


def load_settings() -> NotificationSettings:
    """Charge les parametres depuis le fichier JSON et le keyring."""
    data: dict[str, object] = {}
    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    kwargs = build_notification_settings_kwargs(data)
    user = str(kwargs.get("user", "") or "").strip()
    secrets = _secrets_store()
    kwargs["password"] = secrets.get_password(user) if user else ""
    kwargs["github_token"] = secrets.get_password(UPDATER_TOKEN_ACCOUNT)
    kwargs["config_smb_password"] = secrets.get_password(CONFIG_SMB_PASSWORD_ACCOUNT)
    return NotificationSettings(**kwargs)


def save_settings(settings: NotificationSettings) -> None:
    """Sauvegarde les parametres dans le fichier JSON et le keyring."""
    previous_user = ""
    if CONFIG_FILE.is_file():
        try:
            previous_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            previous_user = str(previous_data.get("user", "")).strip()
        except Exception:
            previous_user = ""

    data = build_settings_payload(settings)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    secrets = _secrets_store()

    if previous_user and previous_user != settings.user:
        secrets.delete_password(previous_user)

    if settings.user and settings.password:
        secrets.set_or_delete_password(settings.user, settings.password)
    elif previous_user:
        secrets.delete_password(previous_user)

    token = str(getattr(settings, "github_token", "") or "").strip()
    secrets.set_or_delete_password(UPDATER_TOKEN_ACCOUNT, token)
    smb_password = str(getattr(settings, "config_smb_password", "") or "").strip()
    secrets.set_or_delete_password(CONFIG_SMB_PASSWORD_ACCOUNT, smb_password)
