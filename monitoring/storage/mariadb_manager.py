from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import threading
from typing import Dict, List
from pathlib import Path
import uuid

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

    @staticmethod
    def _custom_service_module_code(service_code: str) -> str:
        normalized = str(service_code or "").strip().lower() or "service"
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
        safe_base = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in normalized)
        max_base_len = max(1, 64 - len("service_") - len("_") - len(digest))
        return f"service_{safe_base[:max_base_len]}_{digest}"

    @staticmethod
    def _custom_service_route_path(service_code: str) -> str:
        return f"/#service={str(service_code or '').strip().lower()}"

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
        self._bootstrap_lock = threading.Lock()
        self._bootstrap_completed = False
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
        if self._bootstrap_completed:
            return
        with self._bootstrap_lock:
            if self._bootstrap_completed:
                return
            MariaDBBootstrapper.ensure_database(self)
            self._bootstrap_completed = True

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

    def _ensure_custom_service_field_columns(self, conn) -> None:
        MariaDBBootstrapper.ensure_custom_service_field_columns(conn, self.db_name)

    def _ensure_custom_service_columns(self, conn) -> None:
        MariaDBBootstrapper.ensure_custom_service_columns(conn, self.db_name)

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

    @staticmethod
    def _ensure_shared_list_rows(conn) -> None:
        MariaDBBootstrapper.ensure_shared_list_rows(conn)

    def _sync_custom_service_auth_modules(self, conn) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT code, label, is_active, sort_order
                FROM custom_services
                ORDER BY sort_order, label
                """
            )
            service_rows = cursor.fetchall()
        module_rows: list[tuple[str, str, str, int, int]] = []
        service_module_codes: set[str] = set()
        for service_code, label, is_active, sort_order in service_rows:
            normalized_service_code = str(service_code or "").strip().lower()
            if not normalized_service_code:
                continue
            module_code = self._custom_service_module_code(normalized_service_code)
            service_module_codes.add(module_code)
            module_rows.append(
                (
                    module_code,
                    str(label or normalized_service_code).strip() or normalized_service_code,
                    self._custom_service_route_path(normalized_service_code),
                    1 if bool(is_active) else 0,
                    1000 + int(sort_order or 0),
                )
            )
        if module_rows:
            with conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO auth_modules(code, label, route_path, is_active, sort_order)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        label=VALUES(label),
                        route_path=VALUES(route_path),
                        is_active=VALUES(is_active),
                        sort_order=VALUES(sort_order)
                    """,
                    module_rows,
                )
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT code
                FROM auth_modules
                WHERE code LIKE 'service_%'
                """
            )
            stale_candidates = [str(code or "") for (code,) in cursor.fetchall()]
        stale_service_codes = sorted(code for code in stale_candidates if code not in service_module_codes)
        if stale_service_codes:
            placeholders = ",".join(["%s"] * len(stale_service_codes))
            with conn.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM auth_role_modules WHERE module_code IN ({placeholders})",
                    stale_service_codes,
                )
                cursor.execute(
                    f"DELETE FROM auth_modules WHERE code IN ({placeholders})",
                    stale_service_codes,
                )
        if service_module_codes:
            with conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT IGNORE INTO auth_role_modules(role_code, module_code)
                    VALUES ('admin', %s)
                    """,
                    [(code,) for code in sorted(service_module_codes)],
                )

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

    def list_auth_modules(self) -> List[dict]:
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT code, label, route_path, is_active, sort_order
                        FROM auth_modules
                        ORDER BY sort_order, label
                        """
                    )
                    rows = cursor.fetchall()
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
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT code, label, is_system, sort_order
                        FROM auth_roles
                        ORDER BY sort_order, label
                        """
                    )
                    role_rows = cursor.fetchall()
                    cursor.execute(
                        """
                        SELECT role_code, module_code
                        FROM auth_role_modules
                        """
                    )
                    module_rows = cursor.fetchall()
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
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO auth_roles(code, label, is_system, sort_order)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            label=VALUES(label),
                            is_system=VALUES(is_system),
                            sort_order=VALUES(sort_order)
                        """,
                        (normalized_code, str(label or "").strip(), 1 if bool(is_system) else 0, int(sort_order or 0)),
                    )
                    cursor.execute("DELETE FROM auth_role_modules WHERE role_code = %s", (normalized_code,))
                    if normalized_modules:
                        cursor.executemany(
                            """
                            INSERT IGNORE INTO auth_role_modules(role_code, module_code)
                            VALUES (%s, %s)
                            """,
                            [(normalized_code, module_code) for module_code in normalized_modules],
                        )
                conn.commit()

    def list_auth_users(self) -> List[dict]:
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT subject, label, is_active, must_change_password
                        FROM auth_users
                        ORDER BY subject
                        """
                    )
                    user_rows = cursor.fetchall()
                    cursor.execute(
                        """
                        SELECT subject, role_code
                        FROM auth_user_roles
                        """
                    )
                    role_rows = cursor.fetchall()
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
        raw_roles = [str(item or "").strip().lower() for item in (role_codes or []) if str(item or "").strip()]
        chosen_role = raw_roles[0] if raw_roles else ""
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    if chosen_role:
                        cursor.execute("SELECT 1 FROM auth_roles WHERE code = %s LIMIT 1", (chosen_role,))
                        if cursor.fetchone() is None:
                            raise ValueError(f"Role introuvable: {chosen_role}")
                    cursor.execute("DELETE FROM auth_user_roles WHERE subject = %s", (normalized_subject,))
                    if chosen_role:
                        cursor.execute(
                            """
                            INSERT IGNORE INTO auth_user_roles(subject, role_code)
                            VALUES (%s, %s)
                            """,
                            (normalized_subject, chosen_role),
                        )
                conn.commit()

    def delete_auth_role(self, *, code: str) -> int:
        normalized_code = str(code or "").strip().lower()
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM auth_roles WHERE code = %s", (normalized_code,))
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    def delete_auth_user(self, *, subject: str) -> int:
        normalized_subject = str(subject or "").strip().lower()
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM auth_users WHERE subject = %s", (normalized_subject,))
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    @staticmethod
    def _decode_json_map(raw: object) -> dict[str, str]:
        try:
            parsed = json.loads(str(raw or "{}"))
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict):
            return {}
        return {str(key): str(value or "") for key, value in parsed.items()}

    def list_shared_lists(self) -> List[dict]:
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT code, label, is_system, sort_order
                        FROM shared_lists
                        ORDER BY sort_order, label
                        """
                    )
                    list_rows = cursor.fetchall()
                    cursor.execute(
                        """
                        SELECT list_code, COUNT(*)
                        FROM shared_list_items
                        GROUP BY list_code
                        """
                    )
                    count_rows = cursor.fetchall()
        count_map = {str(list_code or ""): int(count or 0) for list_code, count in count_rows}
        return [
            {
                "code": str(code or ""),
                "label": str(label or ""),
                "is_system": bool(is_system),
                "sort_order": int(sort_order or 0),
                "item_count": int(count_map.get(str(code or ""), 0)),
            }
            for code, label, is_system, sort_order in list_rows
        ]

    def get_shared_list(self, *, code: str) -> dict | None:
        normalized = str(code or "").strip().lower()
        if not normalized:
            return None
        rows = self.list_shared_lists()
        return next((row for row in rows if str(row.get("code") or "").strip().lower() == normalized), None)

    def save_shared_list(
        self,
        *,
        code: str,
        label: str,
        is_system: bool,
        sort_order: int,
    ) -> dict:
        normalized_code = str(code or "").strip().lower()
        if not normalized_code:
            raise ValueError("Code referentiel invalide.")
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO shared_lists(code, label, is_system, sort_order)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            label=VALUES(label),
                            is_system=VALUES(is_system),
                            sort_order=VALUES(sort_order)
                        """,
                        (
                            normalized_code,
                            str(label or "").strip(),
                            1 if bool(is_system) else 0,
                            int(sort_order or 0),
                        ),
                    )
                conn.commit()
        saved = self.get_shared_list(code=normalized_code)
        if saved is None:
            raise ValueError("Referentiel non persiste.")
        return saved

    def delete_shared_list(self, *, code: str) -> int:
        normalized = str(code or "").strip().lower()
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM shared_lists WHERE code = %s", (normalized,))
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    def list_shared_list_items(self, *, list_code: str) -> List[dict]:
        normalized = str(list_code or "").strip().lower()
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT list_code, item_code, item_label, is_active, sort_order
                        FROM shared_list_items
                        WHERE list_code = %s
                        ORDER BY sort_order, item_label
                        """,
                        (normalized,),
                    )
                    rows = cursor.fetchall()
        return [
            {
                "list_code": str(list_code_value or ""),
                "code": str(item_code or ""),
                "label": str(item_label or ""),
                "is_active": bool(is_active),
                "sort_order": int(sort_order or 0),
            }
            for list_code_value, item_code, item_label, is_active, sort_order in rows
        ]

    def save_shared_list_item(
        self,
        *,
        list_code: str,
        code: str,
        label: str,
        is_active: bool,
        sort_order: int,
    ) -> dict:
        normalized_list_code = str(list_code or "").strip().lower()
        normalized_code = str(code or "").strip().lower()
        if not normalized_list_code or not normalized_code:
            raise ValueError("Code referentiel ou code valeur invalide.")
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO shared_list_items(list_code, item_code, item_label, is_active, sort_order)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            item_label=VALUES(item_label),
                            is_active=VALUES(is_active),
                            sort_order=VALUES(sort_order)
                        """,
                        (
                            normalized_list_code,
                            normalized_code,
                            str(label or "").strip(),
                            1 if bool(is_active) else 0,
                            int(sort_order or 0),
                        ),
                    )
                conn.commit()
        row = next((item for item in self.list_shared_list_items(list_code=normalized_list_code) if str(item.get("code") or "") == normalized_code), None)
        if row is None:
            raise ValueError("Valeur de referentiel non persistee.")
        return row

    def delete_shared_list_item(self, *, list_code: str, code: str) -> int:
        normalized_list_code = str(list_code or "").strip().lower()
        normalized_code = str(code or "").strip().lower()
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM shared_list_items WHERE list_code = %s AND item_code = %s",
                        (normalized_list_code, normalized_code),
                    )
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    def list_custom_services(self) -> List[dict]:
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT code, label, is_active, child_enabled, child_label, sort_order
                        FROM custom_services
                        ORDER BY sort_order, label
                        """
                    )
                    service_rows = cursor.fetchall()
                    cursor.execute(
                        """
                        SELECT service_code, field_key, label, field_kind, required, options, default_value, sort_order, list_source_kind, shared_list_code
                        FROM custom_service_fields
                        ORDER BY service_code, sort_order, id
                        """
                    )
                    field_rows = cursor.fetchall()
        fields_by_service: dict[str, list[dict]] = {}
        for service_code, field_key, label, field_kind, required, options, default_value, sort_order, list_source_kind, shared_list_code in field_rows:
            key = str(service_code or "")
            fields_by_service.setdefault(key, []).append(
                {
                    "field_key": str(field_key or ""),
                    "label": str(label or ""),
                    "field_kind": str(field_kind or "text"),
                    "required": bool(required),
                    "options": str(options or ""),
                    "default_value": str(default_value or ""),
                    "sort_order": int(sort_order or 0),
                    "list_source_kind": str(list_source_kind or "local"),
                    "shared_list_code": str(shared_list_code or ""),
                }
            )
        return [
            {
                "code": str(code or ""),
                "label": str(label or ""),
                "is_active": bool(is_active),
                "child_enabled": bool(child_enabled),
                "child_label": str(child_label or "Elements lies"),
                "sort_order": int(sort_order or 0),
                "fields": fields_by_service.get(str(code or ""), []),
            }
            for code, label, is_active, child_enabled, child_label, sort_order in service_rows
        ]

    def get_custom_service(self, *, code: str) -> dict | None:
        normalized = str(code or "").strip().lower()
        if not normalized:
            return None
        services = self.list_custom_services()
        return next((row for row in services if str(row.get("code") or "").strip().lower() == normalized), None)

    def save_custom_service(
        self,
        *,
        code: str,
        label: str,
        is_active: bool,
        child_enabled: bool,
        child_label: str,
        sort_order: int,
        fields: List[dict],
    ) -> dict:
        normalized_code = str(code or "").strip().lower()
        if not normalized_code:
            raise ValueError("Code service invalide.")
        normalized_fields = list(fields or [])
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO custom_services(code, label, is_active, child_enabled, child_label, sort_order)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            label=VALUES(label),
                            is_active=VALUES(is_active),
                            child_enabled=VALUES(child_enabled),
                            child_label=VALUES(child_label),
                            sort_order=VALUES(sort_order)
                        """,
                        (
                            normalized_code,
                            str(label or "").strip(),
                            1 if bool(is_active) else 0,
                            1 if bool(child_enabled) else 0,
                            str(child_label or "").strip() or "Elements lies",
                            int(sort_order or 0),
                        ),
                    )
                    cursor.execute("DELETE FROM custom_service_fields WHERE service_code = %s", (normalized_code,))
                    if normalized_fields:
                        cursor.executemany(
                            """
                            INSERT INTO custom_service_fields(
                                service_code, field_key, label, field_kind, required, options, default_value, sort_order, list_source_kind, shared_list_code
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            [
                                (
                                    normalized_code,
                                    str(field.get("field_key") or "").strip().lower(),
                                    str(field.get("label") or "").strip(),
                                    str(field.get("field_kind") or "text").strip().lower(),
                                    1 if bool(field.get("required", False)) else 0,
                                    str(field.get("options") or ""),
                                    str(field.get("default_value") or ""),
                                    int(field.get("sort_order") or 0),
                                    str(field.get("list_source_kind") or "local").strip().lower(),
                                    str(field.get("shared_list_code") or "").strip().lower(),
                                )
                                for field in normalized_fields
                            ],
                        )
                self._sync_custom_service_auth_modules(conn)
                conn.commit()
        saved = self.get_custom_service(code=normalized_code)
        if saved is None:
            raise ValueError("Service non persiste.")
        return saved

    def delete_custom_service(self, *, code: str) -> int:
        normalized = str(code or "").strip().lower()
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM custom_services WHERE code = %s", (normalized,))
                    deleted = int(cursor.rowcount or 0)
                self._sync_custom_service_auth_modules(conn)
                conn.commit()
                return deleted

    def list_custom_service_records(self, *, service_code: str) -> List[dict]:
        normalized_code = str(service_code or "").strip().lower()
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, service_code, payload_json, created_at, updated_at
                        FROM custom_service_records
                        WHERE service_code = %s
                        ORDER BY updated_at DESC, id DESC
                        """,
                        (normalized_code,),
                    )
                    record_rows = cursor.fetchall()
                    cursor.execute(
                        """
                        SELECT c.id, c.record_id, c.child_name, c.child_code, c.sort_order
                        FROM custom_service_children c
                        JOIN custom_service_records r ON r.id = c.record_id
                        WHERE r.service_code = %s
                        ORDER BY c.sort_order, c.id
                        """,
                        (normalized_code,),
                    )
                    child_rows = cursor.fetchall()
        children_by_record: dict[str, list[dict]] = {}
        for child_id, record_id, child_name, child_code, sort_order in child_rows:
            key = str(record_id or "")
            children_by_record.setdefault(key, []).append(
                {
                    "id": str(child_id or ""),
                    "name": str(child_name or ""),
                    "code": str(child_code or ""),
                    "sort_order": int(sort_order or 0),
                }
            )
        return [
            {
                "id": str(record_id or ""),
                "service_code": str(code or ""),
                "values": self._decode_json_map(payload_json),
                "children": children_by_record.get(str(record_id or ""), []),
                "created_at": str(created_at or ""),
                "updated_at": str(updated_at or ""),
            }
            for record_id, code, payload_json, created_at, updated_at in record_rows
        ]

    def save_custom_service_record(
        self,
        *,
        service_code: str,
        values: dict[str, str],
        children: list[dict],
        record_id: str = "",
    ) -> dict:
        normalized_code = str(service_code or "").strip().lower()
        normalized_record_id = str(record_id or "").strip() or uuid.uuid4().hex
        now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        payload_json = json.dumps(values or {}, ensure_ascii=False)
        normalized_children = list(children or [])
        created_at = now_iso
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT created_at
                        FROM custom_service_records
                        WHERE id = %s AND service_code = %s
                        """,
                        (normalized_record_id, normalized_code),
                    )
                    existing = cursor.fetchone()
                    if existing is None:
                        cursor.execute(
                            """
                            INSERT INTO custom_service_records(id, service_code, payload_json, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (normalized_record_id, normalized_code, payload_json, now_iso, now_iso),
                        )
                    else:
                        created_at = str(existing[0] or now_iso)
                        cursor.execute(
                            """
                            UPDATE custom_service_records
                            SET payload_json = %s, updated_at = %s
                            WHERE id = %s AND service_code = %s
                            """,
                            (payload_json, now_iso, normalized_record_id, normalized_code),
                        )
                    cursor.execute("DELETE FROM custom_service_children WHERE record_id = %s", (normalized_record_id,))
                    if normalized_children:
                        cursor.executemany(
                            """
                            INSERT INTO custom_service_children(record_id, child_name, child_code, sort_order)
                            VALUES (%s, %s, %s, %s)
                            """,
                            [
                                (
                                    normalized_record_id,
                                    str(child.get("name") or "").strip(),
                                    str(child.get("code") or "").strip(),
                                    int(child.get("sort_order") or 0),
                                )
                                for child in normalized_children
                            ],
                        )
                    cursor.execute(
                        """
                        SELECT id, child_name, child_code, sort_order
                        FROM custom_service_children
                        WHERE record_id = %s
                        ORDER BY sort_order, id
                        """,
                        (normalized_record_id,),
                    )
                    child_rows = cursor.fetchall()
                conn.commit()
        return {
            "id": normalized_record_id,
            "service_code": normalized_code,
            "values": {str(key): str(value or "") for key, value in (values or {}).items()},
            "children": [
                {
                    "id": str(child_id or ""),
                    "name": str(child_name or ""),
                    "code": str(child_code or ""),
                    "sort_order": int(sort_order or 0),
                }
                for child_id, child_name, child_code, sort_order in child_rows
            ],
            "created_at": created_at,
            "updated_at": now_iso,
        }

    def delete_custom_service_record(self, *, service_code: str, record_id: str) -> int:
        normalized_code = str(service_code or "").strip().lower()
        normalized_record_id = str(record_id or "").strip()
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM custom_service_records
                        WHERE id = %s AND service_code = %s
                        """,
                        (normalized_record_id, normalized_code),
                    )
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted
