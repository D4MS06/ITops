from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from monitoring.config.settings import NotificationSettings, load_settings


def send_alert_email(
    subject: str,
    body: str,
    *,
    settings: Optional[NotificationSettings] = None,
    recipients: list[str] | None = None,
) -> None:
    """Envoie un email d'alerte selon les parametres fournis ou charges."""
    settings = settings or load_settings()
    target_recipients = [str(value).strip() for value in (recipients or []) if str(value).strip()]
    if not target_recipients:
        target_recipients = [value.strip() for value in str(settings.recipients or "").split(",") if value.strip()]
    if not settings.smtp_host or not target_recipients:
        return
    auth_enabled = bool(getattr(settings, "smtp_auth_enabled", False))
    if auth_enabled and (not settings.user or not settings.password):
        raise RuntimeError("Authentification SMTP activee mais identifiant ou mot de passe manquant.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.user or target_recipients[0]
    msg["To"] = ", ".join(target_recipients)
    msg.set_content(body)

    port = int(settings.smtp_port or (587 if settings.use_tls else 25))
    server: smtplib.SMTP | None = None
    try:
        server = smtplib.SMTP(settings.smtp_host, port, timeout=20)
        server.ehlo_or_helo_if_needed()
        if settings.use_tls:
            server.starttls(context=ssl.create_default_context())
            server.ehlo_or_helo_if_needed()

        if auth_enabled:
            server.login(settings.user, settings.password)
        server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(f"Echec authentification SMTP ({exc.smtp_code}): {exc.smtp_error!r}") from exc
    except smtplib.SMTPNotSupportedError as exc:
        raise RuntimeError(f"Fonction SMTP non supportee par le serveur: {exc}") from exc
    except smtplib.SMTPException as exc:
        raise RuntimeError(f"Echec SMTP: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Connexion SMTP impossible: {exc}") from exc
    finally:
        try:
            if server is not None:
                server.quit()
        except Exception:
            pass
