from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from monitoring.services.auth_service import AuthService, AuthSession
from monitoring.storage.sqlite_manager import SQLiteFileManager


def test_auth_service_hashes_and_verifies_admin_password(tmp_path):
    stored = {}

    def fake_set_password(_service, account, value):
        stored[account] = value

    def fake_get_password(_service, account):
        return stored.get(account, "")

    with patch("monitoring.services.auth_service.keyring.set_password", side_effect=fake_set_password), patch(
        "monitoring.services.auth_service.keyring.get_password",
        side_effect=fake_get_password,
    ):
        service = AuthService(session_ttl_seconds=300, password_store_path=tmp_path / "auth.json")
        assert service.has_admin_password() is False

        service.set_admin_password("admin-pass")
        assert service.has_admin_password() is True
        assert stored[service._password_account] != "admin-pass"
        assert service.verify_admin_password("admin-pass") is True
        assert service.verify_admin_password("bad-pass") is False


def test_auth_service_login_validate_and_logout(tmp_path):
    password_hash = AuthService.hash_password("admin-pass")

    with patch(
        "monitoring.services.auth_service.keyring.get_password",
        return_value=password_hash,
    ):
        service = AuthService(session_ttl_seconds=300, password_store_path=tmp_path / "auth.json")
        session = service.login("admin-pass")

        assert session is not None
        assert session.subject == AuthService.SUBJECT_ADMIN
        assert service.validate_session(session.token) is True
        assert service.logout(session.token) is True
        assert service.validate_session(session.token) is False


def test_auth_service_rejects_invalid_password_and_expires_sessions(tmp_path):
    password_hash = AuthService.hash_password("admin-pass")

    with patch(
        "monitoring.services.auth_service.keyring.get_password",
        return_value=password_hash,
    ):
        service = AuthService(session_ttl_seconds=300, password_store_path=tmp_path / "auth.json")
        assert service.login("wrong-pass") is None

        session = service.login("admin-pass")
        assert session is not None

        expired = AuthSession(
            token=session.token,
            subject=session.subject,
            created_at=session.created_at,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        service._sessions[session.token] = expired

        assert service.get_session(session.token) is None
        assert service.validate_session(session.token) is False


def test_auth_service_requires_non_empty_password(tmp_path):
    service = AuthService(password_store_path=tmp_path / "auth.json")
    with pytest.raises(ValueError, match="Mot de passe administrateur requis"):
        service.set_admin_password("")


def test_auth_service_persists_sessions_with_session_store(tmp_path):
    password_hash = AuthService.hash_password("admin-pass")

    def fake_init(self, _db_name="devices.db"):
        self.data_dir = str(tmp_path)
        self.db_path = str(tmp_path / _db_name)

    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.__init__",
        fake_init,
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json",
        lambda self, conn: None,
    ), patch(
        "monitoring.services.auth_service.keyring.get_password",
        return_value=password_hash,
    ):
        manager = SQLiteFileManager()
        store_path = tmp_path / "auth.json"
        service = AuthService(session_ttl_seconds=300, password_store_path=store_path, session_store=manager)
        session = service.login("admin-pass")

        assert session is not None

        other_service = AuthService(session_ttl_seconds=300, password_store_path=store_path, session_store=manager)
        restored = other_service.get_session(session.token)

        assert restored is not None
        assert restored.token == session.token
        assert other_service.logout(session.token) is True
        assert service.get_session(session.token) is None


def test_auth_service_fallback_password_store_when_keyring_unavailable(tmp_path):
    store_path = tmp_path / "auth.json"

    def failing_set_password(*_args, **_kwargs):
        raise RuntimeError("keyring unavailable")

    with patch("monitoring.services.auth_service.keyring.get_password", return_value=""), patch(
        "monitoring.services.auth_service.keyring.set_password",
        side_effect=failing_set_password,
    ):
        service = AuthService(password_store_path=store_path)
        service.set_admin_password("admin-pass")

    with patch("monitoring.services.auth_service.keyring.get_password", return_value=""):
        reloaded = AuthService(password_store_path=store_path)
        assert reloaded.has_admin_password() is True
        assert reloaded.verify_admin_password("admin-pass") is True
        assert reloaded.login("admin-pass") is not None
