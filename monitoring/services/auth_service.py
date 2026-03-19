from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from monitoring.config.settings import ADMIN_PASSWORD_HASH_ACCOUNT, KEYRING_SERVICE, keyring
from monitoring.utils.logger import log_with_timestamp


class SessionStore(Protocol):
    def save_auth_session(self, *, token: str, subject: str, created_at: str, expires_at: str) -> None: ...
    def get_auth_session(self, *, token: str) -> dict | None: ...
    def delete_auth_session(self, *, token: str) -> int: ...
    def delete_all_auth_sessions(self) -> int: ...
    def delete_expired_auth_sessions(self, *, now_iso: str) -> int: ...


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

    @staticmethod
    def _default_password_store_path() -> Path:
        app_data_root = Path(os.environ.get("LOCALAPPDATA") or str(Path.home()))
        return app_data_root / "NetworkMonitoringProject" / "config" / "auth.json"

    def __init__(
        self,
        *,
        session_ttl_seconds: int = 3600,
        keyring_service: str = KEYRING_SERVICE,
        password_account: str = ADMIN_PASSWORD_HASH_ACCOUNT,
        password_store_path: str | Path | None = None,
        session_store: SessionStore | None = None,
    ) -> None:
        self.session_ttl_seconds = max(60, int(session_ttl_seconds or 3600))
        self._keyring_service = keyring_service
        self._password_account = password_account
        self._password_store_path = Path(password_store_path) if password_store_path else self._default_password_store_path()
        self._session_store = session_store
        self._sessions: dict[str, AuthSession] = {}
        self._lock = threading.Lock()

    def has_admin_password(self) -> bool:
        return bool(self._load_password_hash())

    def set_admin_password(self, password: str) -> None:
        normalized = self._normalize_password(password)
        encoded = self.hash_password(normalized)
        self._save_password_hash_file(encoded)
        try:
            keyring.set_password(self._keyring_service, self._password_account, encoded)
        except Exception as exc:
            log_with_timestamp(f"Ecriture keyring impossible, fallback fichier actif: {exc}", level="WARNING")
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
            self._store_session_locked(session)
        return session

    def logout(self, token: str) -> bool:
        normalized = str(token or "").strip()
        if not normalized:
            return False
        with self._lock:
            if self._session_store is not None:
                return self._session_store.delete_auth_session(token=normalized) > 0
            return self._sessions.pop(normalized, None) is not None

    def validate_session(self, token: str) -> bool:
        return self.get_session(token) is not None

    def get_session(self, token: str) -> AuthSession | None:
        normalized = str(token or "").strip()
        if not normalized:
            return None
        with self._lock:
            self._purge_expired_sessions_locked()
            session = self._load_session_locked(normalized)
            if session is None or session.is_expired:
                self._delete_session_locked(normalized)
                return None
            return session

    def revoke_all_sessions(self) -> None:
        with self._lock:
            if self._session_store is not None:
                self._session_store.delete_all_auth_sessions()
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
        except (TypeError, ValueError) as exc:
            log_with_timestamp(f"Hash admin invalide: {exc}", level="WARNING")
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
            from_keyring = str(keyring.get_password(self._keyring_service, self._password_account) or "").strip()
            if from_keyring:
                return from_keyring
        except Exception as exc:
            log_with_timestamp(f"Lecture keyring impossible: {exc}", level="WARNING")
        return self._load_password_hash_file()

    def _load_password_hash_file(self) -> str:
        try:
            if not self._password_store_path.is_file():
                return ""
            payload = json.loads(self._password_store_path.read_text(encoding="utf-8"))
            return str(payload.get("admin_password_hash", "") or "").strip()
        except Exception as exc:
            log_with_timestamp(f"Lecture fallback auth impossible: {exc}", level="WARNING")
            return ""

    def _save_password_hash_file(self, password_hash: str) -> None:
        try:
            self._password_store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"admin_password_hash": str(password_hash or "").strip()}
            self._password_store_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            log_with_timestamp(f"Ecriture fallback auth impossible: {exc}", level="WARNING")

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
        if self._session_store is not None:
            self._session_store.delete_expired_auth_sessions(now_iso=now.isoformat())
            return
        for token, session in list(self._sessions.items()):
            if now >= session.expires_at:
                self._sessions.pop(token, None)

    def _store_session_locked(self, session: AuthSession) -> None:
        if self._session_store is not None:
            self._session_store.save_auth_session(
                token=session.token,
                subject=session.subject,
                created_at=session.created_at.isoformat(),
                expires_at=session.expires_at.isoformat(),
            )
            return
        self._sessions[session.token] = session

    def _load_session_locked(self, token: str) -> AuthSession | None:
        if self._session_store is None:
            return self._sessions.get(token)
        row = self._session_store.get_auth_session(token=token)
        if row is None:
            return None
        try:
            return AuthSession(
                token=str(row["token"]),
                subject=str(row["subject"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
                expires_at=datetime.fromisoformat(str(row["expires_at"])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            log_with_timestamp(f"Session auth corrompue supprimee: {exc}", level="WARNING")
            self._session_store.delete_auth_session(token=token)
            return None

    def _delete_session_locked(self, token: str) -> None:
        if self._session_store is not None:
            self._session_store.delete_auth_session(token=token)
            return
        self._sessions.pop(token, None)

    @staticmethod
    def _normalize_password(password: str) -> str:
        normalized = str(password or "")
        if not normalized:
            raise ValueError("Mot de passe administrateur requis.")
        return normalized
