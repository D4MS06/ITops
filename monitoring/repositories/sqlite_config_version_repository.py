from __future__ import annotations

from typing import List

from monitoring.repositories.sqlite_base import SQLiteRepository


class ConfigVersionRepository(SQLiteRepository):
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
                conn.execute(
                    """
                    INSERT INTO config_file_versions(
                        file_path, device_type_label, device_name, filename, detail, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(file_path) DO UPDATE SET
                        device_type_label=excluded.device_type_label,
                        device_name=excluded.device_name,
                        filename=excluded.filename,
                        detail=excluded.detail,
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
                rows = conn.execute(
                    """
                    SELECT file_path, filename, detail, created_at, updated_at
                    FROM config_file_versions
                    WHERE device_type_label = ? AND device_name = ?
                    ORDER BY updated_at DESC, id DESC
                    """,
                    (str(device_type_label), str(device_name)),
                ).fetchall()
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
                cur = conn.execute("DELETE FROM config_file_versions WHERE file_path = ?", (str(file_path),))
                conn.commit()
                return int(cur.rowcount or 0)

    def rename_config_file_version(self, *, old_file_path: str, new_file_path: str, new_filename: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    UPDATE config_file_versions
                    SET file_path = ?, filename = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE file_path = ?
                    """,
                    (str(new_file_path), str(new_filename), str(old_file_path)),
                )
                conn.commit()
                return int(cur.rowcount or 0)

    def delete_config_file_versions_by_type_label(self, *, device_type_label: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM config_file_versions WHERE device_type_label = ?",
                    (str(device_type_label),),
                )
                conn.commit()
                return int(cur.rowcount or 0)
