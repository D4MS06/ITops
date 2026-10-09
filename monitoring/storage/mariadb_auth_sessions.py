from __future__ import annotations


class AuthSessionRepository:
    def __init__(self, *, connect, ensure_database, lock) -> None:
        self._connect = connect
        self._ensure_database = ensure_database
        self._lock = lock

    def save_auth_session(self, *, token: str, subject: str, created_at: str, expires_at: str) -> None:
        self._ensure_database()
        with self._lock, self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO auth_sessions(token, subject, created_at, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        subject=VALUES(subject),
                        created_at=VALUES(created_at),
                        expires_at=VALUES(expires_at)
                    """,
                    (str(token), str(subject), str(created_at), str(expires_at)),
                )
            conn.commit()

    def get_auth_session(self, *, token: str) -> dict | None:
        self._ensure_database()
        with self._lock, self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT token, subject, created_at, expires_at
                    FROM auth_sessions
                    WHERE token = %s
                    """,
                    (str(token),),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return {
            "token": str(row[0]),
            "subject": str(row[1]),
            "created_at": str(row[2]),
            "expires_at": str(row[3]),
        }

    def delete_auth_session(self, *, token: str) -> int:
        self._ensure_database()
        with self._lock, self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM auth_sessions WHERE token = %s", (str(token),))
                deleted = int(cursor.rowcount or 0)
            conn.commit()
            return deleted

    def delete_all_auth_sessions(self) -> int:
        self._ensure_database()
        with self._lock, self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM auth_sessions")
                deleted = int(cursor.rowcount or 0)
            conn.commit()
            return deleted

    def delete_expired_auth_sessions(self, *, now_iso: str) -> int:
        self._ensure_database()
        with self._lock, self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM auth_sessions WHERE expires_at <= %s", (str(now_iso),))
                deleted = int(cursor.rowcount or 0)
            conn.commit()
            return deleted
