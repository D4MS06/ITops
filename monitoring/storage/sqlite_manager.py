from __future__ import annotations

import os
import sqlite3
import threading
from typing import Dict, List

from monitoring.repositories.sqlite_repositories import (
    ConfigVersionRepository,
    DeviceRepository,
    DeviceTypeRepository,
    StatusLogRepository,
)
from monitoring.storage.db_backend import resolve_storage_backend
from monitoring.storage.sqlite_auth_sessions import AuthSessionRepository
from monitoring.storage.sqlite_bootstrap import SQLiteBootstrapper
from monitoring.utils.logger import log_with_timestamp


class SQLiteFileManager:
    _lock = threading.Lock()
    OS_FIELD_OPTIONS = "Windows,Linux,Firmware,Autre"
    OS_FIELD_DEFAULT = "Windows"
    ALL_OS_SCOPE = "windows,linux,firmware,autre"

    def __new__(cls, *args, **kwargs):
        if cls is SQLiteFileManager and resolve_storage_backend() == "mariadb":
            from monitoring.storage.mariadb_manager import MariaDBFileManager

            return MariaDBFileManager(*args, **kwargs)
        return super().__new__(cls)

    @staticmethod
    def _normalize_os_key(value: str) -> str:
        raw = str(value or "").strip().lower()
        return raw if raw in {"windows", "linux", "firmware", "autre"} else "autre"

    @staticmethod
    def _format_os_scope(values: list[str]) -> str:
        ordered = []
        seen: set[str] = set()
        for value in values:
            key = SQLiteFileManager._normalize_os_key(value)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(key)
        return ",".join(ordered)

    def __init__(self, db_name: str = "devices.db") -> None:
        local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        self.data_dir = os.path.join(local_app_data, "NetworkMonitoringProject", "data")
        self.db_path = os.path.join(self.data_dir, db_name)
        self._init_repositories()

    def _init_repositories(self) -> None:
        self.devices = DeviceRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )
        self.device_types = DeviceTypeRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )
        self.status_logs = StatusLogRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )
        self.config_versions = ConfigVersionRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )
        self.auth_sessions = AuthSessionRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )

    def _ensure_repositories(self) -> None:
        if not all(hasattr(self, attr) for attr in ("devices", "device_types", "status_logs", "config_versions", "auth_sessions")):
            self._init_repositories()

    def _repo(self, attr: str):
        self._ensure_repositories()
        return getattr(self, attr)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_database(self) -> None:
        SQLiteBootstrapper.ensure_database(self)

    @staticmethod
    def _ensure_status_logs_columns(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_status_logs_columns(conn)

    @staticmethod
    def _ensure_devices_columns(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_devices_columns(conn)

    @staticmethod
    def _ensure_device_type_actions_columns(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_device_type_actions_columns(conn)

    @staticmethod
    def _ensure_device_types_columns(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_device_types_columns(conn)

    @staticmethod
    def _ensure_auth_users_columns(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_auth_users_columns(conn)

    @staticmethod
    def _ensure_default_schema_rows(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_default_schema_rows(conn, SQLiteFileManager)

    def _seed_from_json(self, conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.seed_from_json(conn)

    @staticmethod
    def _seed_default_device_types(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.seed_default_device_types(conn, SQLiteFileManager)

    @staticmethod
    def _ensure_os_field_rows(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_os_field_rows(conn, SQLiteFileManager)

    @staticmethod
    def _ensure_action_os_scope_rows(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_action_os_scope_rows(conn, SQLiteFileManager)

    @staticmethod
    def _ensure_auth_rbac_rows(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_auth_rbac_rows(conn)

    def read_devices_map(self) -> Dict[str, List[dict]]:
        return self._repo("devices").read_devices_map()

    def list_device_types(self) -> List[dict]:
        return self._repo("device_types").list_device_types()

    def list_type_fields(self, type_code: str) -> List[dict]:
        return self._repo("device_types").list_type_fields(type_code)

    def list_type_actions(self, type_code: str) -> List[dict]:
        return self._repo("device_types").list_type_actions(type_code)

    def save_device_type(
        self,
        *,
        code: str,
        label: str,
        template_code: str | None = None,
        monitoring_enabled: bool = True,
        config_backups_enabled: bool | None = None,
        rebuild_schema: bool = False,
    ) -> str:
        return self._repo("device_types").save_device_type(
            code=code,
            label=label,
            template_code=template_code,
            monitoring_enabled=monitoring_enabled,
            config_backups_enabled=config_backups_enabled,
            rebuild_schema=rebuild_schema,
        )

    def count_devices_by_type(self, code: str) -> int:
        return self._repo("device_types").count_devices_by_type(code)

    def delete_device_type(self, code: str, *, cascade_devices: bool = False) -> bool:
        return self._repo("device_types").delete_device_type(code, cascade_devices=cascade_devices)

    def replace_type_schema(
        self,
        *,
        type_code: str,
        fields: List[dict],
        actions: List[dict],
    ) -> None:
        self._repo("device_types").replace_type_schema(type_code=type_code, fields=fields, actions=actions)

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
        self._repo("status_logs").record_status_log(
            dtype=dtype,
            device_id=device_id,
            device_name=device_name,
            old_status=old_status,
            new_status=new_status,
            event_kind=event_kind,
            details=details,
        )

    def list_status_logs(
        self,
        *,
        limit: int = 300,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> List[dict]:
        return self._repo("status_logs").list_status_logs(limit=limit, dtype=dtype, device_id=device_id)

    def delete_status_logs(
        self,
        *,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> int:
        return self._repo("status_logs").delete_status_logs(dtype=dtype, device_id=device_id)

    def count_status_logs(
        self,
        *,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> int:
        return self._repo("status_logs").count_status_logs(dtype=dtype, device_id=device_id)

    def upsert_config_file_version(
        self,
        *,
        file_path: str,
        device_type_label: str,
        device_name: str,
        filename: str,
        detail: str = "",
    ) -> None:
        self._repo("config_versions").upsert_config_file_version(
            file_path=file_path,
            device_type_label=device_type_label,
            device_name=device_name,
            filename=filename,
            detail=detail,
        )

    def list_config_file_versions(
        self,
        *,
        device_type_label: str,
        device_name: str,
    ) -> List[dict]:
        return self._repo("config_versions").list_config_file_versions(
            device_type_label=device_type_label,
            device_name=device_name,
        )

    def delete_config_file_version(self, *, file_path: str) -> int:
        return self._repo("config_versions").delete_config_file_version(file_path=file_path)

    def rename_config_file_version(self, *, old_file_path: str, new_file_path: str, new_filename: str) -> int:
        return self._repo("config_versions").rename_config_file_version(
            old_file_path=old_file_path,
            new_file_path=new_file_path,
            new_filename=new_filename,
        )

    def delete_config_file_versions_by_type_label(self, *, device_type_label: str) -> int:
        return self._repo("config_versions").delete_config_file_versions_by_type_label(
            device_type_label=device_type_label
        )

    def upsert_device(self, *, dtype: str, item: dict) -> None:
        self._repo("devices").upsert_device(dtype=dtype, item=item)

    def delete_device(self, *, device_id: str) -> int:
        return self._repo("devices").delete_device(device_id=device_id)

    def write_devices_map(self, data: Dict[str, List[dict]]) -> None:
        self._repo("devices").write_devices_map(data)
        total = sum(len(items) for items in data.values())
        log_with_timestamp(f"Ecriture SQLite reussie ({total} equipements).", level="DEBUG")

    def save_auth_session(self, *, token: str, subject: str, created_at: str, expires_at: str) -> None:
        self._repo("auth_sessions").save_auth_session(
            token=token,
            subject=subject,
            created_at=created_at,
            expires_at=expires_at,
        )

    def get_auth_session(self, *, token: str) -> dict | None:
        return self._repo("auth_sessions").get_auth_session(token=token)

    def delete_auth_session(self, *, token: str) -> int:
        return self._repo("auth_sessions").delete_auth_session(token=token)

    def delete_all_auth_sessions(self) -> int:
        return self._repo("auth_sessions").delete_all_auth_sessions()

    def delete_expired_auth_sessions(self, *, now_iso: str) -> int:
        return self._repo("auth_sessions").delete_expired_auth_sessions(now_iso=now_iso)

    def list_subject_modules(self, *, subject: str) -> List[dict]:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT
                        m.code,
                        m.label,
                        m.route_path,
                        m.is_active,
                        CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM auth_users u
                                JOIN auth_user_roles ur ON ur.subject = u.subject
                                JOIN auth_role_modules rm ON rm.role_code = ur.role_code
                                WHERE u.subject = ?
                                  AND u.is_active = 1
                                  AND rm.module_code = m.code
                            ) THEN 1
                            ELSE 0
                        END AS granted
                    FROM auth_modules m
                    ORDER BY m.sort_order, m.label
                    """,
                    (str(subject or "").strip(),),
                ).fetchall()
        return [
            {
                "code": str(code),
                "label": str(label),
                "route_path": str(route_path),
                "is_active": bool(is_active),
                "granted": bool(granted),
            }
            for code, label, route_path, is_active, granted in rows
        ]

    def subject_has_module(self, *, subject: str, module_code: str) -> bool:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM auth_users u
                    JOIN auth_user_roles ur ON ur.subject = u.subject
                    JOIN auth_role_modules rm ON rm.role_code = ur.role_code
                    JOIN auth_modules m ON m.code = rm.module_code
                    WHERE u.subject = ?
                      AND u.is_active = 1
                      AND m.code = ?
                      AND m.is_active = 1
                    """,
                    (str(subject or "").strip(), str(module_code or "").strip()),
                ).fetchone()
        return bool(int((row[0] if row else 0) or 0))

    def get_auth_user(self, *, subject: str) -> dict | None:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT subject, label, is_active, password_hash, must_change_password
                    FROM auth_users
                    WHERE subject = ?
                    """,
                    (str(subject or "").strip().lower(),),
                ).fetchone()
        if row is None:
            return None
        return {
            "subject": str(row[0]),
            "label": str(row[1]),
            "is_active": bool(row[2]),
            "password_hash": str(row[3] or ""),
            "must_change_password": bool(row[4]),
        }

    def upsert_auth_user(
        self,
        *,
        subject: str,
        label: str,
        password_hash: str,
        must_change_password: bool,
        is_active: bool = True,
    ) -> None:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO auth_users(subject, label, is_active, password_hash, must_change_password)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(subject) DO UPDATE SET
                        label=excluded.label,
                        is_active=excluded.is_active,
                        password_hash=excluded.password_hash,
                        must_change_password=excluded.must_change_password
                    """,
                    (
                        str(subject or "").strip().lower(),
                        str(label or "").strip(),
                        1 if bool(is_active) else 0,
                        str(password_hash or "").strip(),
                        1 if bool(must_change_password) else 0,
                    ),
                )
                conn.commit()

    def set_auth_user_password(self, *, subject: str, password_hash: str, must_change_password: bool) -> None:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE auth_users
                    SET password_hash = ?, must_change_password = ?
                    WHERE subject = ?
                    """,
                    (
                        str(password_hash or "").strip(),
                        1 if bool(must_change_password) else 0,
                        str(subject or "").strip().lower(),
                    ),
                )
                conn.commit()

    def list_auth_modules(self) -> List[dict]:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT code, label, route_path, is_active, sort_order
                    FROM auth_modules
                    ORDER BY sort_order, label
                    """
                ).fetchall()
        return [
            {
                "code": str(code),
                "label": str(label),
                "route_path": str(route_path),
                "is_active": bool(is_active),
                "sort_order": int(sort_order or 0),
            }
            for code, label, route_path, is_active, sort_order in rows
        ]

    def list_auth_roles(self) -> List[dict]:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                role_rows = conn.execute(
                    """
                    SELECT code, label, is_system, sort_order
                    FROM auth_roles
                    ORDER BY sort_order, label
                    """
                ).fetchall()
                module_rows = conn.execute(
                    """
                    SELECT role_code, module_code
                    FROM auth_role_modules
                    """
                ).fetchall()
        module_map: dict[str, list[str]] = {}
        for role_code, module_code in module_rows:
            key = str(role_code)
            module_map.setdefault(key, []).append(str(module_code))
        return [
            {
                "code": str(code),
                "label": str(label),
                "is_system": bool(is_system),
                "sort_order": int(sort_order or 0),
                "module_codes": sorted(module_map.get(str(code), [])),
            }
            for code, label, is_system, sort_order in role_rows
        ]

    def save_auth_role(self, *, code: str, label: str, module_codes: List[str], is_system: bool = False, sort_order: int = 0) -> None:
        normalized_code = str(code or "").strip().lower()
        normalized_modules = sorted({str(item or "").strip().lower() for item in (module_codes or []) if str(item or "").strip()})
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO auth_roles(code, label, is_system, sort_order)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                        label=excluded.label,
                        is_system=excluded.is_system,
                        sort_order=excluded.sort_order
                    """,
                    (normalized_code, str(label or "").strip(), 1 if bool(is_system) else 0, int(sort_order or 0)),
                )
                conn.execute("DELETE FROM auth_role_modules WHERE role_code = ?", (normalized_code,))
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO auth_role_modules(role_code, module_code)
                    VALUES (?, ?)
                    """,
                    [(normalized_code, module_code) for module_code in normalized_modules],
                )
                conn.commit()

    def list_auth_users(self) -> List[dict]:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                user_rows = conn.execute(
                    """
                    SELECT subject, label, is_active, must_change_password
                    FROM auth_users
                    ORDER BY subject
                    """
                ).fetchall()
                role_rows = conn.execute(
                    """
                    SELECT subject, role_code
                    FROM auth_user_roles
                    """
                ).fetchall()
        role_map: dict[str, list[str]] = {}
        for subject, role_code in role_rows:
            key = str(subject)
            role_map.setdefault(key, []).append(str(role_code))
        return [
            {
                "subject": str(subject),
                "label": str(label),
                "is_active": bool(is_active),
                "must_change_password": bool(must_change_password),
                "role_codes": sorted(role_map.get(str(subject), [])),
            }
            for subject, label, is_active, must_change_password in user_rows
        ]

    def set_auth_user_roles(self, *, subject: str, role_codes: List[str]) -> None:
        normalized_subject = str(subject or "").strip().lower()
        normalized_roles = sorted({str(item or "").strip().lower() for item in (role_codes or []) if str(item or "").strip()})
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                conn.execute("DELETE FROM auth_user_roles WHERE subject = ?", (normalized_subject,))
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO auth_user_roles(subject, role_code)
                    VALUES (?, ?)
                    """,
                    [(normalized_subject, role_code) for role_code in normalized_roles],
                )
                conn.commit()

    def delete_auth_role(self, *, code: str) -> int:
        normalized_code = str(code or "").strip().lower()
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM auth_roles WHERE code = ?", (normalized_code,))
                conn.commit()
                return int(cursor.rowcount or 0)

    def delete_auth_user(self, *, subject: str) -> int:
        normalized_subject = str(subject or "").strip().lower()
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM auth_users WHERE subject = ?", (normalized_subject,))
                conn.commit()
                return int(cursor.rowcount or 0)
