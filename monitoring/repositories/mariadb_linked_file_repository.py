from __future__ import annotations

import json
from typing import List

from monitoring.repositories.mariadb_base import MariaDBRepository


class LinkedFileRepository(MariaDBRepository):
    def upsert_linked_file(
        self,
        *,
        file_id: str,
        owner_kind: str,
        owner_id: str,
        module_code: str,
        category: str,
        filename: str,
        stored_path: str,
        mime_type: str = "",
        size_bytes: int = 0,
        sha256: str = "",
        version_label: str = "",
        detail: str = "",
        metadata_json: str = "{}",
        sync_status: str = "local_only",
        sync_error: str = "",
        created_by: str = "",
    ) -> dict:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO linked_files(
                            id, owner_kind, owner_id, module_code, category,
                            filename, stored_path, mime_type, size_bytes, sha256,
                            version_label, detail, metadata_json, sync_status,
                            sync_error, created_by, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        ON DUPLICATE KEY UPDATE
                            owner_kind=VALUES(owner_kind),
                            owner_id=VALUES(owner_id),
                            module_code=VALUES(module_code),
                            category=VALUES(category),
                            filename=VALUES(filename),
                            stored_path=VALUES(stored_path),
                            mime_type=VALUES(mime_type),
                            size_bytes=VALUES(size_bytes),
                            sha256=VALUES(sha256),
                            version_label=VALUES(version_label),
                            detail=VALUES(detail),
                            metadata_json=VALUES(metadata_json),
                            sync_status=VALUES(sync_status),
                            sync_error=VALUES(sync_error),
                            created_by=VALUES(created_by),
                            updated_at=CURRENT_TIMESTAMP
                        """,
                        (
                            str(file_id),
                            str(owner_kind),
                            str(owner_id),
                            str(module_code),
                            str(category),
                            str(filename),
                            str(stored_path),
                            str(mime_type or ""),
                            int(size_bytes or 0),
                            str(sha256 or ""),
                            str(version_label or ""),
                            str(detail or ""),
                            str(metadata_json or "{}"),
                            str(sync_status or "local_only"),
                            str(sync_error or ""),
                            str(created_by or ""),
                        ),
                    )
                conn.commit()
        row = self.get_linked_file(file_id=file_id)
        if row is None:
            raise ValueError("Fichier lie non persiste.")
        return row

    def get_linked_file(self, *, file_id: str) -> dict | None:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, owner_kind, owner_id, module_code, category,
                               filename, stored_path, mime_type, size_bytes, sha256,
                               version_label, detail, metadata_json, sync_status,
                               sync_error, created_by, created_at, updated_at
                        FROM linked_files
                        WHERE id = %s
                        """,
                        (str(file_id),),
                    )
                    row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def get_linked_file_by_stored_path(self, *, stored_path: str) -> dict | None:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, owner_kind, owner_id, module_code, category,
                               filename, stored_path, mime_type, size_bytes, sha256,
                               version_label, detail, metadata_json, sync_status,
                               sync_error, created_by, created_at, updated_at
                        FROM linked_files
                        WHERE stored_path = %s
                        """,
                        (str(stored_path),),
                    )
                    row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def list_linked_files_by_stored_path_prefix(self, *, stored_path: str, child_path_pattern: str, limit: int = 10000) -> List[dict]:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, owner_kind, owner_id, module_code, category,
                               filename, stored_path, mime_type, size_bytes, sha256,
                               version_label, detail, metadata_json, sync_status,
                               sync_error, created_by, created_at, updated_at
                        FROM linked_files
                        WHERE stored_path = %s OR stored_path LIKE %s
                        ORDER BY updated_at DESC, id DESC
                        LIMIT %s
                        """,
                        (str(stored_path), str(child_path_pattern), max(1, min(int(limit or 10000), 10000))),
                    )
                    rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_linked_files(
        self,
        *,
        owner_kind: str,
        owner_id: str,
        category: str = "",
        module_code: str = "",
        limit: int = 200,
    ) -> List[dict]:
        clauses = ["owner_kind = %s", "owner_id = %s"]
        params: list[object] = [str(owner_kind), str(owner_id)]
        if str(category or "").strip():
            clauses.append("category = %s")
            params.append(str(category).strip())
        if str(module_code or "").strip():
            clauses.append("module_code = %s")
            params.append(str(module_code).strip())
        params.append(max(1, min(int(limit or 200), 1000)))
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT id, owner_kind, owner_id, module_code, category,
                               filename, stored_path, mime_type, size_bytes, sha256,
                               version_label, detail, metadata_json, sync_status,
                               sync_error, created_by, created_at, updated_at
                        FROM linked_files
                        WHERE {' AND '.join(clauses)}
                        ORDER BY updated_at DESC, id DESC
                        LIMIT %s
                        """,
                        tuple(params),
                    )
                    rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_linked_files_by_module_category(
        self,
        *,
        module_code: str,
        category: str,
        limit: int = 1000,
    ) -> List[dict]:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, owner_kind, owner_id, module_code, category,
                               filename, stored_path, mime_type, size_bytes, sha256,
                               version_label, detail, metadata_json, sync_status,
                               sync_error, created_by, created_at, updated_at
                        FROM linked_files
                        WHERE module_code = %s AND category = %s
                        ORDER BY updated_at DESC, id DESC
                        LIMIT %s
                        """,
                        (str(module_code), str(category), max(1, min(int(limit or 1000), 10000))),
                    )
                    rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def update_linked_file_sync_state(
        self,
        *,
        file_id: str,
        sync_status: str,
        sync_error: str = "",
    ) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE linked_files
                        SET sync_status = %s,
                            sync_error = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (str(sync_status or "local_only"), str(sync_error or ""), str(file_id)),
                    )
                    updated = int(cursor.rowcount or 0)
                conn.commit()
        return updated

    def delete_linked_file(self, *, file_id: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM linked_files WHERE id = %s", (str(file_id),))
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
        return deleted

    @staticmethod
    def _row_to_dict(row) -> dict:
        (
            file_id,
            owner_kind,
            owner_id,
            module_code,
            category,
            filename,
            stored_path,
            mime_type,
            size_bytes,
            sha256,
            version_label,
            detail,
            metadata_json,
            sync_status,
            sync_error,
            created_by,
            created_at,
            updated_at,
        ) = row
        try:
            metadata = json.loads(str(metadata_json or "{}"))
        except Exception:
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        return {
            "id": str(file_id or ""),
            "owner_kind": str(owner_kind or ""),
            "owner_id": str(owner_id or ""),
            "module_code": str(module_code or ""),
            "category": str(category or ""),
            "filename": str(filename or ""),
            "stored_path": str(stored_path or ""),
            "mime_type": str(mime_type or ""),
            "size_bytes": int(size_bytes or 0),
            "sha256": str(sha256 or ""),
            "version_label": str(version_label or ""),
            "detail": str(detail or ""),
            "metadata": {str(key): str(value or "") for key, value in metadata.items()},
            "sync_status": str(sync_status or "local_only"),
            "sync_error": str(sync_error or ""),
            "created_by": str(created_by or ""),
            "created_at": str(created_at or ""),
            "updated_at": str(updated_at or ""),
        }
