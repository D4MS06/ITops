from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Optional

from monitoring.config.settings import NotificationSettings, load_settings


def send_alert_email(subject: str, body: str,
                     *, settings: Optional[NotificationSettings] = None) -> None:
    """Envoie un email d'alerte selon les paramètres fournis ou chargés."""
    settings = settings or load_settings()
    if not settings.smtp_host or not settings.recipients:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.user
    msg["To"] = settings.recipients
    msg.set_content(body)

    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port or 0)
    try:
        if settings.use_tls:
            server.starttls()
        if settings.user and settings.password:
            server.login(settings.user, settings.password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
