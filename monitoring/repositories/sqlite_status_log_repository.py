from __future__ import annotations

from datetime import datetime
from typing import List

from monitoring.repositories.sqlite_base import SQLiteRepository


class StatusLogRepository(SQLiteRepository):
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
                conn.execute(
                    """
                    INSERT INTO status_logs(
                        created_at, dtype, device_id, device_name, old_status, new_status, event_kind, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            where_parts.append("dtype = ?")
            args.append(str(dtype))
        if device_id:
            where_parts.append("device_id = ?")
            args.append(str(device_id))
        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)
        query += " ORDER BY id DESC LIMIT ?"
        args.append(max(1, int(limit or 300)))

        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                rows = conn.execute(query, args).fetchall()
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
            where_parts.append("dtype = ?")
            args.append(str(dtype))
        if device_id:
            where_parts.append("device_id = ?")
            args.append(str(device_id))
        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                cur = conn.execute(query, args)
                conn.commit()
                return int(cur.rowcount or 0)

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
            where_parts.append("dtype = ?")
            args.append(str(dtype))
        if device_id:
            where_parts.append("device_id = ?")
            args.append(str(device_id))
        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                row = conn.execute(query, args).fetchone()
        return int((row[0] if row else 0) or 0)
