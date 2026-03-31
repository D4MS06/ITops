from __future__ import annotations

import json
import os
import sqlite3
from hashlib import pbkdf2_hmac
from typing import List

from monitoring.storage.json_manager import JSONFileManager
from monitoring.utils.logger import log_with_timestamp


class MariaDBBootstrapper:
    @staticmethod
    def ensure_database(manager) -> None:
        manager._ensure_database_exists()
        with manager._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SET SESSION sql_mode = ''")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS devices (
                        id VARCHAR(191) PRIMARY KEY,
                        dtype VARCHAR(64) NOT NULL,
                        name VARCHAR(191) NOT NULL,
                        ip VARCHAR(191) NOT NULL,
                        description TEXT NOT NULL,
                        notify TINYINT(1) NOT NULL DEFAULT 1,
                        id_teamviewer VARCHAR(191) NOT NULL DEFAULT '',
                        subtype VARCHAR(191) NOT NULL DEFAULT '',
                        action_double_click VARCHAR(191) NOT NULL DEFAULT '',
                        web_url TEXT NOT NULL,
                        ssh_user VARCHAR(191) NOT NULL DEFAULT '',
                        custom_data LONGTEXT NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS device_types (
                        code VARCHAR(64) PRIMARY KEY,
                        label VARCHAR(191) NOT NULL,
                        icon VARCHAR(191) NOT NULL DEFAULT '',
                        monitoring_enabled TINYINT(1) NOT NULL DEFAULT 1,
                        config_backups_enabled TINYINT(1) DEFAULT NULL,
                        is_system TINYINT(1) NOT NULL DEFAULT 0,
                        sort_order INT NOT NULL DEFAULT 0
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS device_type_fields (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        type_code VARCHAR(64) NOT NULL,
                        field_key VARCHAR(191) NOT NULL,
                        label VARCHAR(191) NOT NULL,
                        field_kind VARCHAR(64) NOT NULL,
                        required TINYINT(1) NOT NULL DEFAULT 0,
                        options TEXT NOT NULL,
                        default_value TEXT NOT NULL,
                        sort_order INT NOT NULL DEFAULT 0,
                        UNIQUE KEY uq_type_field (type_code, field_key),
                        CONSTRAINT fk_type_fields_code FOREIGN KEY (type_code)
                            REFERENCES device_types(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS device_type_actions (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        type_code VARCHAR(64) NOT NULL,
                        action_key VARCHAR(191) NOT NULL,
                        label VARCHAR(191) NOT NULL,
                        target_kind VARCHAR(64) NOT NULL DEFAULT 'builtin',
                        target_value TEXT NOT NULL,
                        os_scope TEXT NOT NULL,
                        sort_order INT NOT NULL DEFAULT 0,
                        is_default TINYINT(1) NOT NULL DEFAULT 0,
                        UNIQUE KEY uq_type_action (type_code, action_key),
                        CONSTRAINT fk_type_actions_code FOREIGN KEY (type_code)
                            REFERENCES device_types(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS status_logs (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        created_at DATETIME NOT NULL,
                        dtype VARCHAR(64) NOT NULL,
                        device_id VARCHAR(191) NOT NULL,
                        device_name VARCHAR(191) NOT NULL,
                        old_status VARCHAR(64) NOT NULL,
                        new_status VARCHAR(64) NOT NULL,
                        event_kind VARCHAR(64) NOT NULL DEFAULT 'status_change',
                        details TEXT NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS config_file_versions (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        file_path VARCHAR(512) NOT NULL,
                        device_type_label VARCHAR(191) NOT NULL,
                        device_name VARCHAR(191) NOT NULL,
                        filename VARCHAR(191) NOT NULL,
                        detail TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_file_path (file_path)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_sessions (
                        token VARCHAR(255) PRIMARY KEY,
                        subject VARCHAR(255) NOT NULL,
                        created_at VARCHAR(64) NOT NULL,
                        expires_at VARCHAR(64) NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS auth_users (
                    subject VARCHAR(255) PRIMARY KEY,
                    label VARCHAR(255) NOT NULL DEFAULT '',
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    password_hash TEXT NOT NULL,
                    must_change_password TINYINT(1) NOT NULL DEFAULT 1
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_roles (
                        code VARCHAR(64) PRIMARY KEY,
                        label VARCHAR(191) NOT NULL,
                        is_system TINYINT(1) NOT NULL DEFAULT 0,
                        sort_order INT NOT NULL DEFAULT 0
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_modules (
                        code VARCHAR(64) PRIMARY KEY,
                        label VARCHAR(191) NOT NULL,
                        route_path VARCHAR(191) NOT NULL,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        sort_order INT NOT NULL DEFAULT 0
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_user_roles (
                        subject VARCHAR(255) NOT NULL,
                        role_code VARCHAR(64) NOT NULL,
                        PRIMARY KEY(subject, role_code),
                        CONSTRAINT fk_auth_user_roles_subject FOREIGN KEY (subject)
                            REFERENCES auth_users(subject) ON DELETE CASCADE,
                        CONSTRAINT fk_auth_user_roles_role FOREIGN KEY (role_code)
                            REFERENCES auth_roles(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_role_modules (
                        role_code VARCHAR(64) NOT NULL,
                        module_code VARCHAR(64) NOT NULL,
                        PRIMARY KEY(role_code, module_code),
                        CONSTRAINT fk_auth_role_modules_role FOREIGN KEY (role_code)
                            REFERENCES auth_roles(code) ON DELETE CASCADE,
                        CONSTRAINT fk_auth_role_modules_module FOREIGN KEY (module_code)
                            REFERENCES auth_modules(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
            manager._ensure_status_logs_columns(conn)
            manager._ensure_devices_columns(conn)
            manager._ensure_device_type_actions_columns(conn)
            manager._ensure_device_types_columns(conn)
            manager._ensure_auth_users_columns(conn)
            conn.commit()

            manager._seed_default_device_types(conn)
            manager._ensure_default_schema_rows(conn)
            manager._ensure_os_field_rows(conn)
            manager._ensure_action_os_scope_rows(conn)
            manager._ensure_auth_rbac_rows(conn)

            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM devices")
                count = int(cursor.fetchone()[0] or 0)
            if count == 0:
                imported = manager._seed_from_sqlite(conn)
                if int(imported or 0) <= 0:
                    manager._seed_from_json(conn)

    @staticmethod
    def _column_exists(conn, *, db_name: str, table_name: str, column_name: str) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
                """,
                (db_name, table_name, column_name),
            )
            row = cursor.fetchone()
            return bool(int(row[0] if row else 0))

    @staticmethod
    def ensure_status_logs_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="status_logs", column_name="event_kind"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE status_logs ADD COLUMN event_kind VARCHAR(64) NOT NULL DEFAULT 'status_change'")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="status_logs", column_name="details"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE status_logs ADD COLUMN details TEXT NOT NULL")

    @staticmethod
    def ensure_devices_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="devices", column_name="custom_data"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE devices ADD COLUMN custom_data LONGTEXT NOT NULL")

    @staticmethod
    def ensure_device_type_actions_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="device_type_actions", column_name="os_scope"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE device_type_actions ADD COLUMN os_scope TEXT NOT NULL")

    @staticmethod
    def ensure_device_types_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="device_types", column_name="config_backups_enabled"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE device_types ADD COLUMN config_backups_enabled TINYINT(1) DEFAULT NULL")

    @staticmethod
    def ensure_auth_users_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="auth_users", column_name="password_hash"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE auth_users ADD COLUMN password_hash TEXT NOT NULL")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="auth_users", column_name="must_change_password"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE auth_users ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 1")

    @staticmethod
    def ensure_default_schema_rows(conn, manager_cls) -> None:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'switch'")
            fields_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'switch'")
            actions_count = int(cursor.fetchone()[0] or 0)
            if fields_count == 0:
                cursor.executemany(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ("switch", "name", "Nom", "text", 1, "", "", 10),
                        ("switch", "ip", "IP", "ip", 1, "", "", 20),
                        ("switch", "description", "Description", "text", 0, "", "", 30),
                        ("switch", "type", "OS", "choice", 1, manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, 40),
                        ("switch", "action_double_click", "Action double-clic", "choice", 0, "web,ssh,teamviewer,remote_desktop", "", 60),
                    ],
                )
            if actions_count == 0:
                cursor.execute(
                    """
                    INSERT INTO device_type_actions(
                        type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    ("switch", "web", "Ouvrir IP", "builtin", "web", manager_cls.ALL_OS_SCOPE, 10, 1),
                )
        conn.commit()

    @staticmethod
    def seed_from_json(conn) -> None:
        json_mgr = JSONFileManager()
        data = json_mgr.read_json_file()
        if not isinstance(data, dict):
            return

        rows: List[tuple] = []
        for dtype, items in data.items():
            if not isinstance(items, list):
                continue
            for item in items:
                rows.append(
                    (
                        str(item.get("id", "")),
                        str(dtype),
                        str(item.get("name", "")),
                        str(item.get("ip", "")),
                        str(item.get("description", "")),
                        1 if bool(item.get("notify", True)) else 0,
                        str(item.get("id_Teamviewer", "")),
                        str(item.get("type", "")),
                        str(item.get("action_double_click", "")),
                        str(item.get("web_url", "")),
                        str(item.get("ssh_user", "")),
                        json.dumps(item.get("custom_data", {}), ensure_ascii=False),
                    )
                )

        if not rows:
            return

        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO devices (
                    id, dtype, name, ip, description, notify,
                    id_teamviewer, subtype, action_double_click, web_url, ssh_user, custom_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    dtype=VALUES(dtype),
                    name=VALUES(name),
                    ip=VALUES(ip),
                    description=VALUES(description),
                    notify=VALUES(notify),
                    id_teamviewer=VALUES(id_teamviewer),
                    subtype=VALUES(subtype),
                    action_double_click=VALUES(action_double_click),
                    web_url=VALUES(web_url),
                    ssh_user=VALUES(ssh_user),
                    custom_data=VALUES(custom_data)
                """,
                rows,
            )
        conn.commit()
        log_with_timestamp(f"Migration JSON vers MariaDB terminee ({len(rows)} equipements).")

    @staticmethod
    def seed_from_sqlite(conn, sqlite_path: str) -> int:
        source = str(sqlite_path or "").strip()
        if not source or (not os.path.isfile(source)):
            return 0

        try:
            with sqlite3.connect(source) as sqlite_conn:
                sqlite_conn.row_factory = None
                devices = sqlite_conn.execute(
                    """
                    SELECT id, dtype, name, ip, description, notify,
                           id_teamviewer, subtype, action_double_click, web_url, ssh_user,
                           COALESCE(custom_data, '')
                    FROM devices
                    """
                ).fetchall()
                device_types = sqlite_conn.execute(
                    """
                    SELECT code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order
                    FROM device_types
                    """
                ).fetchall()
                device_type_fields = sqlite_conn.execute(
                    """
                    SELECT type_code, field_key, label, field_kind, required, options, default_value, sort_order
                    FROM device_type_fields
                    """
                ).fetchall()
                device_type_actions = sqlite_conn.execute(
                    """
                    SELECT type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    FROM device_type_actions
                    """
                ).fetchall()
                status_logs = sqlite_conn.execute(
                    """
                    SELECT created_at, dtype, device_id, device_name, old_status, new_status, event_kind, details
                    FROM status_logs
                    """
                ).fetchall()
                config_versions = sqlite_conn.execute(
                    """
                    SELECT file_path, device_type_label, device_name, filename, detail, created_at, updated_at
                    FROM config_file_versions
                    """
                ).fetchall()
                auth_sessions = sqlite_conn.execute(
                    """
                    SELECT token, subject, created_at, expires_at
                    FROM auth_sessions
                    """
                ).fetchall()
        except Exception as exc:
            log_with_timestamp(f"Echec migration SQLite vers MariaDB: {exc}", level="WARNING")
            return 0

        with conn.cursor() as cursor:
            if device_types:
                cursor.executemany(
                    """
                    INSERT INTO device_types(
                        code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        label=VALUES(label),
                        icon=VALUES(icon),
                        monitoring_enabled=VALUES(monitoring_enabled),
                        config_backups_enabled=VALUES(config_backups_enabled),
                        is_system=VALUES(is_system),
                        sort_order=VALUES(sort_order)
                    """,
                    device_types,
                )
            if device_type_fields:
                cursor.executemany(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        label=VALUES(label),
                        field_kind=VALUES(field_kind),
                        required=VALUES(required),
                        options=VALUES(options),
                        default_value=VALUES(default_value),
                        sort_order=VALUES(sort_order)
                    """,
                    device_type_fields,
                )
            if device_type_actions:
                cursor.executemany(
                    """
                    INSERT INTO device_type_actions(
                        type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        label=VALUES(label),
                        target_kind=VALUES(target_kind),
                        target_value=VALUES(target_value),
                        os_scope=VALUES(os_scope),
                        sort_order=VALUES(sort_order),
                        is_default=VALUES(is_default)
                    """,
                    device_type_actions,
                )
            if devices:
                cursor.executemany(
                    """
                    INSERT INTO devices(
                        id, dtype, name, ip, description, notify,
                        id_teamviewer, subtype, action_double_click, web_url, ssh_user, custom_data
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        dtype=VALUES(dtype),
                        name=VALUES(name),
                        ip=VALUES(ip),
                        description=VALUES(description),
                        notify=VALUES(notify),
                        id_teamviewer=VALUES(id_teamviewer),
                        subtype=VALUES(subtype),
                        action_double_click=VALUES(action_double_click),
                        web_url=VALUES(web_url),
                        ssh_user=VALUES(ssh_user),
                        custom_data=VALUES(custom_data)
                    """,
                    devices,
                )
            if status_logs:
                cursor.executemany(
                    """
                    INSERT INTO status_logs(
                        created_at, dtype, device_id, device_name, old_status, new_status, event_kind, details
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    status_logs,
                )
            if config_versions:
                cursor.executemany(
                    """
                    INSERT INTO config_file_versions(
                        file_path, device_type_label, device_name, filename, detail, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        device_type_label=VALUES(device_type_label),
                        device_name=VALUES(device_name),
                        filename=VALUES(filename),
                        detail=VALUES(detail),
                        created_at=VALUES(created_at),
                        updated_at=VALUES(updated_at)
                    """,
                    config_versions,
                )
            if auth_sessions:
                cursor.executemany(
                    """
                    INSERT INTO auth_sessions(token, subject, created_at, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        subject=VALUES(subject),
                        created_at=VALUES(created_at),
                        expires_at=VALUES(expires_at)
                    """,
                    auth_sessions,
                )
        conn.commit()
        imported_count = int(len(devices or []))
        log_with_timestamp(f"Migration SQLite vers MariaDB terminee ({imported_count} equipements).")
        return imported_count

    @staticmethod
    def ensure_auth_rbac_rows(conn) -> None:
        default_sa_hash = MariaDBBootstrapper._default_hash_for_password("sa")
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT IGNORE INTO auth_modules(code, label, route_path, is_active, sort_order)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    ("monitoring", "Monitoring", "/monitoring", 1, 10),
                    ("interventions", "Interventions", "/interventions", 1, 20),
                    ("imprimantes", "Imprimantes", "/imprimantes", 1, 30),
                    ("comptes", "Comptes techniques", "/comptes-techniques", 1, 40),
                    ("admin", "Administration", "/admin", 1, 50),
                ],
            )
            cursor.executemany(
                """
                INSERT IGNORE INTO auth_roles(code, label, is_system, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    ("admin", "Administrateur", 1, 10),
                    ("technician", "Technicien", 1, 20),
                ],
            )
            cursor.execute(
                """
                INSERT IGNORE INTO auth_users(subject, label, is_active, password_hash, must_change_password)
                VALUES ('sa', 'Super Admin', 1, %s, 1)
                """,
                (default_sa_hash,),
            )
            cursor.execute(
                """
                INSERT IGNORE INTO auth_users(subject, label, is_active, password_hash, must_change_password)
                VALUES ('admin', 'Administrateur local', 1, '', 1)
                """
            )
            cursor.execute(
                """
                INSERT IGNORE INTO auth_user_roles(subject, role_code)
                VALUES ('sa', 'admin')
                """
            )
            cursor.execute(
                """
                INSERT IGNORE INTO auth_user_roles(subject, role_code)
                VALUES ('admin', 'admin')
                """
            )
            cursor.execute(
                """
                UPDATE auth_modules
                SET is_active = CASE WHEN code IN ('monitoring', 'admin') THEN 1 ELSE 0 END
                WHERE code IN ('monitoring', 'interventions', 'imprimantes', 'comptes', 'admin')
                """
            )
            cursor.executemany(
                """
                INSERT IGNORE INTO auth_role_modules(role_code, module_code)
                VALUES (%s, %s)
                """,
                [
                    ("admin", "monitoring"),
                    ("admin", "interventions"),
                    ("admin", "imprimantes"),
                    ("admin", "comptes"),
                    ("admin", "admin"),
                    ("technician", "monitoring"),
                    ("technician", "interventions"),
                    ("technician", "imprimantes"),
                ],
            )
        conn.commit()

    @staticmethod
    def _default_hash_for_password(password: str) -> str:
        salt = b"nmp_sa_bootstrap"
        iterations = 600_000
        digest = pbkdf2_hmac("sha256", str(password or "").encode("utf-8"), salt, iterations)
        return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"

    @staticmethod
    def seed_default_device_types(conn, manager_cls) -> None:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT IGNORE INTO device_types(
                    code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    ("switch", "Switch", "switch", 1, 1, 1, 10),
                    ("server", "Serveur", "server", 1, 0, 1, 20),
                ],
            )

            cursor.execute("SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'switch'")
            switch_fields_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'switch'")
            switch_actions_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'server'")
            server_fields_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'server'")
            server_actions_count = int(cursor.fetchone()[0] or 0)

            if switch_fields_count == 0:
                cursor.executemany(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ("switch", "name", "Nom", "text", 1, "", "", 10),
                        ("switch", "ip", "IP", "ip", 1, "", "", 20),
                        ("switch", "description", "Description", "text", 0, "", "", 30),
                        ("switch", "type", "OS", "choice", 1, manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, 40),
                        ("switch", "action_double_click", "Action double-clic", "choice", 0, "web,ssh,teamviewer,remote_desktop", "", 60),
                    ],
                )
            if switch_actions_count == 0:
                cursor.execute(
                    """
                    INSERT INTO device_type_actions(
                        type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    ("switch", "web", "Ouvrir IP", "builtin", "web", manager_cls.ALL_OS_SCOPE, 10, 1),
                )
            if server_fields_count == 0:
                cursor.executemany(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ("server", "name", "Nom", "text", 1, "", "", 10),
                        ("server", "ip", "IP", "ip", 1, "", "", 20),
                        ("server", "description", "Description", "text", 0, "", "", 30),
                        ("server", "type", "OS", "choice", 1, manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, 40),
                        ("server", "id_Teamviewer", "ID TeamViewer", "text", 0, "", "", 50),
                        ("server", "action_double_click", "Action double-clic", "choice", 0, "ssh,web,teamviewer,remote_desktop", "", 60),
                        ("server", "web_url", "URL interface web", "url", 0, "", "", 70),
                        ("server", "ssh_user", "SSH user", "text", 0, "", "", 80),
                    ],
                )
            if server_actions_count == 0:
                cursor.executemany(
                    """
                    INSERT INTO device_type_actions(
                        type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ("server", "ssh", "SSH", "builtin", "ssh", manager_cls._format_os_scope(["linux", "firmware", "autre"]), 10, 0),
                        ("server", "web", "Web", "builtin", "web", manager_cls.ALL_OS_SCOPE, 20, 0),
                        ("server", "teamviewer", "TeamViewer", "builtin", "teamviewer", manager_cls._format_os_scope(["windows", "linux", "autre"]), 30, 0),
                        ("server", "remote_desktop", "Remote Desktop", "builtin", "remote_desktop", manager_cls._format_os_scope(["windows", "autre"]), 40, 1),
                    ],
                )
        conn.commit()

    @staticmethod
    def ensure_os_field_rows(conn, manager_cls) -> None:
        with conn.cursor() as cursor:
            cursor.execute("SELECT code FROM device_types ORDER BY sort_order, label")
            rows = cursor.fetchall()
            for (type_code,) in rows:
                code = str(type_code or "").strip().lower()
                if not code:
                    continue
                cursor.execute(
                    """
                    SELECT id, sort_order
                    FROM device_type_fields
                    WHERE type_code = %s AND field_key = 'type'
                    """,
                    (code,),
                )
                os_row = cursor.fetchone()
                if os_row is None:
                    cursor.execute(
                        """
                        SELECT sort_order
                        FROM device_type_fields
                        WHERE type_code = %s AND field_key = 'description'
                        """,
                        (code,),
                    )
                    desc_sort = cursor.fetchone()
                    sort_order = int(desc_sort[0]) + 10 if desc_sort is not None else 40
                    cursor.execute(
                        """
                        INSERT INTO device_type_fields(
                            type_code, field_key, label, field_kind, required, options, default_value, sort_order
                        ) VALUES (%s, 'type', 'OS', 'choice', 1, %s, %s, %s)
                        """,
                        (code, manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, sort_order),
                    )
                    continue
                cursor.execute(
                    """
                    UPDATE device_type_fields
                    SET label = 'OS',
                        field_kind = 'choice',
                        required = 1,
                        options = %s,
                        default_value = CASE
                            WHEN default_value IN ('Windows', 'Linux', 'Firmware', 'Autre') THEN default_value
                            ELSE %s
                        END
                    WHERE type_code = %s AND field_key = 'type'
                    """,
                    (manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, code),
                )
        conn.commit()

    @staticmethod
    def ensure_action_os_scope_rows(conn, manager_cls) -> None:
        legacy_scope = {
            "ssh": manager_cls._format_os_scope(["linux", "firmware", "autre"]),
            "web": manager_cls._format_os_scope(["windows", "linux", "firmware", "autre"]),
            "teamviewer": manager_cls._format_os_scope(["windows", "linux", "autre"]),
            "remote_desktop": manager_cls._format_os_scope(["windows", "autre"]),
        }
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT type_code, action_key, os_scope
                FROM device_type_actions
                """
            )
            rows = cursor.fetchall()
            for type_code, action_key, os_scope in rows:
                if str(os_scope or "").strip():
                    continue
                key = str(action_key or "").strip().lower()
                scope = legacy_scope.get(key, manager_cls.ALL_OS_SCOPE)
                cursor.execute(
                    """
                    UPDATE device_type_actions
                    SET os_scope = %s
                    WHERE type_code = %s AND action_key = %s
                    """,
                    (scope, str(type_code), key),
                )
        conn.commit()
