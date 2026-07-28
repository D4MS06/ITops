from monitoring.services.auth_service import AuthService


class _MemoryAuthStore:
    def __init__(self, users=None):
        self.users = dict(users or {})
        self.sessions = {}

    def get_auth_user(self, *, subject):
        return self.users.get(subject)

    def upsert_auth_user(self, *, subject, label, password_hash, must_change_password, is_active=True):
        self.users[subject] = {
            "subject": subject,
            "label": label,
            "is_active": is_active,
            "password_hash": password_hash,
            "must_change_password": must_change_password,
        }

    def set_auth_user_password(self, *, subject, password_hash, must_change_password):
        row = self.users.setdefault(subject, {"subject": subject, "label": subject, "is_active": True})
        row["password_hash"] = password_hash
        row["must_change_password"] = must_change_password

    def save_auth_session(self, *, token, subject, created_at, expires_at):
        self.sessions[token] = {
            "token": token,
            "subject": subject,
            "created_at": created_at,
            "expires_at": expires_at,
        }

    def get_auth_session(self, *, token):
        return self.sessions.get(token)

    def delete_auth_session(self, *, token):
        return 1 if self.sessions.pop(token, None) else 0

    def delete_all_auth_sessions(self):
        count = len(self.sessions)
        self.sessions.clear()
        return count

    def delete_expired_auth_sessions(self, *, now_iso):
        return 0


def test_auth_service_uses_configured_session_ttl(tmp_path):
    service = AuthService(
        session_ttl_seconds=900,
        password_store_path=tmp_path / "auth.json",
    )

    assert service.session_ttl_seconds == 900


def test_auth_service_clamps_session_ttl_to_five_minutes(tmp_path):
    service = AuthService(
        session_ttl_seconds=30,
        password_store_path=tmp_path / "auth.json",
    )

    assert service.session_ttl_seconds == 300


def test_auth_service_updates_session_ttl_at_runtime(tmp_path):
    service = AuthService(
        session_ttl_seconds=900,
        password_store_path=tmp_path / "auth.json",
    )

    service.set_session_ttl_seconds(1800)

    assert service.session_ttl_seconds == 1800


def test_legacy_admin_with_empty_hash_uses_sa_password(tmp_path):
    password_hash = AuthService.hash_password("secret")
    store = _MemoryAuthStore(
        {
            "sa": {
                "subject": "sa",
                "label": "Super Admin",
                "is_active": True,
                "password_hash": password_hash,
                "must_change_password": False,
            },
            "admin": {
                "subject": "admin",
                "label": "Administrateur local",
                "is_active": True,
                "password_hash": "",
                "must_change_password": True,
            },
        }
    )
    service = AuthService(password_store_path=tmp_path / "auth.json", session_store=store)

    session = service.login("secret", username="admin")

    assert session is not None
    assert session.subject == "admin"
