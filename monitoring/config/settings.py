from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import keyring  # type: ignore
except Exception:  # pragma: no cover - keyring may be absent
    class _DummyKeyring:
        def get_password(self, *_, **__):
            return ""

        def set_password(self, *_, **__):
            pass

        def delete_password(self, *_, **__):
            pass

    keyring = _DummyKeyring()  # type: ignore
    sys.modules["keyring"] = keyring

CONFIG_FILE = Path.home() / ".network_monitor_settings.json"
KEYRING_SERVICE = "NetworkMonitoringProject"
UPDATER_TOKEN_ACCOUNT = "__github_updates_token__"


@dataclass
class NotificationSettings:
    smtp_host: str = ""
    smtp_port: int = 0
    user: str = ""
    password: str = ""
    use_tls: bool = False
    recipients: str = ""
    offline_delay_seconds: int = 5
    online_recovery_delay_seconds: int = 5
    notification_cooldown_seconds: int = 120
    show_status_popup: bool = True
    updates_enabled: bool = False
    github_owner: str = ""
    github_repo: str = ""
    github_token: str = ""
    include_prerelease: bool = False


def load_settings() -> NotificationSettings:
    """Charge les parametres depuis le fichier JSON et le keyring."""
    data: dict[str, object] = {}
    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text())
        except Exception:
            data = {}

    user = str(data.get("user", "")).strip()
    password = ""
    if user and keyring is not None:
        try:
            password = keyring.get_password(KEYRING_SERVICE, user) or ""
        except Exception:
            password = ""

    try:
        offline_delay_seconds = max(1, int(data.get("offline_delay_seconds", 5) or 5))
    except Exception:
        offline_delay_seconds = 5

    try:
        online_recovery_delay_seconds = max(
            1, int(data.get("online_recovery_delay_seconds", offline_delay_seconds) or offline_delay_seconds)
        )
    except Exception:
        online_recovery_delay_seconds = offline_delay_seconds

    try:
        notification_cooldown_seconds = max(0, int(data.get("notification_cooldown_seconds", 120) or 0))
    except Exception:
        notification_cooldown_seconds = 120

    github_token = ""
    if keyring is not None:
        try:
            github_token = keyring.get_password(KEYRING_SERVICE, UPDATER_TOKEN_ACCOUNT) or ""
        except Exception:
            github_token = ""

    return NotificationSettings(
        smtp_host=str(data.get("smtp_host", "")).strip(),
        smtp_port=int(data.get("smtp_port", 0) or 0),
        user=user,
        password=password,
        use_tls=bool(data.get("use_tls", False)),
        recipients=str(data.get("recipients", "")).strip(),
        offline_delay_seconds=offline_delay_seconds,
        online_recovery_delay_seconds=online_recovery_delay_seconds,
        notification_cooldown_seconds=notification_cooldown_seconds,
        show_status_popup=bool(data.get("show_status_popup", True)),
        updates_enabled=bool(data.get("updates_enabled", False)),
        github_owner=str(data.get("github_owner", "")).strip(),
        github_repo=str(data.get("github_repo", "")).strip(),
        github_token=github_token,
        include_prerelease=bool(data.get("include_prerelease", False)),
    )


def save_settings(settings: NotificationSettings) -> None:
    """Sauvegarde les parametres dans le fichier JSON et le keyring."""
    previous_user = ""
    if CONFIG_FILE.is_file():
        try:
            previous_data = json.loads(CONFIG_FILE.read_text())
            previous_user = str(previous_data.get("user", "")).strip()
        except Exception:
            previous_user = ""

    data = {
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "user": settings.user,
        "use_tls": settings.use_tls,
        "recipients": settings.recipients,
        "offline_delay_seconds": max(1, int(settings.offline_delay_seconds or 5)),
        "online_recovery_delay_seconds": max(
            1, int(getattr(settings, "online_recovery_delay_seconds", settings.offline_delay_seconds) or settings.offline_delay_seconds)
        ),
        "notification_cooldown_seconds": max(
            0, int(getattr(settings, "notification_cooldown_seconds", 120) or 0)
        ),
        "show_status_popup": bool(settings.show_status_popup),
        "updates_enabled": bool(getattr(settings, "updates_enabled", False)),
        "github_owner": str(getattr(settings, "github_owner", "") or "").strip(),
        "github_repo": str(getattr(settings, "github_repo", "") or "").strip(),
        "include_prerelease": bool(getattr(settings, "include_prerelease", False)),
    }
    CONFIG_FILE.write_text(json.dumps(data, indent=2))

    if keyring is None:
        return

    if previous_user and previous_user != settings.user:
        try:
            keyring.delete_password(KEYRING_SERVICE, previous_user)
        except Exception:
            pass

    if settings.user and settings.password:
        try:
            keyring.set_password(KEYRING_SERVICE, settings.user, settings.password)
        except Exception:
            pass
    elif previous_user:
        try:
            keyring.delete_password(KEYRING_SERVICE, previous_user)
        except Exception:
            pass

    try:
        token = str(getattr(settings, "github_token", "") or "").strip()
        if token:
            keyring.set_password(KEYRING_SERVICE, UPDATER_TOKEN_ACCOUNT, token)
        else:
            keyring.delete_password(KEYRING_SERVICE, UPDATER_TOKEN_ACCOUNT)
    except Exception:
        pass
