from email.message import EmailMessage

from monitoring.utils.notifications import send_alert_email, NotificationSettings


class DummySMTP:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.starttls_called = False
        self.login_called = False
        self.sent = []

    def starttls(self):
        self.starttls_called = True

    def login(self, user, password):
        self.login_called = True
        self.login_user = user
        self.login_password = password

    def send_message(self, msg: EmailMessage):
        self.sent.append(msg)

    def quit(self):
        pass


def test_send_alert_email_sends(monkeypatch):
    smtp = DummySMTP("", 0)

    def smtp_factory(host, port):
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


def test_send_alert_email_missing_params(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("SMTP should not be called")

    monkeypatch.setattr("smtplib.SMTP", fail)

    settings = NotificationSettings()
    send_alert_email("S", "B", settings=settings)
