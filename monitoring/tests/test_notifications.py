from email.message import EmailMessage
import smtplib

from monitoring.utils.notifications import NotificationSettings, send_alert_email


class DummySMTP:
    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.starttls_called = False
        self.login_called = False
        self.ehlo_called = 0
        self.sent = []
        self._has_auth = True

    def ehlo_or_helo_if_needed(self):
        self.ehlo_called += 1

    def has_extn(self, name):
        return self._has_auth if str(name).lower() == "auth" else False

    def starttls(self, context=None):
        self.starttls_called = True

    def login(self, user, password):
        self.login_called = True
        self.login_user = user
        self.login_password = password

    def send_message(self, msg: EmailMessage):
        self.sent.append(msg)

    def quit(self):
        pass


def test_send_alert_email_sends_with_auth(monkeypatch):
    smtp = DummySMTP("", 0)

    def smtp_factory(host, port, timeout=None):
        assert host == "smtp.example.com"
        assert port == 25
        return smtp

    monkeypatch.setattr("smtplib.SMTP", smtp_factory)

    settings = NotificationSettings(
        smtp_host="smtp.example.com",
        smtp_port=25,
        user="user",
        password="pwd",
        use_tls=True,
        recipients="a@example.com",
    )

    send_alert_email("Sub", "Body", settings=settings)

    assert smtp.starttls_called is True
    assert smtp.login_called is True
    assert len(smtp.sent) == 1
    msg = smtp.sent[0]
    assert msg["Subject"] == "Sub"
    assert msg["To"] == "a@example.com"


def test_send_alert_email_sends_without_auth_when_server_does_not_support_it(monkeypatch):
    smtp = DummySMTP("", 0)
    smtp._has_auth = False

    def smtp_factory(host, port, timeout=None):
        return smtp

    monkeypatch.setattr("smtplib.SMTP", smtp_factory)

    settings = NotificationSettings(
        smtp_host="smtp.example.com",
        smtp_port=25,
        user="user",
        password="pwd",
        use_tls=False,
        recipients="a@example.com",
    )

    send_alert_email("Sub", "Body", settings=settings)

    assert smtp.login_called is False
    assert len(smtp.sent) == 1


def test_send_alert_email_falls_back_when_auth_method_is_not_supported(monkeypatch):
    smtp = DummySMTP("", 0)

    def _login(_user, _password):
        raise smtplib.SMTPException("No suitable authentication method found.")

    smtp.login = _login  # type: ignore[assignment]

    def smtp_factory(host, port, timeout=None):
        return smtp

    monkeypatch.setattr("smtplib.SMTP", smtp_factory)

    settings = NotificationSettings(
        smtp_host="smtp.example.com",
        smtp_port=25,
        user="user",
        password="pwd",
        use_tls=False,
        recipients="a@example.com",
    )

    send_alert_email("Sub", "Body", settings=settings)
    assert len(smtp.sent) == 1


def test_send_alert_email_falls_back_when_authentication_fails_but_relay_allows_send(monkeypatch):
    smtp = DummySMTP("", 0)

    def _login(_user, _password):
        raise smtplib.SMTPAuthenticationError(535, b"5.7.3 Authentication unsuccessful")

    smtp.login = _login  # type: ignore[assignment]

    def smtp_factory(host, port, timeout=None):
        return smtp

    monkeypatch.setattr("smtplib.SMTP", smtp_factory)

    settings = NotificationSettings(
        smtp_host="smtp.example.com",
        smtp_port=25,
        user="user",
        password="pwd",
        use_tls=False,
        recipients="a@example.com",
    )

    send_alert_email("Sub", "Body", settings=settings)
    assert len(smtp.sent) == 1


def test_send_alert_email_missing_params(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("SMTP should not be called")

    monkeypatch.setattr("smtplib.SMTP", fail)

    settings = NotificationSettings()
    send_alert_email("S", "B", settings=settings)
