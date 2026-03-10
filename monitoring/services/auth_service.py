from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from monitoring.config.settings import ADMIN_PASSWORD_HASH_ACCOUNT, KEYRING_SERVICE, keyring


@dataclass(frozen=True)
class AuthSession:
    token: str
    subject: str
    created_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


class AuthService:
    """Authentification locale admin avec hash PBKDF2 et sessions tokenisees."""

    HASH_SCHEME = "pbkdf2_sha256"
    HASH_ITERATIONS = 600_000
    SUBJECT_ADMIN = "admin"

    def __init__(
        self,
        *,
        session_ttl_seconds: int = 3600,
        keyring_service: str = KEYRING_SERVICE,
        password_account: str = ADMIN_PASSWORD_HASH_ACCOUNT,
    ) -> None:
        self.session_ttl_seconds = max(60, int(session_ttl_seconds or 3600))
        self._keyring_service = keyring_service
        self._password_account = password_account
        self._sessions: dict[str, AuthSession] = {}
        self._lock = threading.Lock()

    def has_admin_password(self) -> bool:
        return bool(self._load_password_hash())

    def set_admin_password(self, password: str) -> None:
        normalized = self._normalize_password(password)
        encoded = self.hash_password(normalized)
        keyring.set_password(self._keyring_service, self._password_account, encoded)
        self.revoke_all_sessions()

    def verify_admin_password(self, password: str) -> bool:
        stored_hash = self._load_password_hash()
        if not stored_hash:
            return False
        return self.verify_password(password, stored_hash)

    def login(self, password: str) -> AuthSession | None:
        if not self.verify_admin_password(password):
            return None
        session = self._build_session()
        with self._lock:
            self._purge_expired_sessions_locked()
            self._sessions[session.token] = session
        return session

    def logout(self, token: str) -> bool:
        normalized = str(token or "").strip()
        if not normalized:
            return False
        with self._lock:
            return self._sessions.pop(normalized, None) is not None

    def validate_session(self, token: str) -> bool:
        return self.get_session(token) is not None

    def get_session(self, token: str) -> AuthSession | None:
        normalized = str(token or "").strip()
        if not normalized:
            return None
        with self._lock:
            self._purge_expired_sessions_locked()
            session = self._sessions.get(normalized)
            if session is None or session.is_expired:
                self._sessions.pop(normalized, None)
                return None
            return session

    def revoke_all_sessions(self) -> None:
        with self._lock:
            self._sessions.clear()

    @classmethod
    def hash_password(cls, password: str) -> str:
        normalized = cls._normalize_password(password)
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            normalized.encode("utf-8"),
            salt,
            cls.HASH_ITERATIONS,
        )
        return (
            f"{cls.HASH_SCHEME}$"
            f"{cls.HASH_ITERATIONS}$"
            f"{salt.hex()}$"
            f"{digest.hex()}"
        )

    @classmethod
    def verify_password(cls, password: str, stored_hash: str) -> bool:
        try:
            scheme, iterations_raw, salt_hex, digest_hex = str(stored_hash or "").split("$", 3)
        except ValueError:
            return False
        if scheme != cls.HASH_SCHEME:
            return False
        try:
            iterations = int(iterations_raw)
            salt = bytes.fromhex(salt_hex)
            expected_digest = bytes.fromhex(digest_hex)
        except Exception:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            cls._normalize_password(password).encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(candidate, expected_digest)

    def _load_password_hash(self) -> str:
        try:
            return str(keyring.get_password(self._keyring_service, self._password_account) or "").strip()
        except Exception:
            return ""

    def _build_session(self) -> AuthSession:
        now = datetime.now(timezone.utc)
        return AuthSession(
            token=secrets.token_urlsafe(32),
            subject=self.SUBJECT_ADMIN,
            created_at=now,
            expires_at=now + timedelta(seconds=self.session_ttl_seconds),
        )

    def _purge_expired_sessions_locked(self) -> None:
        now = datetime.now(timezone.utc)
        for token, session in list(self._sessions.items()):
            if now >= session.expires_at:
                self._sessions.pop(token, None)

    @staticmethod
    def _normalize_password(password: str) -> str:
        normalized = str(password or "")
        if not normalized:
            raise ValueError("Mot de passe administrateur requis.")
        return normalized
