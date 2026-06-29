from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import threading
from typing import Dict, List
import uuid

from monitoring.repositories.mariadb_repositories import (
    ConfigVersionRepository,
    DeviceRepository,
    DeviceTypeRepository,
    LinkedFileRepository,
    StatusLogRepository,
    StorageTargetRepository,
)
from monitoring.storage.mariadb_auth_sessions import AuthSessionRepository
from monitoring.storage.mariadb_bootstrap import MariaDBBootstrapper
from monitoring.services.custom_service_history import build_field_history_events
from monitoring.services.custom_service_index import delete_record_index, upsert_record_index
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
    HIDDEN_AUTH_MODULE_CODES = frozenset({"interventions"})

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

    def __init__(self, db_name: str = "network_monitoring") -> None:
        if pymysql is None:
            raise RuntimeError("Le backend MariaDB requiert la dependance 'PyMySQL'. Installez requirements.txt.")
        configured_name = str(os.environ.get("NMP_MARIADB_DATABASE") or "").strip()
        self.db_name = configured_name or (str(db_name or "").strip() or "network_monitoring")
        self.host = str(os.environ.get("NMP_MARIADB_HOST") or "127.0.0.1").strip()
        self.port = int(str(os.environ.get("NMP_MARIADB_PORT") or "3306").strip() or 3306)
        self.user = str(os.environ.get("NMP_MARIADB_USER") or "root").strip()
        self.password = str(os.environ.get("NMP_MARIADB_PASSWORD") or "")
        self.charset = str(os.environ.get("NMP_MARIADB_CHARSET") or "utf8mb4").strip() or "utf8mb4"
        self._bootstrap_lock = threading.Lock()
        self._bootstrap_completed = False
        self._repo_locks = {
            "devices": threading.Lock(),
            "device_types": threading.Lock(),
            "status_logs": threading.Lock(),
            "config_versions": threading.Lock(),
            "linked_files": threading.Lock(),
            "storage_targets": threading.Lock(),
            "auth_sessions": threading.Lock(),
        }
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
            lock=self._repo_locks["devices"],
        )
        self.device_types = DeviceTypeRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=self._repo_locks["device_types"],
        )
        self.status_logs = StatusLogRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=self._repo_locks["status_logs"],
        )
        self.config_versions = ConfigVersionRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=self._repo_locks["config_versions"],
        )
        self.linked_files = LinkedFileRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=self._repo_locks["linked_files"],
        )
        self.storage_targets = StorageTargetRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=self._repo_locks["storage_targets"],
        )
        self.auth_sessions = AuthSessionRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=self._repo_locks["auth_sessions"],
        )

    def _ensure_repositories(self) -> None:
        if not all(
            hasattr(self, attr)
            for attr in ("devices", "device_types", "status_logs", "config_versions", "linked_files", "storage_targets", "auth_sessions")
        ):
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

    def _ensure_device_type_fields_columns(self, conn) -> None:
        MariaDBBootstrapper.ensure_device_type_fields_columns(conn, self.db_name)

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

    def _ensure_devices_indexes(self, conn) -> None:
        MariaDBBootstrapper.ensure_devices_indexes(conn, self.db_name)

    def _ensure_status_logs_indexes(self, conn) -> None:
        MariaDBBootstrapper.ensure_status_logs_indexes(conn, self.db_name)

    def _ensure_custom_service_record_indexes(self, conn) -> None:
        MariaDBBootstrapper.ensure_custom_service_record_indexes(conn, self.db_name)

    def _ensure_custom_service_history_schema(self, conn) -> None:
        MariaDBBootstrapper.ensure_custom_service_history_schema(conn, self.db_name)

    def _ensure_custom_service_relation_schema(self, conn) -> None:
        MariaDBBootstrapper.ensure_custom_service_relation_schema(conn, self.db_name)

    def _ensure_custom_service_relation_link_schema(self, conn) -> None:
        MariaDBBootstrapper.ensure_custom_service_relation_link_schema(conn, self.db_name)

    @staticmethod
    def _ensure_default_schema_rows(conn) -> None:
        MariaDBBootstrapper.ensure_default_schema_rows(conn, MariaDBFileManager)

    def _seed_from_json(self, conn) -> None:
        MariaDBBootstrapper.seed_from_json(conn)

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
        return self._repo("linked_files").upsert_linked_file(
            file_id=file_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
            module_code=module_code,
            category=category,
            filename=filename,
            stored_path=stored_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            version_label=version_label,
            detail=detail,
            metadata_json=metadata_json,
            sync_status=sync_status,
            sync_error=sync_error,
            created_by=created_by,
        )

    def get_linked_file(self, *, file_id: str) -> dict | None:
        return self._repo("linked_files").get_linked_file(file_id=file_id)

    def get_linked_file_by_stored_path(self, *, stored_path: str) -> dict | None:
        return self._repo("linked_files").get_linked_file_by_stored_path(stored_path=stored_path)

    def list_linked_files_by_stored_path_prefix(
        self,
        *,
        stored_path: str,
        child_path_pattern: str,
        limit: int = 10000,
    ) -> List[dict]:
        return self._repo("linked_files").list_linked_files_by_stored_path_prefix(
            stored_path=stored_path,
            child_path_pattern=child_path_pattern,
            limit=limit,
        )

    def list_linked_files(
        self,
        *,
        owner_kind: str,
        owner_id: str,
        category: str = "",
        module_code: str = "",
        limit: int = 200,
    ) -> List[dict]:
        return self._repo("linked_files").list_linked_files(
            owner_kind=owner_kind,
            owner_id=owner_id,
            category=category,
            module_code=module_code,
            limit=limit,
        )

    def update_linked_file_sync_state(
        self,
        *,
        file_id: str,
        sync_status: str,
        sync_error: str = "",
    ) -> int:
        return self._repo("linked_files").update_linked_file_sync_state(
            file_id=file_id,
            sync_status=sync_status,
            sync_error=sync_error,
        )

    def list_linked_files_by_module_category(
        self,
        *,
        module_code: str,
        category: str,
        limit: int = 1000,
    ) -> List[dict]:
        return self._repo("linked_files").list_linked_files_by_module_category(
            module_code=module_code,
            category=category,
            limit=limit,
        )

    def delete_linked_file(self, *, file_id: str) -> int:
        return self._repo("linked_files").delete_linked_file(file_id=file_id)

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
        return self._repo("storage_targets").upsert_storage_target(
            target_id=target_id,
            label=label,
            service_code=service_code,
            service_label=service_label,
            kind=kind,
            remote_path=remote_path,
            username=username,
            secret_ref=secret_ref,
            local_mount_path=local_mount_path,
            auto_mount_enabled=auto_mount_enabled,
            status=status,
            last_error=last_error,
        )

    def get_storage_target(self, *, target_id: str) -> dict | None:
        return self._repo("storage_targets").get_storage_target(target_id=target_id)

    def list_storage_targets(self, *, service_code: str = "", limit: int = 500) -> List[dict]:
        return self._repo("storage_targets").list_storage_targets(service_code=service_code, limit=limit)

    def update_storage_target_status(
        self,
        *,
        target_id: str,
        status: str,
        last_error: str = "",
    ) -> int:
        return self._repo("storage_targets").update_storage_target_status(
            target_id=target_id,
            status=status,
            last_error=last_error,
        )

    def delete_storage_target(self, *, target_id: str) -> int:
        return self._repo("storage_targets").delete_storage_target(target_id=target_id)

    def upsert_device(self, *, dtype: str, item: dict) -> None:
        self._repo("devices").upsert_device(dtype=dtype, item=item)

    def delete_device(self, *, device_id: str) -> int:
        return self._repo("devices").delete_device(device_id=device_id)

    def set_device_notify(self, *, device_id: str, notify: bool) -> int:
        return self._repo("devices").set_device_notify(device_id=device_id, notify=notify)

    def purge_device_credentials_by_type(self, *, dtype: str) -> int:
        return self._repo("devices").purge_device_credentials_by_type(dtype=dtype)

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
        hidden_codes = self.HIDDEN_AUTH_MODULE_CODES
        return [
            {
                "code": str(code),
                "label": str(label),
                "route_path": str(route_path),
                "is_active": bool(is_active),
                "granted": bool(granted),
            }
            for code, label, route_path, is_active, granted in rows
            if str(code or "").strip().lower() not in hidden_codes
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
        hidden_codes = self.HIDDEN_AUTH_MODULE_CODES
        return [
            {
                "code": str(code),
                "label": str(label),
                "route_path": str(route_path),
                "is_active": bool(is_active),
                "sort_order": int(sort_order or 0),
            }
            for code, label, route_path, is_active, sort_order in rows
            if str(code or "").strip().lower() not in hidden_codes
        ]

    def set_auth_module_active(self, *, code: str, is_active: bool) -> dict | None:
        normalized_code = str(code or "").strip().lower()
        if not normalized_code or normalized_code in self.HIDDEN_AUTH_MODULE_CODES:
            return None
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE auth_modules
                        SET is_active = %s
                        WHERE code = %s
                        """,
                        (1 if bool(is_active) else 0, normalized_code),
                    )
                    updated = int(cursor.rowcount or 0)
                conn.commit()
        if updated <= 0:
            return None
        return next((row for row in self.list_auth_modules() if str(row.get("code") or "").strip().lower() == normalized_code), None)

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
        hidden_codes = self.HIDDEN_AUTH_MODULE_CODES
        return [
            {
                "code": str(role_code),
                "label": str(label),
                "is_system": bool(is_system),
                "sort_order": int(sort_order or 0),
                "module_codes": sorted(
                    module_code
                    for module_code in module_map.get(str(role_code), [])
                    if str(module_code or "").strip().lower() not in hidden_codes
                ),
            }
            for role_code, label, is_system, sort_order in role_rows
        ]

    def save_auth_role(self, *, code: str, label: str, module_codes: List[str], is_system: bool = False, sort_order: int = 0) -> None:
        normalized_code = str(code or "").strip().lower()
        hidden_codes = self.HIDDEN_AUTH_MODULE_CODES
        normalized_modules = sorted(
            {
                str(item or "").strip().lower()
                for item in (module_codes or [])
                if str(item or "").strip() and str(item or "").strip().lower() not in hidden_codes
            }
        )
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
                        SELECT code, label, is_active, credentials_enabled, child_enabled, child_label, sort_order,
                               icon, color, description, treeview_config, allow_export, allow_import, created_at, updated_at
                        FROM custom_services
                        ORDER BY sort_order, label
                        """
                    )
                    service_rows = cursor.fetchall()
                    cursor.execute(
                        """
                        SELECT service_code, field_key, label, field_kind, required, options, default_value, sort_order,
                               list_source_kind, shared_list_code, show_in_list, searchable, unique_value,
                               placeholder, help_text, min_value, max_value, track_history, inline_editable, quick_filter
                        FROM custom_service_fields
                        ORDER BY service_code, sort_order, id
                        """
                    )
                    field_rows = cursor.fetchall()
        fields_by_service: dict[str, list[dict]] = {}
        for (
            service_code,
            field_key,
            label,
            field_kind,
            required,
            options,
            default_value,
            sort_order,
            list_source_kind,
            shared_list_code,
            show_in_list,
            searchable,
            unique_value,
            placeholder,
            help_text,
            min_value,
            max_value,
            track_history,
            inline_editable,
            quick_filter,
        ) in field_rows:
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
                    "show_in_list": bool(show_in_list),
                    "searchable": bool(searchable),
                    "unique_value": bool(unique_value),
                    "placeholder": str(placeholder or ""),
                    "help_text": str(help_text or ""),
                    "min_value": None if min_value is None else float(min_value),
                    "max_value": None if max_value is None else float(max_value),
                    "track_history": bool(track_history),
                    "inline_editable": bool(inline_editable),
                    "quick_filter": bool(quick_filter),
                }
            )
        return [
            {
                "code": str(code or ""),
                "label": str(label or ""),
                "is_active": bool(is_active),
                "credentials_enabled": bool(credentials_enabled),
                "child_enabled": bool(child_enabled),
                "child_label": str(child_label or "Elements lies"),
                "sort_order": int(sort_order or 0),
                "icon": str(icon or ""),
                "color": str(color or ""),
                "description": str(description or ""),
                "treeview_config": str(treeview_config or ""),
                "allow_export": bool(allow_export),
                "allow_import": bool(allow_import),
                "created_at": str(created_at or ""),
                "updated_at": str(updated_at or ""),
                "fields": fields_by_service.get(str(code or ""), []),
            }
            for (
                code,
                label,
                is_active,
                credentials_enabled,
                child_enabled,
                child_label,
                sort_order,
                icon,
                color,
                description,
                treeview_config,
                allow_export,
                allow_import,
                created_at,
                updated_at,
            ) in service_rows
        ]

    def get_custom_service(self, *, code: str) -> dict | None:
        normalized = str(code or "").strip().lower()
        if not normalized:
            return None
        services = self.list_custom_services()
        return next((row for row in services if str(row.get("code") or "").strip().lower() == normalized), None)

    @staticmethod
    def _normalize_custom_service_relation_cardinality(value: str) -> str:
        raw = str(value or "").strip().lower().replace("-", "_")
        aliases = {
            "reference": "many_to_one",
            "one_one": "one_to_one",
            "one_to_one": "one_to_one",
            "1_1": "one_to_one",
            "one_many": "one_to_many",
            "one_to_many": "one_to_many",
            "1_n": "one_to_many",
            "many_one": "many_to_one",
            "many_to_one": "many_to_one",
            "n_1": "many_to_one",
            "many_many": "many_to_many",
            "many_to_many": "many_to_many",
            "n_n": "many_to_many",
        }
        return aliases.get(raw, "many_to_one")

    @staticmethod
    def _normalize_custom_service_relation_direction(value: str) -> str:
        raw = str(value or "").strip().lower()
        return raw if raw in {"out", "in"} else "out"

    @staticmethod
    def _custom_service_relation_cardinality_limits(cardinality: str) -> tuple[bool, bool]:
        normalized = MariaDBFileManager._normalize_custom_service_relation_cardinality(cardinality)
        if normalized == "many_to_many":
            return True, True
        if normalized == "one_to_many":
            return True, False
        if normalized == "one_to_one":
            return False, False
        return False, True

    @staticmethod
    def _normalize_relation_coordinate(value) -> int | None:
        if value in ("", None):
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    def _normalize_custom_service_relation_payload(
        self,
        *,
        source_service_code: str,
        relation: dict,
        sort_order: int = 0,
    ) -> dict:
        source = str(source_service_code or "").strip().lower()
        target = str((relation or {}).get("target_service_code") or (relation or {}).get("service_code") or "").strip().lower()
        if not source:
            raise ValueError("Service source invalide.")
        if not target:
            raise ValueError("Service cible invalide.")
        if source == target:
            raise ValueError("Une relation ne peut pas pointer vers le meme service.")
        cardinality = self._normalize_custom_service_relation_cardinality(str((relation or {}).get("cardinality") or (relation or {}).get("relation_type") or "many_to_one"))
        direction = self._normalize_custom_service_relation_direction(str((relation or {}).get("direction") or "out"))
        verb = str((relation or {}).get("verb") or "").strip() or "est lie a"
        display_label = str((relation or {}).get("display_label") or (relation or {}).get("label") or "").strip()
        return {
            "id": int((relation or {}).get("id") or 0),
            "source_service_code": source,
            "target_service_code": target,
            "verb": verb[:191],
            "cardinality": cardinality,
            "direction": direction,
            "display_label": display_label[:191],
            "required": bool((relation or {}).get("required", False)),
            "is_active": bool((relation or {}).get("is_active", True)),
            "source_x": self._normalize_relation_coordinate((relation or {}).get("source_x")),
            "source_y": self._normalize_relation_coordinate((relation or {}).get("source_y")),
            "target_x": self._normalize_relation_coordinate((relation or {}).get("target_x") if "target_x" in (relation or {}) else (relation or {}).get("x")),
            "target_y": self._normalize_relation_coordinate((relation or {}).get("target_y") if "target_y" in (relation or {}) else (relation or {}).get("y")),
            "sort_order": int((relation or {}).get("sort_order") or sort_order or 0),
        }

    @staticmethod
    def _custom_service_relation_from_row(row) -> dict:
        (
            relation_id,
            source_service_code,
            target_service_code,
            verb,
            cardinality,
            direction,
            display_label,
            required,
            is_active,
            source_x,
            source_y,
            target_x,
            target_y,
            sort_order,
            created_at,
            updated_at,
        ) = row
        return {
            "id": int(relation_id or 0),
            "source_service_code": str(source_service_code or ""),
            "target_service_code": str(target_service_code or ""),
            "service_code": str(target_service_code or ""),
            "verb": str(verb or ""),
            "cardinality": str(cardinality or "many_to_one"),
            "relation_type": str(cardinality or "many_to_one"),
            "direction": str(direction or "out"),
            "display_label": str(display_label or ""),
            "label": str(display_label or ""),
            "required": bool(required),
            "is_active": bool(is_active),
            "source_x": None if source_x is None else int(source_x),
            "source_y": None if source_y is None else int(source_y),
            "target_x": None if target_x is None else int(target_x),
            "target_y": None if target_y is None else int(target_y),
            "x": None if target_x is None else int(target_x),
            "y": None if target_y is None else int(target_y),
            "sort_order": int(sort_order or 0),
            "created_at": str(created_at or ""),
            "updated_at": str(updated_at or ""),
        }

    def list_custom_service_relations(self, *, service_code: str = "") -> list[dict]:
        normalized_code = str(service_code or "").strip().lower()
        clauses: list[str] = []
        params: list[object] = []
        if normalized_code:
            clauses.append("(source_service_code = %s OR target_service_code = %s)")
            params.extend([normalized_code, normalized_code])
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT id, source_service_code, target_service_code, verb, cardinality, direction,
                               display_label, required, is_active, source_x, source_y, target_x, target_y,
                               sort_order, created_at, updated_at
                        FROM custom_service_relations
                        {where_sql}
                        ORDER BY sort_order, id
                        """,
                        params,
                    )
                    rows = cursor.fetchall()
        return [self._custom_service_relation_from_row(row) for row in rows]

    def save_custom_service_relation(self, *, source_service_code: str, relation: dict) -> dict:
        normalized = self._normalize_custom_service_relation_payload(
            source_service_code=source_service_code,
            relation=relation or {},
            sort_order=10,
        )
        existing_source = self.get_custom_service(code=normalized["source_service_code"])
        existing_target = self.get_custom_service(code=normalized["target_service_code"])
        if existing_source is None:
            raise ValueError("Service source introuvable.")
        if existing_target is None:
            raise ValueError("Service cible introuvable.")
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO custom_service_relations(
                            source_service_code, target_service_code, verb, cardinality, direction,
                            display_label, required, is_active, source_x, source_y, target_x, target_y, sort_order
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            verb=VALUES(verb),
                            display_label=VALUES(display_label),
                            required=VALUES(required),
                            is_active=VALUES(is_active),
                            source_x=VALUES(source_x),
                            source_y=VALUES(source_y),
                            target_x=VALUES(target_x),
                            target_y=VALUES(target_y),
                            sort_order=VALUES(sort_order)
                        """,
                        (
                            normalized["source_service_code"],
                            normalized["target_service_code"],
                            normalized["verb"],
                            normalized["cardinality"],
                            normalized["direction"],
                            normalized["display_label"],
                            1 if normalized["required"] else 0,
                            1 if normalized["is_active"] else 0,
                            normalized["source_x"],
                            normalized["source_y"],
                            normalized["target_x"],
                            normalized["target_y"],
                            normalized["sort_order"],
                        ),
                    )
                conn.commit()
        return next(
            (
                item
                for item in self.list_custom_service_relations(service_code=normalized["source_service_code"])
                if item["source_service_code"] == normalized["source_service_code"]
                and item["target_service_code"] == normalized["target_service_code"]
                and item["cardinality"] == normalized["cardinality"]
                and item["direction"] == normalized["direction"]
            ),
            normalized,
        )

    def replace_custom_service_relations(self, *, service_code: str, relations: list[dict]) -> list[dict]:
        normalized_code = str(service_code or "").strip().lower()
        if not normalized_code:
            raise ValueError("Service source invalide.")
        if self.get_custom_service(code=normalized_code) is None:
            raise ValueError("Service source introuvable.")
        normalized_relations = [
            self._normalize_custom_service_relation_payload(
                source_service_code=normalized_code,
                relation=relation,
                sort_order=(index + 1) * 10,
            )
            for index, relation in enumerate(list(relations or []))
        ]
        seen: set[tuple[str, str, str, str]] = set()
        for relation in normalized_relations:
            key = (
                relation["source_service_code"],
                relation["target_service_code"],
                relation["cardinality"],
                relation["direction"],
            )
            if key in seen:
                raise ValueError("Relation en doublon.")
            seen.add(key)
            if self.get_custom_service(code=relation["target_service_code"]) is None:
                raise ValueError(f"Service cible introuvable: {relation['target_service_code']}.")
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM custom_service_relations WHERE source_service_code = %s", (normalized_code,))
                    if normalized_relations:
                        cursor.executemany(
                            """
                            INSERT INTO custom_service_relations(
                                source_service_code, target_service_code, verb, cardinality, direction,
                                display_label, required, is_active, source_x, source_y, target_x, target_y, sort_order
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            [
                                (
                                    relation["source_service_code"],
                                    relation["target_service_code"],
                                    relation["verb"],
                                    relation["cardinality"],
                                    relation["direction"],
                                    relation["display_label"],
                                    1 if relation["required"] else 0,
                                    1 if relation["is_active"] else 0,
                                    relation["source_x"],
                                    relation["source_y"],
                                    relation["target_x"],
                                    relation["target_y"],
                                    relation["sort_order"],
                                )
                                for relation in normalized_relations
                            ],
                        )
                conn.commit()
        return [
            relation
            for relation in self.list_custom_service_relations(service_code=normalized_code)
            if str(relation.get("source_service_code") or "").strip().lower() == normalized_code
        ]

    def delete_custom_service_relation(self, *, relation_id: int = 0, source_service_code: str = "", target_service_code: str = "") -> int:
        normalized_id = int(relation_id or 0)
        normalized_source = str(source_service_code or "").strip().lower()
        normalized_target = str(target_service_code or "").strip().lower()
        if normalized_id <= 0 and (not normalized_source or not normalized_target):
            return 0
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    if normalized_id > 0:
                        if normalized_source:
                            cursor.execute(
                                "DELETE FROM custom_service_relations WHERE id = %s AND source_service_code = %s",
                                (normalized_id, normalized_source),
                            )
                        else:
                            cursor.execute("DELETE FROM custom_service_relations WHERE id = %s", (normalized_id,))
                    else:
                        cursor.execute(
                            """
                            DELETE FROM custom_service_relations
                            WHERE source_service_code = %s AND target_service_code = %s
                            """,
                            (normalized_source, normalized_target),
                        )
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    def _get_custom_service_relation_by_id(self, *, relation_id: int) -> dict | None:
        normalized_id = int(relation_id or 0)
        if normalized_id <= 0:
            return None
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, source_service_code, target_service_code, verb, cardinality, direction,
                               display_label, required, is_active, source_x, source_y, target_x, target_y,
                               sort_order, created_at, updated_at
                        FROM custom_service_relations
                        WHERE id = %s
                        """,
                        (normalized_id,),
                    )
                    row = cursor.fetchone()
        return self._custom_service_relation_from_row(row) if row else None

    def list_custom_service_record_relation_links(self, *, service_code: str, record_id: str, relation_id: int) -> list[dict]:
        normalized_service_code = str(service_code or "").strip().lower()
        normalized_record_id = str(record_id or "").strip()
        normalized_relation_id = int(relation_id or 0)
        relation = self._get_custom_service_relation_by_id(relation_id=normalized_relation_id)
        if relation is None:
            raise ValueError("Relation introuvable.")
        if not bool(relation.get("is_active", True)):
            raise ValueError("Relation inactive.")
        source_service = str(relation.get("source_service_code") or "").strip().lower()
        target_service = str(relation.get("target_service_code") or "").strip().lower()
        if normalized_service_code not in {source_service, target_service}:
            raise ValueError("Relation incompatible avec ce service.")
        current_is_source = normalized_service_code == source_service
        linked_service_code = target_service if current_is_source else source_service
        join_column = "target_record_id" if current_is_source else "source_record_id"
        where_column = "source_record_id" if current_is_source else "target_record_id"
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT l.id, l.relation_id, l.source_record_id, l.target_record_id,
                               r.id, r.service_code, r.payload_json, r.created_at, r.updated_at,
                               l.created_at, l.updated_at
                        FROM custom_service_relation_links l
                        JOIN custom_service_records r ON r.id = l.{join_column}
                        WHERE l.relation_id = %s
                          AND l.{where_column} = %s
                          AND r.service_code = %s
                        ORDER BY r.updated_at DESC, r.id DESC
                        """,
                        (normalized_relation_id, normalized_record_id, linked_service_code),
                    )
                    rows = cursor.fetchall()
        output: list[dict] = []
        for (
            link_id,
            rel_id,
            source_record_id,
            target_record_id,
            linked_record_id,
            linked_service,
            payload_json,
            record_created_at,
            record_updated_at,
            link_created_at,
            link_updated_at,
        ) in rows:
            output.append(
                {
                    "id": int(link_id or 0),
                    "relation_id": int(rel_id or 0),
                    "source_record_id": str(source_record_id or ""),
                    "target_record_id": str(target_record_id or ""),
                    "linked_service_code": str(linked_service or linked_service_code),
                    "linked_record": {
                        "id": str(linked_record_id or ""),
                        "service_code": str(linked_service or linked_service_code),
                        "values": self._decode_json_map(payload_json),
                        "children": [],
                        "created_at": str(record_created_at or ""),
                        "updated_at": str(record_updated_at or ""),
                    },
                    "created_at": str(link_created_at or ""),
                    "updated_at": str(link_updated_at or ""),
                }
            )
        return output

    def save_custom_service_record_relation_link(
        self,
        *,
        service_code: str,
        record_id: str,
        relation_id: int,
        linked_record_id: str,
    ) -> dict:
        normalized_service_code = str(service_code or "").strip().lower()
        normalized_record_id = str(record_id or "").strip()
        normalized_linked_record_id = str(linked_record_id or "").strip()
        normalized_relation_id = int(relation_id or 0)
        relation = self._get_custom_service_relation_by_id(relation_id=normalized_relation_id)
        if relation is None:
            raise ValueError("Relation introuvable.")
        if not bool(relation.get("is_active", True)):
            raise ValueError("Relation inactive.")
        source_service = str(relation.get("source_service_code") or "").strip().lower()
        target_service = str(relation.get("target_service_code") or "").strip().lower()
        if normalized_service_code == source_service:
            source_record_id = normalized_record_id
            target_record_id = normalized_linked_record_id
        elif normalized_service_code == target_service:
            source_record_id = normalized_linked_record_id
            target_record_id = normalized_record_id
        else:
            raise ValueError("Relation incompatible avec ce service.")
        if not source_record_id or not target_record_id:
            raise ValueError("Fiche liee invalide.")
        source_allows_many, target_allows_many = self._custom_service_relation_cardinality_limits(
            str(relation.get("cardinality") or relation.get("relation_type") or "many_to_one")
        )
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM custom_service_records
                        WHERE id = %s AND service_code = %s
                        """,
                        (source_record_id, source_service),
                    )
                    if int((cursor.fetchone() or (0,))[0] or 0) <= 0:
                        raise ValueError("Fiche source introuvable.")
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM custom_service_records
                        WHERE id = %s AND service_code = %s
                        """,
                        (target_record_id, target_service),
                    )
                    if int((cursor.fetchone() or (0,))[0] or 0) <= 0:
                        raise ValueError("Fiche cible introuvable.")
                    if not source_allows_many:
                        cursor.execute(
                            """
                            SELECT COUNT(*)
                            FROM custom_service_relation_links
                            WHERE relation_id = %s
                              AND source_record_id = %s
                              AND target_record_id <> %s
                            """,
                            (normalized_relation_id, source_record_id, target_record_id),
                        )
                        if int((cursor.fetchone() or (0,))[0] or 0) > 0:
                            raise ValueError("Cette relation n'accepte qu'une fiche cible pour cette fiche source.")
                    if not target_allows_many:
                        cursor.execute(
                            """
                            SELECT COUNT(*)
                            FROM custom_service_relation_links
                            WHERE relation_id = %s
                              AND target_record_id = %s
                              AND source_record_id <> %s
                            """,
                            (normalized_relation_id, target_record_id, source_record_id),
                        )
                        if int((cursor.fetchone() or (0,))[0] or 0) > 0:
                            raise ValueError("Cette relation n'accepte qu'une fiche source pour cette fiche cible.")
                    cursor.execute(
                        """
                        INSERT INTO custom_service_relation_links(relation_id, source_record_id, target_record_id)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                        """,
                        (normalized_relation_id, source_record_id, target_record_id),
                    )
                conn.commit()
        links = self.list_custom_service_record_relation_links(
            service_code=normalized_service_code,
            record_id=normalized_record_id,
            relation_id=normalized_relation_id,
        )
        return next(
            (
                row
                for row in links
                if str(row.get("source_record_id") or "") == source_record_id
                and str(row.get("target_record_id") or "") == target_record_id
            ),
            {},
        )

    def delete_custom_service_record_relation_link(
        self,
        *,
        service_code: str,
        record_id: str,
        relation_id: int,
        linked_record_id: str,
    ) -> int:
        normalized_service_code = str(service_code or "").strip().lower()
        normalized_record_id = str(record_id or "").strip()
        normalized_linked_record_id = str(linked_record_id or "").strip()
        normalized_relation_id = int(relation_id or 0)
        relation = self._get_custom_service_relation_by_id(relation_id=normalized_relation_id)
        if relation is None:
            return 0
        source_service = str(relation.get("source_service_code") or "").strip().lower()
        target_service = str(relation.get("target_service_code") or "").strip().lower()
        if normalized_service_code == source_service:
            source_record_id = normalized_record_id
            target_record_id = normalized_linked_record_id
        elif normalized_service_code == target_service:
            source_record_id = normalized_linked_record_id
            target_record_id = normalized_record_id
        else:
            return 0
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM custom_service_relation_links
                        WHERE relation_id = %s AND source_record_id = %s AND target_record_id = %s
                        """,
                        (normalized_relation_id, source_record_id, target_record_id),
                    )
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    def save_custom_service(
        self,
        *,
        code: str,
        label: str,
        is_active: bool,
        credentials_enabled: bool,
        child_enabled: bool,
        child_label: str,
        sort_order: int,
        fields: List[dict],
    ) -> dict:
        normalized_code = str(code or "").strip().lower()
        if not normalized_code:
            raise ValueError("Code service invalide.")
        normalized_fields = [
            dict(field or {})
            for field in list(fields or [])
            if str((field or {}).get("field_key") or "").strip().lower() not in {"device_login", "device_password"}
        ]
        normalized_fields = [
            {
                **field,
                "sort_order": int((index + 1) * 10),
            }
            for index, field in enumerate(normalized_fields)
        ]
        now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO custom_services(
                            code, label, is_active, credentials_enabled, child_enabled, child_label, sort_order,
                            icon, color, description, treeview_config, allow_export, allow_import, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            label=VALUES(label),
                            is_active=VALUES(is_active),
                            credentials_enabled=VALUES(credentials_enabled),
                            child_enabled=VALUES(child_enabled),
                            child_label=VALUES(child_label),
                            sort_order=VALUES(sort_order),
                            updated_at=VALUES(updated_at)
                        """,
                        (
                            normalized_code,
                            str(label or "").strip(),
                            1 if bool(is_active) else 0,
                            1 if bool(credentials_enabled) else 0,
                            1 if bool(child_enabled) else 0,
                            str(child_label or "").strip() or "Elements lies",
                            int(sort_order or 0),
                            "",
                            "",
                            "",
                            "",
                            1,
                            1,
                            now_iso,
                            now_iso,
                        ),
                    )
                    cursor.execute("DELETE FROM custom_service_fields WHERE service_code = %s", (normalized_code,))
                    if normalized_fields:
                        cursor.executemany(
                            """
                            INSERT INTO custom_service_fields(
                                service_code, field_key, label, field_kind, required, options, default_value, sort_order,
                                list_source_kind, shared_list_code, show_in_list, searchable, unique_value,
                                placeholder, help_text, min_value, max_value, track_history, inline_editable, quick_filter
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                                    1 if bool(field.get("show_in_list", True)) else 0,
                                    1 if bool(field.get("searchable", True)) else 0,
                                    1 if bool(field.get("unique_value", False)) else 0,
                                    str(field.get("placeholder") or ""),
                                    str(field.get("help_text") or ""),
                                    field.get("min_value") if field.get("min_value") not in ("", None) else None,
                                    field.get("max_value") if field.get("max_value") not in ("", None) else None,
                                    1 if bool(field.get("track_history", False)) else 0,
                                    1 if bool(field.get("inline_editable", False)) else 0,
                                    1 if bool(field.get("quick_filter", False)) else 0,
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
        if not normalized:
            return 0
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    # The foreign keys installed on new databases already cascade these
                    # deletes.  Keeping the cleanup explicit also protects databases
                    # upgraded from an older schema where those constraints may be
                    # absent or have been disabled during a restore.
                    cursor.execute(
                        """
                        DELETE l
                        FROM custom_service_relation_links l
                        JOIN custom_service_relations r ON r.id = l.relation_id
                        WHERE r.source_service_code = %s OR r.target_service_code = %s
                        """,
                        (normalized, normalized),
                    )
                    cursor.execute(
                        """
                        DELETE l
                        FROM custom_service_relation_links l
                        JOIN custom_service_records r ON r.id = l.source_record_id OR r.id = l.target_record_id
                        WHERE r.service_code = %s
                        """,
                        (normalized,),
                    )
                    cursor.execute(
                        """
                        DELETE FROM custom_service_relations
                        WHERE source_service_code = %s OR target_service_code = %s
                        """,
                        (normalized, normalized),
                    )
                    cursor.execute("DELETE FROM custom_service_records WHERE service_code = %s", (normalized,))
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
                    history_summary_by_record = self._latest_custom_service_record_history_summary_with_cursor(
                        cursor=cursor,
                        service_code=normalized_code,
                        record_ids=[str(record_id or "") for record_id, *_rest in record_rows],
                    )
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
                "history_summary": history_summary_by_record.get(str(record_id or ""), {}),
                "created_at": str(created_at or ""),
                "updated_at": str(updated_at or ""),
            }
            for record_id, code, payload_json, created_at, updated_at in record_rows
        ]

    def purge_custom_service_record_credentials(self, *, service_code: str, credential_keys: list[str] | None = None) -> int:
        normalized_code = str(service_code or "").strip().lower()
        keys = [
            str(key or "").strip().lower()
            for key in list(credential_keys or ["device_login", "device_password"])
            if str(key or "").strip()
        ]
        if not normalized_code or not keys:
            return 0
        now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        updated_rows = 0
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, payload_json
                        FROM custom_service_records
                        WHERE service_code = %s
                        """,
                        (normalized_code,),
                    )
                    record_rows = cursor.fetchall()
                    for record_id, payload_json in record_rows:
                        values = self._decode_json_map(payload_json)
                        changed = False
                        for key in keys:
                            if key in values:
                                values.pop(key, None)
                                changed = True
                        if not changed:
                            continue
                        cursor.execute(
                            """
                            UPDATE custom_service_records
                            SET payload_json = %s, updated_at = %s
                            WHERE id = %s AND service_code = %s
                            """,
                            (json.dumps(values or {}, ensure_ascii=False), now_iso, str(record_id or ""), normalized_code),
                        )
                        updated_rows += 1
                conn.commit()
        return updated_rows

    def save_custom_service_record(
        self,
        *,
        service_code: str,
        values: dict[str, str],
        children: list[dict],
        record_id: str = "",
        change_source: str = "manual",
        changed_by: str = "",
        record_history: bool = True,
        history_changed_at: str = "",
    ) -> dict:
        normalized_code = str(service_code or "").strip().lower()
        normalized_record_id = str(record_id or "").strip() or uuid.uuid4().hex
        now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        history_changed_at_iso = self._normalize_custom_service_history_changed_at(history_changed_at) or now_iso
        payload_json = json.dumps(values or {}, ensure_ascii=False)
        normalized_children = list(children or [])
        created_at = now_iso
        service = self.get_custom_service(code=normalized_code)
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT created_at, payload_json
                        FROM custom_service_records
                        WHERE id = %s AND service_code = %s
                        """,
                        (normalized_record_id, normalized_code),
                    )
                    existing = cursor.fetchone()
                    old_values = self._decode_json_map(existing[1]) if existing is not None else {}
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
                    history_events = build_field_history_events(
                        fields=list((service or {}).get("fields") or []),
                        old_values=old_values,
                        new_values=values or {},
                    )
                    if record_history and history_events:
                        cursor.executemany(
                            """
                            INSERT INTO custom_service_record_history(
                                service_code, record_id, field_key, old_value, new_value, changed_at, changed_by, change_source
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            [
                                (
                                    normalized_code,
                                    normalized_record_id,
                                    str(event.get("field_key") or ""),
                                    str(event.get("old_value") or ""),
                                    str(event.get("new_value") or ""),
                                    history_changed_at_iso,
                                    str(changed_by or "").strip(),
                                    str(change_source or "").strip()[:64],
                                )
                                for event in history_events
                            ],
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
        row = {
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
        if service is not None:
            upsert_record_index(manager=self, service=service, record=row)
        return row

    @staticmethod
    def _normalize_custom_service_history_changed_at(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        normalized = raw.replace("T", " ")
        if len(normalized) == 16:
            normalized = f"{normalized}:00"
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return dt.datetime.strptime(normalized, pattern).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        try:
            parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError("Date d'historique invalide.") from exc

    def list_custom_service_record_history(
        self,
        *,
        service_code: str,
        record_id: str = "",
        field_key: str = "",
        limit: int = 200,
    ) -> list[dict]:
        normalized_code = str(service_code or "").strip().lower()
        normalized_record_id = str(record_id or "").strip()
        normalized_field_key = str(field_key or "").strip()
        safe_limit = max(1, min(int(limit or 200), 1000))
        clauses = ["service_code = %s"]
        params: list[object] = [normalized_code]
        if normalized_record_id:
            clauses.append("record_id = %s")
            params.append(normalized_record_id)
        if normalized_field_key:
            clauses.append("field_key = %s")
            params.append(normalized_field_key)
        params.append(safe_limit)
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT id, service_code, record_id, field_key, old_value, new_value, changed_at, changed_by, change_source
                        FROM custom_service_record_history
                        WHERE {' AND '.join(clauses)}
                        ORDER BY changed_at DESC, id DESC
                        LIMIT %s
                        """,
                        params,
                    )
                    rows = cursor.fetchall()
        return [
            {
                "id": int(row_id or 0),
                "service_code": str(code or ""),
                "record_id": str(record_id_value or ""),
                "field_key": str(field_key_value or ""),
                "old_value": str(old_value or ""),
                "new_value": str(new_value or ""),
                "changed_at": str(changed_at or ""),
                "changed_by": str(changed_by_value or ""),
                "change_source": str(change_source_value or ""),
            }
            for (
                row_id,
                code,
                record_id_value,
                field_key_value,
                old_value,
                new_value,
                changed_at,
                changed_by_value,
                change_source_value,
            ) in rows
        ]

    def _latest_custom_service_record_history_summary(self, *, service_code: str, record_ids: list[str]) -> dict[str, dict[str, dict[str, str]]]:
        normalized_code = str(service_code or "").strip().lower()
        ids = [str(record_id or "").strip() for record_id in list(record_ids or []) if str(record_id or "").strip()]
        if not normalized_code or not ids:
            return {}
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    return self._latest_custom_service_record_history_summary_with_cursor(
                        cursor=cursor,
                        service_code=normalized_code,
                        record_ids=ids,
                    )

    def _latest_custom_service_record_history_summary_with_cursor(
        self,
        *,
        cursor,
        service_code: str,
        record_ids: list[str],
    ) -> dict[str, dict[str, dict[str, str]]]:
        normalized_code = str(service_code or "").strip().lower()
        ids = [str(record_id or "").strip() for record_id in list(record_ids or []) if str(record_id or "").strip()]
        if not normalized_code or not ids:
            return {}
        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(
            f"""
            SELECT h.record_id, h.field_key, h.old_value, h.new_value, h.changed_at, h.changed_by, h.change_source
            FROM custom_service_record_history h
            JOIN (
                SELECT record_id, field_key, MAX(id) AS latest_id
                FROM custom_service_record_history
                WHERE service_code = %s AND record_id IN ({placeholders})
                GROUP BY record_id, field_key
            ) latest ON latest.latest_id = h.id
            ORDER BY h.record_id, h.field_key
            """,
            [normalized_code, *ids],
        )
        rows = cursor.fetchall()
        summary: dict[str, dict[str, dict[str, str]]] = {}
        for record_id, field_key, old_value, new_value, changed_at, changed_by, change_source in rows:
            record_key = str(record_id or "")
            field = str(field_key or "")
            if not record_key or not field:
                continue
            summary.setdefault(record_key, {})[field] = {
                "old_value": str(old_value or ""),
                "new_value": str(new_value or ""),
                "changed_at": str(changed_at or ""),
                "changed_by": str(changed_by or ""),
                "change_source": str(change_source or ""),
            }
        return summary

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
        if deleted > 0:
            delete_record_index(manager=self, record_id=normalized_record_id)
        return deleted

    def upsert_custom_service_record_index(
        self,
        *,
        record_id: str,
        service_code: str,
        label_value: str,
        search_blob: str,
    ) -> None:
        normalized_record_id = str(record_id or "").strip()
        normalized_service_code = str(service_code or "").strip().lower()
        if not normalized_record_id or not normalized_service_code:
            return
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO custom_service_record_index(record_id, service_code, label_value, search_blob, indexed_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON DUPLICATE KEY UPDATE
                            service_code = VALUES(service_code),
                            label_value = VALUES(label_value),
                            search_blob = VALUES(search_blob),
                            indexed_at = CURRENT_TIMESTAMP
                        """,
                        (
                            normalized_record_id,
                            normalized_service_code,
                            str(label_value or "")[:500],
                            str(search_blob or ""),
                        ),
                    )
                conn.commit()

    def delete_custom_service_record_index(self, *, record_id: str) -> int:
        normalized_record_id = str(record_id or "").strip()
        if not normalized_record_id:
            return 0
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM custom_service_record_index WHERE record_id = %s",
                        (normalized_record_id,),
                    )
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    def list_custom_service_records_missing_index(self, *, limit: int = 100) -> list[dict]:
        safe_limit = max(1, min(int(limit or 100), 1000))
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT r.id, r.service_code, r.payload_json, r.created_at, r.updated_at
                        FROM custom_service_records r
                        LEFT JOIN custom_service_record_index i ON i.record_id = r.id
                        WHERE i.record_id IS NULL
                        ORDER BY r.updated_at ASC, r.id ASC
                        LIMIT %s
                        """,
                        (safe_limit,),
                    )
                    rows = cursor.fetchall()
                    record_ids = [str(record_id or "") for record_id, *_rest in rows if str(record_id or "")]
                    child_rows = []
                    if record_ids:
                        placeholders = ",".join(["%s"] * len(record_ids))
                        cursor.execute(
                            f"""
                            SELECT id, record_id, child_name, child_code, sort_order
                            FROM custom_service_children
                            WHERE record_id IN ({placeholders})
                            ORDER BY sort_order, id
                            """,
                            record_ids,
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
                "service_code": str(service_code or ""),
                "values": self._decode_json_map(payload_json),
                "children": children_by_record.get(str(record_id or ""), []),
                "created_at": str(created_at or ""),
                "updated_at": str(updated_at or ""),
            }
            for record_id, service_code, payload_json, created_at, updated_at in rows
        ]

    def search_custom_service_record_index(
        self,
        *,
        service_code: str,
        search: str = "",
        limit: int = 50,
        offset: int = 0,
        sort: str = "label",
        direction: str = "asc",
    ) -> list[dict]:
        page = self.query_custom_service_record_index(
            service_code=service_code,
            search=search,
            limit=limit,
            offset=offset,
            sort=sort,
            direction=direction,
        )
        return list(page.get("items") or [])

    def query_custom_service_record_index(
        self,
        *,
        service_code: str,
        search: str = "",
        limit: int = 50,
        offset: int = 0,
        sort: str = "label",
        direction: str = "asc",
    ) -> dict:
        normalized_code = str(service_code or "").strip().lower()
        safe_limit = max(1, min(int(limit or 50), 500))
        safe_offset = max(0, int(offset or 0))
        search_text = str(search or "").strip()
        sort_key = str(sort or "label").strip().lower()
        sort_sql = {
            "label": "i.label_value",
            "updated_at": "r.updated_at",
            "created_at": "r.created_at",
        }.get(sort_key, "i.label_value")
        direction_sql = "DESC" if str(direction or "").strip().lower() == "desc" else "ASC"
        filters = ["i.service_code = %s"]
        filter_params: list[object] = [normalized_code]
        if search_text:
            filters.append("i.search_blob LIKE %s")
            filter_params.append(f"%{search_text}%")
        where_clause = " AND ".join(filters)
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM custom_service_record_index i
                        JOIN custom_service_records r ON r.id = i.record_id
                        WHERE {where_clause}
                        """,
                        filter_params,
                    )
                    total_row = cursor.fetchone()
                    total = int(total_row[0] or 0) if total_row else 0
                    cursor.execute(
                        f"""
                        SELECT r.id, r.service_code, r.payload_json, r.created_at, r.updated_at, i.label_value
                        FROM custom_service_record_index i
                        JOIN custom_service_records r ON r.id = i.record_id
                        WHERE {where_clause}
                        ORDER BY {sort_sql} {direction_sql}, r.id ASC
                        LIMIT %s OFFSET %s
                        """,
                        [*filter_params, safe_limit, safe_offset],
                    )
                    rows = cursor.fetchall()
                    record_ids = [str(record_id or "") for record_id, *_rest in rows if str(record_id or "")]
                    child_rows = []
                    if record_ids:
                        placeholders = ",".join(["%s"] * len(record_ids))
                        cursor.execute(
                            f"""
                            SELECT id, record_id, child_name, child_code, sort_order
                            FROM custom_service_children
                            WHERE record_id IN ({placeholders})
                            ORDER BY sort_order, id
                            """,
                            record_ids,
                        )
                        child_rows = cursor.fetchall()
                    history_summary_by_record = self._latest_custom_service_record_history_summary_with_cursor(
                        cursor=cursor,
                        service_code=normalized_code,
                        record_ids=record_ids,
                    )
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
        items = [
            {
                "id": str(record_id or ""),
                "service_code": str(code or ""),
                "values": self._decode_json_map(payload_json),
                "children": children_by_record.get(str(record_id or ""), []),
                "history_summary": history_summary_by_record.get(str(record_id or ""), {}),
                "created_at": str(created_at or ""),
                "updated_at": str(updated_at or ""),
                "label_value": str(label_value or ""),
            }
            for record_id, code, payload_json, created_at, updated_at, label_value in rows
        ]
        return {
            "items": items,
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
        }

    def list_dashboard_preferences(self, *, scope: str) -> list[dict]:
        normalized_scope = str(scope or "").strip().lower()
        if not normalized_scope:
            return []
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT card_id, sort_order, is_hidden
                        FROM dashboard_preferences
                        WHERE dashboard_scope = %s
                        ORDER BY sort_order, card_id
                        """,
                        (normalized_scope,),
                    )
                    rows = cursor.fetchall()
        return [
            {
                "card_id": str(card_id or "").strip(),
                "sort_order": int(sort_order or 0),
                "is_hidden": bool(is_hidden),
            }
            for card_id, sort_order, is_hidden in rows
            if str(card_id or "").strip()
        ]

    def save_dashboard_preferences(self, *, scope: str, cards_order: list[str], hidden_cards: list[str]) -> list[dict]:
        normalized_scope = str(scope or "").strip().lower()
        if not normalized_scope:
            return []
        ordered: list[str] = []
        seen: set[str] = set()
        for raw_id in list(cards_order or []) + list(hidden_cards or []):
            card_id = str(raw_id or "").strip()
            if not card_id or card_id in seen:
                continue
            seen.add(card_id)
            ordered.append(card_id)
        hidden = {
            str(raw_id or "").strip()
            for raw_id in list(hidden_cards or [])
            if str(raw_id or "").strip()
        }
        with MariaDBFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    if ordered:
                        placeholders = ", ".join(["%s"] * len(ordered))
                        cursor.execute(
                            f"""
                            DELETE FROM dashboard_preferences
                            WHERE dashboard_scope = %s AND card_id NOT IN ({placeholders})
                            """,
                            [normalized_scope, *ordered],
                        )
                    else:
                        cursor.execute(
                            "DELETE FROM dashboard_preferences WHERE dashboard_scope = %s",
                            (normalized_scope,),
                        )
                    if ordered:
                        cursor.executemany(
                            """
                            INSERT INTO dashboard_preferences(dashboard_scope, card_id, sort_order, is_hidden)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                sort_order = VALUES(sort_order),
                                is_hidden = VALUES(is_hidden)
                            """,
                            [
                                (normalized_scope, card_id, index, 1 if card_id in hidden else 0)
                                for index, card_id in enumerate(ordered)
                            ],
                        )
                conn.commit()
        return self.list_dashboard_preferences(scope=normalized_scope)
