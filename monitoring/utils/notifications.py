from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from monitoring.config.settings import NotificationSettings, load_settings
from monitoring.utils.logger import log_with_timestamp


def send_alert_email(
    subject: str,
    body: str,
    *,
    settings: Optional[NotificationSettings] = None,
) -> None:
    """Envoie un email d'alerte selon les parametres fournis ou charges."""
    settings = settings or load_settings()
    if not settings.smtp_host or not settings.recipients:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.user or ""
    msg["To"] = settings.recipients
    msg.set_content(body)

    port = int(settings.smtp_port or (587 if settings.use_tls else 25))
    server = smtplib.SMTP(settings.smtp_host, port, timeout=20)
    try:
        server.ehlo_or_helo_if_needed()
        if settings.use_tls:
            server.starttls(context=ssl.create_default_context())
            server.ehlo_or_helo_if_needed()

        wants_auth = bool(settings.user and settings.password)
        has_auth_ext = bool(getattr(server, "has_extn", lambda *_: False)("auth"))
        auth_error: Exception | None = None

        if wants_auth and has_auth_ext:
            try:
                server.login(settings.user, settings.password)
            except smtplib.SMTPAuthenticationError as exc:
                auth_error = exc
                log_with_timestamp(
                    f"Echec d'authentification SMTP ({exc.smtp_code}), tentative d'envoi sans auth.",
                    level="WARNING",
                )
            except smtplib.SMTPException as exc:
                if "No suitable authentication method found" in str(exc):
                    log_with_timestamp(
                        "AUTH SMTP annoncee mais methode non supportee, tentative sans authentification.",
                        level="WARNING",
                    )
                else:
                    raise
        elif wants_auth and not has_auth_ext:
            # Certains serveurs Exchange en relay (port 25) n'annoncent pas AUTH.
            log_with_timestamp(
                "SMTP AUTH non annonce par le serveur, tentative d'envoi sans authentification.",
                level="WARNING",
            )

        try:
            server.send_message(msg)
        except Exception as send_exc:
            if auth_error is not None:
                raise RuntimeError(
                    f"Echec authentification SMTP ({auth_error.smtp_code}): {auth_error.smtp_error!r}"
                ) from auth_error
            raise send_exc
    except smtplib.SMTPNotSupportedError as exc:
        raise RuntimeError(f"Fonction SMTP non supportee par le serveur: {exc}") from exc
    finally:
        try:
            server.quit()
        except Exception:
            pass
