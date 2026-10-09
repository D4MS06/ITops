from __future__ import annotations

from datetime import datetime
from typing import List

from monitoring.repositories.mariadb_base import MariaDBRepository


class StatusLogRepository(MariaDBRepository):
    def record_status_log(
        self,
        *,
        dtype: str,
        device_id: str,
        device_name: str,
        old_status: str,
        new_status: str,
        event_kind: str = "status_change",
        details: str = "",
    ) -> None:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO status_logs(
                            created_at, dtype, device_id, device_name, old_status, new_status, event_kind, details
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            str(dtype),
                            str(device_id),
                            str(device_name),
                            str(old_status),
                            str(new_status),
                            str(event_kind or "status_change"),
                            str(details or ""),
                        ),
                    )
                conn.commit()

    def list_status_logs(
        self,
        *,
        limit: int = 300,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> List[dict]:
        query = (
            "SELECT created_at, dtype, device_id, device_name, old_status, new_status, event_kind, details "
            "FROM status_logs"
        )
        args: list = []
        where_parts: list[str] = []
        if dtype:
            where_parts.append("dtype = %s")
            args.append(str(dtype))
        if device_id:
            where_parts.append("device_id = %s")
            args.append(str(device_id))
        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)
        query += " ORDER BY id DESC LIMIT %s"
        args.append(max(1, int(limit or 300)))

        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, args)
                    rows = cursor.fetchall()
        return [
            {
                "created_at": str(created_at),
                "dtype": str(dt),
                "device_id": str(did),
                "device_name": str(dname),
                "old_status": str(old_status),
                "new_status": str(new_status),
                "event_kind": str(event_kind or "status_change"),
                "details": str(details or ""),
            }
            for created_at, dt, did, dname, old_status, new_status, event_kind, details in rows
        ]

    def delete_status_logs(
        self,
        *,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> int:
        query = "DELETE FROM status_logs"
        args: list = []
        where_parts: list[str] = []
        if dtype:
            where_parts.append("dtype = %s")
            args.append(str(dtype))
        if device_id:
            where_parts.append("device_id = %s")
            args.append(str(device_id))
        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, args)
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    def count_status_logs(
        self,
        *,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> int:
        query = "SELECT COUNT(*) FROM status_logs"
        args: list = []
        where_parts: list[str] = []
        if dtype:
            where_parts.append("dtype = %s")
            args.append(str(dtype))
        if device_id:
            where_parts.append("device_id = %s")
            args.append(str(device_id))
        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, args)
                    row = cursor.fetchone()
        return int((row[0] if row else 0) or 0)
