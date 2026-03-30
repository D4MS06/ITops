from __future__ import annotations

import os
import threading
from typing import Dict, List
from pathlib import Path

from monitoring.repositories.mariadb_repositories import (
    ConfigVersionRepository,
    DeviceRepository,
    DeviceTypeRepository,
    StatusLogRepository,
)
from monitoring.storage.mariadb_auth_sessions import AuthSessionRepository
from monitoring.storage.mariadb_bootstrap import MariaDBBootstrapper
from monitoring.utils.logger import log_with_timestamp

try:
    import pymysql
except ModuleNotFoundError:  # pragma: no cover - depends on runtime environment
    pymysql = None


class MariaDBFileManager:
    _lock = threading.Lock()
    OS_FIELD_OPTIONS = "Windows,Linux,Firmware,Autre"
    OS_FIELD_DEFAULT = "Windows"
    ALL_OS_SCOPE = "windows,linux,firmware,autre"

    @staticmethod
    def _normalize_os_key(value: str) -> str:
        raw = str(value or "").strip().lower()
        return raw if raw in {"windows", "linux", "firmware", "autre"} else "autre"

    @staticmethod
    def _format_os_scope(values: list[str]) -> str:
        ordered = []
        seen: set[str] = set()
        for value in values:
            key = MariaDBFileManager._normalize_os_key(value)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(key)
        return ",".join(ordered)

    def __init__(self, db_name: str = "devices.db") -> None:
        if pymysql is None:
            raise RuntimeError("Le backend MariaDB requiert la dependance 'PyMySQL'. Installez requirements.txt.")
        configured_name = str(os.environ.get("NMP_MARIADB_DATABASE") or "").strip()
        self.db_name = configured_name or (db_name if db_name != "devices.db" else "network_monitoring")
        self.host = str(os.environ.get("NMP_MARIADB_HOST") or "127.0.0.1").strip()
        self.port = int(str(os.environ.get("NMP_MARIADB_PORT") or "3306").strip() or 3306)
        self.user = str(os.environ.get("NMP_MARIADB_USER") or "root").strip()
        self.password = str(os.environ.get("NMP_MARIADB_PASSWORD") or "")
        self.charset = str(os.environ.get("NMP_MARIADB_CHARSET") or "utf8mb4").strip() or "utf8mb4"
        self._init_repositories()

    def _connect_server(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            charset=self.charset,
            autocommit=False,
        )

    def _connect(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db_name,
            charset=self.charset,
            autocommit=False,
        )

    def _ensure_database_exists(self) -> None:
        with self._connect_server() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()

    def _init_repositories(self) -> None:
        self.devices = DeviceRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=MariaDBFileManager._lock,
        )
        self.device_types = DeviceTypeRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=MariaDBFileManager._lock,
        )
        self.status_logs = StatusLogRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=MariaDBFileManager._lock,
        )
        self.config_versions = ConfigVersionRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=MariaDBFileManager._lock,
        )
        self.auth_sessions = AuthSessionRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=MariaDBFileManager._lock,
        )

    def _ensure_repositories(self) -> None:
        if not all(hasattr(self, attr) for attr in ("devices", "device_types", "status_logs", "config_versions", "auth_sessions")):
            self._init_repositories()

    def _repo(self, attr: str):
        self._ensure_repositories()
        return getattr(self, attr)

    def _ensure_database(self) -> None:
        MariaDBBootstrapper.ensure_database(self)

    def _ensure_status_logs_columns(self, conn) -> None:
        MariaDBBootstrapper.ensure_status_logs_columns(conn, self.db_name)

    def _ensure_devices_columns(self, conn) -> None:
        MariaDBBootstrapper.ensure_devices_columns(conn, self.db_name)

    def _ensure_device_type_actions_columns(self, conn) -> None:
        MariaDBBootstrapper.ensure_device_type_actions_columns(conn, self.db_name)

    def _ensure_device_types_columns(self, conn) -> None:
        MariaDBBootstrapper.ensure_device_types_columns(conn, self.db_name)

    def _ensure_auth_users_columns(self, conn) -> None:
        MariaDBBootstrapper.ensure_auth_users_columns(conn, self.db_name)

    @staticmethod
    def _ensure_default_schema_rows(conn) -> None:
        MariaDBBootstrapper.ensure_default_schema_rows(conn, MariaDBFileManager)

    def _seed_from_json(self, conn) -> None:
        MariaDBBootstrapper.seed_from_json(conn)

    def _seed_from_sqlite(self, conn) -> int:
        local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home())
        sqlite_path = str(Path(local_app_data) / "NetworkMonitoringProject" / "data" / "devices.db")
        return int(MariaDBBootstrapper.seed_from_sqlite(conn, sqlite_path))

    @staticmethod
    def _seed_default_device_types(conn) -> None:
        MariaDBBootstrapper.seed_default_device_types(conn, MariaDBFileManager)

    @staticmethod
    def _ensure_os_field_rows(conn) -> None:
        MariaDBBootstrapper.ensure_os_field_rows(conn, MariaDBFileManager)

    @staticmethod
    def _ensure_action_os_scope_rows(conn) -> None:
        MariaDBBootstrapper.ensure_action_os_scope_rows(conn, MariaDBFileManager)

    @staticmethod
    def _ensure_auth_rbac_rows(conn) -> None:
        MariaDBBootstrapper.ensure_auth_rbac_rows(conn)

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
        log_with_timestamp(f"Ecriture MariaDB reussie ({total} equipements).", level="DEBUG")

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
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
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
                                    WHERE u.subject = %s
                                      AND u.is_active = 1
                                      AND rm.module_code = m.code
                                ) THEN 1
                                ELSE 0
                            END AS granted
                        FROM auth_modules m
                        ORDER BY m.sort_order, m.label
                        """,
                        (str(subject or "").strip(),),
                    )
                    rows = cursor.fetchall()
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
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM auth_users u
                        JOIN auth_user_roles ur ON ur.subject = u.subject
                        JOIN auth_role_modules rm ON rm.role_code = ur.role_code
                        JOIN auth_modules m ON m.code = rm.module_code
                        WHERE u.subject = %s
                          AND u.is_active = 1
                          AND m.code = %s
                          AND m.is_active = 1
                        """,
                        (str(subject or "").strip(), str(module_code or "").strip()),
                    )
                    row = cursor.fetchone()
        return bool(int((row[0] if row else 0) or 0))

    def get_auth_user(self, *, subject: str) -> dict | None:
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT subject, label, is_active, password_hash, must_change_password
                        FROM auth_users
                        WHERE subject = %s
                        """,
                        (str(subject or "").strip().lower(),),
                    )
                    row = cursor.fetchone()
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
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO auth_users(subject, label, is_active, password_hash, must_change_password)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            label=VALUES(label),
                            is_active=VALUES(is_active),
                            password_hash=VALUES(password_hash),
                            must_change_password=VALUES(must_change_password)
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
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE auth_users
                        SET password_hash = %s, must_change_password = %s
                        WHERE subject = %s
                        """,
                        (
                            str(password_hash or "").strip(),
                            1 if bool(must_change_password) else 0,
                            str(subject or "").strip().lower(),
                        ),
                    )
                conn.commit()
