from __future__ import annotations

import json
import os
import sqlite3
from typing import List

from monitoring.storage.json_manager import JSONFileManager
from monitoring.utils.logger import log_with_timestamp


class SQLiteBootstrapper:
    @staticmethod
    def ensure_database(manager) -> None:
        os.makedirs(manager.data_dir, exist_ok=True)
        with manager._connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    dtype TEXT NOT NULL,
                    name TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    description TEXT NOT NULL,
                    notify INTEGER NOT NULL DEFAULT 1,
                    id_teamviewer TEXT NOT NULL DEFAULT '',
                    subtype TEXT NOT NULL DEFAULT '',
                    action_double_click TEXT NOT NULL DEFAULT '',
                    web_url TEXT NOT NULL DEFAULT '',
                    ssh_user TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_types (
                    code TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    icon TEXT NOT NULL DEFAULT '',
                    monitoring_enabled INTEGER NOT NULL DEFAULT 1,
                    config_backups_enabled INTEGER DEFAULT NULL,
                    is_system INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_type_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type_code TEXT NOT NULL,
                    field_key TEXT NOT NULL,
                    label TEXT NOT NULL,
                    field_kind TEXT NOT NULL,
                    required INTEGER NOT NULL DEFAULT 0,
                    options TEXT NOT NULL DEFAULT '',
                    default_value TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(type_code, field_key),
                    FOREIGN KEY(type_code) REFERENCES device_types(code) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_type_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type_code TEXT NOT NULL,
                    action_key TEXT NOT NULL,
                    label TEXT NOT NULL,
                    target_kind TEXT NOT NULL DEFAULT 'builtin',
                    target_value TEXT NOT NULL DEFAULT '',
                    os_scope TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(type_code, action_key),
                    FOREIGN KEY(type_code) REFERENCES device_types(code) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS status_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    dtype TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    old_status TEXT NOT NULL,
                    new_status TEXT NOT NULL,
                    event_kind TEXT NOT NULL DEFAULT 'status_change',
                    details TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS config_file_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    device_type_label TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_users (
                    subject TEXT PRIMARY KEY,
                    label TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_roles (
                    code TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    is_system INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_modules (
                    code TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    route_path TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_user_roles (
                    subject TEXT NOT NULL,
                    role_code TEXT NOT NULL,
                    PRIMARY KEY(subject, role_code),
                    FOREIGN KEY(subject) REFERENCES auth_users(subject) ON DELETE CASCADE,
                    FOREIGN KEY(role_code) REFERENCES auth_roles(code) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_role_modules (
                    role_code TEXT NOT NULL,
                    module_code TEXT NOT NULL,
                    PRIMARY KEY(role_code, module_code),
                    FOREIGN KEY(role_code) REFERENCES auth_roles(code) ON DELETE CASCADE,
                    FOREIGN KEY(module_code) REFERENCES auth_modules(code) ON DELETE CASCADE
                )
                """
            )
            manager._ensure_status_logs_columns(conn)
            manager._ensure_devices_columns(conn)
            manager._ensure_device_type_actions_columns(conn)
            manager._ensure_device_types_columns(conn)
            conn.commit()

            manager._seed_default_device_types(conn)
            manager._ensure_default_schema_rows(conn)
            manager._ensure_os_field_rows(conn)
            manager._ensure_action_os_scope_rows(conn)
            manager._ensure_auth_rbac_rows(conn)

            count = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
            if count == 0:
                manager._seed_from_json(conn)

    @staticmethod
    def ensure_status_logs_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(status_logs)").fetchall()
        col_names = {str(row[1]) for row in rows}
        if "event_kind" not in col_names:
            conn.execute("ALTER TABLE status_logs ADD COLUMN event_kind TEXT NOT NULL DEFAULT 'status_change'")
        if "details" not in col_names:
            conn.execute("ALTER TABLE status_logs ADD COLUMN details TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def ensure_devices_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(devices)").fetchall()
        col_names = {str(row[1]) for row in rows}
        if "custom_data" not in col_names:
            conn.execute("ALTER TABLE devices ADD COLUMN custom_data TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def ensure_device_type_actions_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(device_type_actions)").fetchall()
        col_names = {str(row[1]) for row in rows}
        if "os_scope" not in col_names:
            conn.execute("ALTER TABLE device_type_actions ADD COLUMN os_scope TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def ensure_device_types_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(device_types)").fetchall()
        col_names = {str(row[1]) for row in rows}
        if "config_backups_enabled" not in col_names:
            conn.execute("ALTER TABLE device_types ADD COLUMN config_backups_enabled INTEGER DEFAULT NULL")

    @staticmethod
    def ensure_default_schema_rows(conn: sqlite3.Connection, manager_cls) -> None:
        fields_count = int(conn.execute("SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'switch'").fetchone()[0] or 0)
        actions_count = int(conn.execute("SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'switch'").fetchone()[0] or 0)
        if fields_count == 0:
            conn.executemany(
                """
                INSERT INTO device_type_fields(
                    type_code, field_key, label, field_kind, required, options, default_value, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.execute(
                """
                INSERT INTO device_type_actions(
                    type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("switch", "web", "Ouvrir IP", "builtin", "web", manager_cls.ALL_OS_SCOPE, 10, 1),
            )
        conn.commit()

    @staticmethod
    def ensure_auth_rbac_rows(conn: sqlite3.Connection) -> None:
        conn.executemany(
            """
            INSERT OR IGNORE INTO auth_modules(code, label, route_path, is_active, sort_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("monitoring", "Monitoring", "/monitoring", 1, 10),
                ("interventions", "Interventions", "/interventions", 1, 20),
                ("imprimantes", "Imprimantes", "/imprimantes", 1, 30),
                ("comptes", "Comptes techniques", "/comptes-techniques", 1, 40),
                ("admin", "Administration", "/admin", 1, 50),
            ],
        )
        conn.executemany(
            """
            INSERT OR IGNORE INTO auth_roles(code, label, is_system, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("admin", "Administrateur", 1, 10),
                ("technician", "Technicien", 1, 20),
            ],
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO auth_users(subject, label, is_active)
            VALUES ('admin', 'Administrateur local', 1)
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO auth_user_roles(subject, role_code)
            VALUES ('admin', 'admin')
            """
        )
        conn.executemany(
            """
            INSERT OR IGNORE INTO auth_role_modules(role_code, module_code)
            VALUES (?, ?)
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
    def seed_from_json(conn: sqlite3.Connection) -> None:
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

        conn.executemany(
            """
            INSERT OR REPLACE INTO devices (
                id, dtype, name, ip, description, notify,
                id_teamviewer, subtype, action_double_click, web_url, ssh_user, custom_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        log_with_timestamp(f"Migration JSON vers SQLite terminee ({len(rows)} equipements).")

    @staticmethod
    def seed_default_device_types(conn: sqlite3.Connection, manager_cls) -> None:
        conn.executemany(
            """
            INSERT OR IGNORE INTO device_types(
                code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("switch", "Switch", "switch", 1, 1, 1, 10),
                ("server", "Serveur", "server", 1, 0, 1, 20),
            ],
        )

        switch_fields_count = int(conn.execute("SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'switch'").fetchone()[0] or 0)
        switch_actions_count = int(conn.execute("SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'switch'").fetchone()[0] or 0)
        server_fields_count = int(conn.execute("SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'server'").fetchone()[0] or 0)
        server_actions_count = int(conn.execute("SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'server'").fetchone()[0] or 0)

        if switch_fields_count == 0:
            conn.executemany(
                """
                INSERT INTO device_type_fields(
                    type_code, field_key, label, field_kind, required, options, default_value, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.execute(
                """
                INSERT INTO device_type_actions(
                    type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("switch", "web", "Ouvrir IP", "builtin", "web", manager_cls.ALL_OS_SCOPE, 10, 1),
            )
        if server_fields_count == 0:
            conn.executemany(
                """
                INSERT INTO device_type_fields(
                    type_code, field_key, label, field_kind, required, options, default_value, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.executemany(
                """
                INSERT INTO device_type_actions(
                    type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
    def ensure_os_field_rows(conn: sqlite3.Connection, manager_cls) -> None:
        rows = conn.execute("SELECT code FROM device_types ORDER BY sort_order, label").fetchall()
        for (type_code,) in rows:
            code = str(type_code or "").strip().lower()
            if not code:
                continue
            os_row = conn.execute(
                """
                SELECT id, sort_order
                FROM device_type_fields
                WHERE type_code = ? AND field_key = 'type'
                """,
                (code,),
            ).fetchone()
            if os_row is None:
                desc_sort = conn.execute(
                    """
                    SELECT sort_order
                    FROM device_type_fields
                    WHERE type_code = ? AND field_key = 'description'
                    """,
                    (code,),
                ).fetchone()
                sort_order = int(desc_sort[0]) + 10 if desc_sort is not None else 40
                conn.execute(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, sort_order
                    ) VALUES (?, 'type', 'OS', 'choice', 1, ?, ?, ?)
                    """,
                    (code, manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, sort_order),
                )
                continue
            conn.execute(
                """
                UPDATE device_type_fields
                SET label = 'OS',
                    field_kind = 'choice',
                    required = 1,
                    options = ?,
                    default_value = CASE
                        WHEN default_value IN ('Windows', 'Linux', 'Firmware', 'Autre') THEN default_value
                        ELSE ?
                    END
                WHERE type_code = ? AND field_key = 'type'
                """,
                (manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, code),
            )
        conn.commit()

    @staticmethod
    def ensure_action_os_scope_rows(conn: sqlite3.Connection, manager_cls) -> None:
        legacy_scope = {
            "ssh": manager_cls._format_os_scope(["linux", "firmware", "autre"]),
            "web": manager_cls._format_os_scope(["windows", "linux", "firmware", "autre"]),
            "teamviewer": manager_cls._format_os_scope(["windows", "linux", "autre"]),
            "remote_desktop": manager_cls._format_os_scope(["windows", "autre"]),
        }
        rows = conn.execute(
            """
            SELECT type_code, action_key, os_scope
            FROM device_type_actions
            """
        ).fetchall()
        for type_code, action_key, os_scope in rows:
            if str(os_scope or "").strip():
                continue
            key = str(action_key or "").strip().lower()
            scope = legacy_scope.get(key, manager_cls.ALL_OS_SCOPE)
            conn.execute(
                """
                UPDATE device_type_actions
                SET os_scope = ?
                WHERE type_code = ? AND action_key = ?
                """,
                (scope, str(type_code), key),
            )
        conn.commit()
