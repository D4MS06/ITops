from __future__ import annotations

from typing import List

from monitoring.repositories.mariadb_base import MariaDBRepository


class StorageTargetRepository(MariaDBRepository):
    def upsert_storage_target(
        self,
        *,
        target_id: str,
        label: str,
        service_code: str,
        service_label: str,
        kind: str,
        remote_path: str,
        username: str = "",
        secret_ref: str = "",
        local_mount_path: str = "",
        auto_mount_enabled: bool = True,
        status: str = "configured",
        last_error: str = "",
    ) -> dict:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO storage_targets(
                            id, label, service_code, service_label, kind,
                            remote_path, username, secret_ref, local_mount_path,
                            auto_mount_enabled, status, last_error, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        ON DUPLICATE KEY UPDATE
                            label=VALUES(label),
                            service_code=VALUES(service_code),
                            service_label=VALUES(service_label),
                            kind=VALUES(kind),
                            remote_path=VALUES(remote_path),
                            username=VALUES(username),
                            secret_ref=VALUES(secret_ref),
                            local_mount_path=VALUES(local_mount_path),
                            auto_mount_enabled=VALUES(auto_mount_enabled),
                            status=VALUES(status),
                            last_error=VALUES(last_error),
                            updated_at=CURRENT_TIMESTAMP
                        """,
                        (
                            str(target_id),
                            str(label),
                            str(service_code),
                            str(service_label),
                            str(kind or "smb3"),
                            str(remote_path or ""),
                            str(username or ""),
                            str(secret_ref or ""),
                            str(local_mount_path or ""),
                            1 if auto_mount_enabled else 0,
                            str(status or "configured"),
                            str(last_error or ""),
                        ),
                    )
                conn.commit()
        row = self.get_storage_target(target_id=target_id)
        if row is None:
            raise ValueError("Cible de stockage non persistee.")
        return row

    def get_storage_target(self, *, target_id: str) -> dict | None:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, label, service_code, service_label, kind,
                               remote_path, username, secret_ref, local_mount_path,
                               auto_mount_enabled, status, last_error,
                               last_checked_at, created_at, updated_at
                        FROM storage_targets
                        WHERE id = %s
                        """,
                        (str(target_id),),
                    )
                    row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def list_storage_targets(self, *, service_code: str = "", limit: int = 500) -> List[dict]:
        clauses: list[str] = []
        params: list[object] = []
        if str(service_code or "").strip():
            clauses.append("service_code = %s")
            params.append(str(service_code).strip())
        params.append(max(1, min(int(limit or 500), 2000)))
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT id, label, service_code, service_label, kind,
                               remote_path, username, secret_ref, local_mount_path,
                               auto_mount_enabled, status, last_error,
                               last_checked_at, created_at, updated_at
                        FROM storage_targets
                        {where_sql}
                        ORDER BY service_label, label, id
                        LIMIT %s
                        """,
                        tuple(params),
                    )
                    rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def update_storage_target_status(
        self,
        *,
        target_id: str,
        status: str,
        last_error: str = "",
    ) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE storage_targets
                        SET status = %s,
                            last_error = %s,
                            last_checked_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (str(status or "configured"), str(last_error or ""), str(target_id)),
                    )
                    updated = int(cursor.rowcount or 0)
                conn.commit()
        return updated

    def delete_storage_target(self, *, target_id: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM storage_targets WHERE id = %s", (str(target_id),))
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
        return deleted

    @staticmethod
    def _row_to_dict(row) -> dict:
        (
            target_id,
            label,
            service_code,
            service_label,
            kind,
            remote_path,
            username,
            secret_ref,
            local_mount_path,
            auto_mount_enabled,
            status,
            last_error,
            last_checked_at,
            created_at,
            updated_at,
        ) = row
        return {
            "id": str(target_id or ""),
            "label": str(label or ""),
            "service_code": str(service_code or ""),
            "service_label": str(service_label or ""),
            "kind": str(kind or "smb3"),
            "remote_path": str(remote_path or ""),
            "username": str(username or ""),
            "secret_ref": str(secret_ref or ""),
            "local_mount_path": str(local_mount_path or ""),
            "auto_mount_enabled": bool(auto_mount_enabled),
            "status": str(status or "configured"),
            "last_error": str(last_error or ""),
            "last_checked_at": str(last_checked_at or ""),
            "created_at": str(created_at or ""),
            "updated_at": str(updated_at or ""),
        }
