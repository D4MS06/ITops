from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sys
try:
    import keyring  # type: ignore
except Exception:  # pragma: no cover - keyring may be absent
    class _DummyKeyring:
        def get_password(self, *_, **__):
            return ""

        def set_password(self, *_, **__):
            pass

    keyring = _DummyKeyring()  # type: ignore
    sys.modules['keyring'] = keyring

CONFIG_FILE = Path.home() / ".network_monitor_settings.json"
KEYRING_SERVICE = "NetworkMonitoringProject"


@dataclass
class NotificationSettings:
    smtp_host: str = ""
    smtp_port: int = 0
    user: str = ""
    password: str = ""
    use_tls: bool = False
    recipients: str = ""


def load_settings() -> NotificationSettings:
    """Charge les paramètres depuis le fichier JSON et le keyring."""
    data: dict[str, object] = {}
    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text())
        except Exception:
            data = {}
    user = str(data.get("user", ""))
    password = ""
    if user and keyring is not None:
        try:
            password = keyring.get_password(KEYRING_SERVICE, user) or ""
        except Exception:
            password = ""
    return NotificationSettings(
        smtp_host=str(data.get("smtp_host", "")),
        smtp_port=int(data.get("smtp_port", 0) or 0),
        user=user,
        password=password,
        use_tls=bool(data.get("use_tls", False)),
        recipients=str(data.get("recipients", "")),
    )


def save_settings(settings: NotificationSettings) -> None:
    """Sauvegarde les paramètres dans le fichier JSON et le keyring."""
    data = {
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "user": settings.user,
        "use_tls": settings.use_tls,
        "recipients": settings.recipients,
    }
    CONFIG_FILE.write_text(json.dumps(data, indent=2))
    if settings.user and settings.password and keyring is not None:
        try:
            keyring.set_password(KEYRING_SERVICE, settings.user, settings.password)
        except Exception:
            pass


