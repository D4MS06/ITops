from __future__ import annotations

from typing import List

from monitoring.repositories.mariadb_base import MariaDBRepository


class ConfigVersionRepository(MariaDBRepository):
    def upsert_config_file_version(
        self,
        *,
        file_path: str,
        device_type_label: str,
        device_name: str,
        filename: str,
        detail: str = "",
    ) -> None:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO config_file_versions(
                            file_path, device_type_label, device_name, filename, detail, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON DUPLICATE KEY UPDATE
                            device_type_label=VALUES(device_type_label),
                            device_name=VALUES(device_name),
                            filename=VALUES(filename),
                            detail=VALUES(detail),
                            updated_at=CURRENT_TIMESTAMP
                        """,
                        (
                            str(file_path),
                            str(device_type_label),
                            str(device_name),
                            str(filename),
                            str(detail or ""),
                        ),
                    )
                conn.commit()

    def list_config_file_versions(
        self,
        *,
        device_type_label: str,
        device_name: str,
    ) -> List[dict]:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT file_path, filename, detail, created_at, updated_at
                        FROM config_file_versions
                        WHERE device_type_label = %s AND device_name = %s
                        ORDER BY updated_at DESC, id DESC
                        """,
                        (str(device_type_label), str(device_name)),
                    )
                    rows = cursor.fetchall()
        return [
            {
                "file_path": str(file_path),
                "filename": str(filename),
                "detail": str(detail or ""),
                "created_at": str(created_at or ""),
                "updated_at": str(updated_at or ""),
            }
            for file_path, filename, detail, created_at, updated_at in rows
        ]

    def delete_config_file_version(self, *, file_path: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM config_file_versions WHERE file_path = %s", (str(file_path),))
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    def rename_config_file_version(self, *, old_file_path: str, new_file_path: str, new_filename: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE config_file_versions
                        SET file_path = %s, filename = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE file_path = %s
                        """,
                        (str(new_file_path), str(new_filename), str(old_file_path)),
                    )
                    updated = int(cursor.rowcount or 0)
                conn.commit()
                return updated

    def delete_config_file_versions_by_type_label(self, *, device_type_label: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM config_file_versions WHERE device_type_label = %s",
                        (str(device_type_label),),
                    )
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted
