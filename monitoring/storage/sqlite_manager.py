from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List

from monitoring.repositories.sqlite_repositories import (
    ConfigVersionRepository,
    DeviceRepository,
    DeviceTypeRepository,
    StatusLogRepository,
)
from monitoring.storage.json_manager import JSONFileManager
from monitoring.utils.exceptions import DeviceReadingError
from monitoring.utils.logger import log_with_timestamp


class SQLiteFileManager:
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
            normalize_type_code=self._normalize_type_code,
            clone_type_schema=self._clone_type_schema,
            list_device_types_callback=lambda: self.device_types.list_device_types(),
        )
        self.status_logs = StatusLogRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )

    def _ensure_repositories(self) -> None:
        if not all(
            hasattr(self, attr)
            for attr in ("devices", "device_types", "status_logs", "config_versions")
        ):
            self._init_repositories()
        self.config_versions = ConfigVersionRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_database(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        with self._connect() as conn:
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
            self._ensure_status_logs_columns(conn)
            self._ensure_devices_columns(conn)
            self._ensure_device_type_actions_columns(conn)
            self._ensure_device_types_columns(conn)
            conn.commit()

            self._seed_default_device_types(conn)
            self._ensure_default_schema_rows(conn)
            self._ensure_os_field_rows(conn)
            self._ensure_action_os_scope_rows(conn)

            count = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
            if count == 0:
                self._seed_from_json(conn)

    @staticmethod
    def _ensure_status_logs_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(status_logs)").fetchall()
        col_names = {str(row[1]) for row in rows}
        if "event_kind" not in col_names:
            conn.execute(
                "ALTER TABLE status_logs ADD COLUMN event_kind TEXT NOT NULL DEFAULT 'status_change'"
            )
        if "details" not in col_names:
            conn.execute("ALTER TABLE status_logs ADD COLUMN details TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def _ensure_devices_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(devices)").fetchall()
        col_names = {str(row[1]) for row in rows}
        if "custom_data" not in col_names:
            conn.execute("ALTER TABLE devices ADD COLUMN custom_data TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def _ensure_device_type_actions_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(device_type_actions)").fetchall()
        col_names = {str(row[1]) for row in rows}
        if "os_scope" not in col_names:
            conn.execute("ALTER TABLE device_type_actions ADD COLUMN os_scope TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def _ensure_device_types_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(device_types)").fetchall()
        col_names = {str(row[1]) for row in rows}
        if "config_backups_enabled" not in col_names:
            conn.execute("ALTER TABLE device_types ADD COLUMN config_backups_enabled INTEGER DEFAULT NULL")

    @staticmethod
    def _ensure_default_schema_rows(conn: sqlite3.Connection) -> None:
        # Migration soft: seed only when switch schema is totally absent.
        fields_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'switch'"
            ).fetchone()[0]
            or 0
        )
        actions_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'switch'"
            ).fetchone()[0]
            or 0
        )
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
                    ("switch", "type", "OS", "choice", 1, SQLiteFileManager.OS_FIELD_OPTIONS, SQLiteFileManager.OS_FIELD_DEFAULT, 40),
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
                ("switch", "web", "Ouvrir IP", "builtin", "web", SQLiteFileManager.ALL_OS_SCOPE, 10, 1),
            )
        conn.commit()

    def _seed_from_json(self, conn: sqlite3.Connection) -> None:
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
    def _seed_default_device_types(conn: sqlite3.Connection) -> None:
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

        switch_fields_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'switch'"
            ).fetchone()[0]
            or 0
        )
        switch_actions_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'switch'"
            ).fetchone()[0]
            or 0
        )
        server_fields_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'server'"
            ).fetchone()[0]
            or 0
        )
        server_actions_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'server'"
            ).fetchone()[0]
            or 0
        )

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
                    ("switch", "type", "OS", "choice", 1, SQLiteFileManager.OS_FIELD_OPTIONS, SQLiteFileManager.OS_FIELD_DEFAULT, 40),
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
                ("switch", "web", "Ouvrir IP", "builtin", "web", SQLiteFileManager.ALL_OS_SCOPE, 10, 1),
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
                    ("server", "type", "OS", "choice", 1, SQLiteFileManager.OS_FIELD_OPTIONS, SQLiteFileManager.OS_FIELD_DEFAULT, 40),
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
                    ("server", "ssh", "SSH", "builtin", "ssh", SQLiteFileManager._format_os_scope(["linux", "firmware", "autre"]), 10, 0),
                    ("server", "web", "Web", "builtin", "web", SQLiteFileManager.ALL_OS_SCOPE, 20, 0),
                    ("server", "teamviewer", "TeamViewer", "builtin", "teamviewer", SQLiteFileManager._format_os_scope(["windows", "linux", "autre"]), 30, 0),
                    ("server", "remote_desktop", "Remote Desktop", "builtin", "remote_desktop", SQLiteFileManager._format_os_scope(["windows", "autre"]), 40, 1),
                ],
            )
        conn.commit()

    @staticmethod
    def _ensure_os_field_rows(conn: sqlite3.Connection) -> None:
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
                    (code, SQLiteFileManager.OS_FIELD_OPTIONS, SQLiteFileManager.OS_FIELD_DEFAULT, sort_order),
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
                (SQLiteFileManager.OS_FIELD_OPTIONS, SQLiteFileManager.OS_FIELD_DEFAULT, code),
            )
        conn.commit()

    @staticmethod
    def _ensure_action_os_scope_rows(conn: sqlite3.Connection) -> None:
        legacy_scope = {
            "ssh": SQLiteFileManager._format_os_scope(["linux", "firmware", "autre"]),
            "web": SQLiteFileManager._format_os_scope(["windows", "linux", "firmware", "autre"]),
            "teamviewer": SQLiteFileManager._format_os_scope(["windows", "linux", "autre"]),
            "remote_desktop": SQLiteFileManager._format_os_scope(["windows", "autre"]),
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
            scope = legacy_scope.get(key, SQLiteFileManager.ALL_OS_SCOPE)
            conn.execute(
                """
                UPDATE device_type_actions
                SET os_scope = ?
                WHERE type_code = ? AND action_key = ?
                """,
                (scope, str(type_code), key),
            )
        conn.commit()

    def read_devices_map(self) -> Dict[str, List[dict]]:
        self._ensure_repositories()
        return self.devices.read_devices_map()

    def list_device_types(self) -> List[dict]:
        self._ensure_repositories()
        return self.device_types.list_device_types()

    def list_type_fields(self, type_code: str) -> List[dict]:
        self._ensure_repositories()
        return self.device_types.list_type_fields(type_code)

    def list_type_actions(self, type_code: str) -> List[dict]:
        self._ensure_repositories()
        return self.device_types.list_type_actions(type_code)

    @staticmethod
    def _normalize_type_code(raw_code: str) -> str:
        code = str(raw_code or "").strip().lower()
        return "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in code)

    @staticmethod
    def _clone_type_schema(conn: sqlite3.Connection, source_type: str, target_type: str) -> None:
        conn.execute("DELETE FROM device_type_fields WHERE type_code = ?", (target_type,))
        conn.execute("DELETE FROM device_type_actions WHERE type_code = ?", (target_type,))

        field_rows = conn.execute(
            """
            SELECT field_key, label, field_kind, required, options, default_value, sort_order
            FROM device_type_fields
            WHERE type_code = ?
            ORDER BY sort_order, id
            """,
            (source_type,),
        ).fetchall()
        conn.executemany(
            """
            INSERT INTO device_type_fields(
                type_code, field_key, label, field_kind, required, options, default_value, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    target_type,
                    str(field_key),
                    str(label),
                    str(field_kind),
                    int(required or 0),
                    str(options or ""),
                    str(default_value or ""),
                    int(sort_order or 0),
                )
                for field_key, label, field_kind, required, options, default_value, sort_order in field_rows
            ],
        )

        action_rows = conn.execute(
            """
            SELECT action_key, label, target_kind, target_value, os_scope, sort_order, is_default
            FROM device_type_actions
            WHERE type_code = ?
            ORDER BY sort_order, id
            """,
            (source_type,),
        ).fetchall()
        conn.executemany(
            """
            INSERT INTO device_type_actions(
                type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    target_type,
                    str(action_key),
                    str(label),
                    str(target_kind),
                    str(target_value or ""),
                    str(os_scope or ""),
                    int(sort_order or 0),
                    int(is_default or 0),
                )
                for action_key, label, target_kind, target_value, os_scope, sort_order, is_default in action_rows
            ],
        )

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
        self._ensure_repositories()
        return self.device_types.save_device_type(
            code=code,
            label=label,
            template_code=template_code,
            monitoring_enabled=monitoring_enabled,
            config_backups_enabled=config_backups_enabled,
            rebuild_schema=rebuild_schema,
        )

    def count_devices_by_type(self, code: str) -> int:
        self._ensure_repositories()
        return self.device_types.count_devices_by_type(code)

    def delete_device_type(self, code: str, *, cascade_devices: bool = False) -> bool:
        self._ensure_repositories()
        return self.device_types.delete_device_type(code, cascade_devices=cascade_devices)

    def replace_type_schema(
        self,
        *,
        type_code: str,
        fields: List[dict],
        actions: List[dict],
    ) -> None:
        self._ensure_repositories()
        self.device_types.replace_type_schema(type_code=type_code, fields=fields, actions=actions)

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
        self._ensure_repositories()
        self.status_logs.record_status_log(
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
        self._ensure_repositories()
        return self.status_logs.list_status_logs(limit=limit, dtype=dtype, device_id=device_id)

    def delete_status_logs(
        self,
        *,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> int:
        self._ensure_repositories()
        return self.status_logs.delete_status_logs(dtype=dtype, device_id=device_id)

    def upsert_config_file_version(
        self,
        *,
        file_path: str,
        device_type_label: str,
        device_name: str,
        filename: str,
        detail: str = "",
    ) -> None:
        self._ensure_repositories()
        self.config_versions.upsert_config_file_version(
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
        self._ensure_repositories()
        return self.config_versions.list_config_file_versions(
            device_type_label=device_type_label,
            device_name=device_name,
        )

    def delete_config_file_version(self, *, file_path: str) -> int:
        self._ensure_repositories()
        return self.config_versions.delete_config_file_version(file_path=file_path)

    def rename_config_file_version(self, *, old_file_path: str, new_file_path: str, new_filename: str) -> int:
        self._ensure_repositories()
        return self.config_versions.rename_config_file_version(
            old_file_path=old_file_path,
            new_file_path=new_file_path,
            new_filename=new_filename,
        )

    def upsert_device(self, *, dtype: str, item: dict) -> None:
        self._ensure_repositories()
        self.devices.upsert_device(dtype=dtype, item=item)

    def delete_device(self, *, device_id: str) -> int:
        self._ensure_repositories()
        return self.devices.delete_device(device_id=device_id)

    def write_devices_map(self, data: Dict[str, List[dict]]) -> None:
        self._ensure_repositories()
        self.devices.write_devices_map(data)
        total = sum(len(items) for items in data.values())
        log_with_timestamp(f"Ecriture SQLite reussie ({total} equipements).")

    def save_auth_session(self, *, token: str, subject: str, created_at: str, expires_at: str) -> None:
        self._ensure_database()
        with SQLiteFileManager._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO auth_sessions(token, subject, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(token), str(subject), str(created_at), str(expires_at)),
            )
            conn.commit()

    def get_auth_session(self, *, token: str) -> dict | None:
        self._ensure_database()
        with SQLiteFileManager._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT token, subject, created_at, expires_at
                FROM auth_sessions
                WHERE token = ?
                """,
                (str(token),),
            ).fetchone()
        if row is None:
            return None
        return {
            "token": str(row[0]),
            "subject": str(row[1]),
            "created_at": str(row[2]),
            "expires_at": str(row[3]),
        }

    def delete_auth_session(self, *, token: str) -> int:
        self._ensure_database()
        with SQLiteFileManager._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM auth_sessions WHERE token = ?", (str(token),))
            conn.commit()
            return int(cursor.rowcount or 0)

    def delete_all_auth_sessions(self) -> int:
        self._ensure_database()
        with SQLiteFileManager._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM auth_sessions")
            conn.commit()
            return int(cursor.rowcount or 0)

    def delete_expired_auth_sessions(self, *, now_iso: str) -> int:
        self._ensure_database()
        with SQLiteFileManager._lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM auth_sessions WHERE expires_at <= ?",
                (str(now_iso),),
            )
            conn.commit()
            return int(cursor.rowcount or 0)
