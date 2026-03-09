from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List

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
            self._ensure_status_logs_columns(conn)
            self._ensure_devices_columns(conn)
            self._ensure_device_type_actions_columns(conn)
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
            INSERT OR IGNORE INTO device_types(code, label, icon, monitoring_enabled, is_system, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("switch", "Switch", "switch", 1, 1, 10),
                ("server", "Serveur", "server", 1, 1, 20),
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
        try:
            with SQLiteFileManager._lock:
                self._ensure_database()
                with self._connect() as conn:
                    rows = conn.execute(
                        """
                        SELECT id, dtype, name, ip, description, notify,
                               id_teamviewer, subtype, action_double_click, web_url, ssh_user, custom_data
                        FROM devices
                        ORDER BY dtype, name
                        """
                    ).fetchall()
        except sqlite3.Error as exc:
            raise DeviceReadingError(f"Erreur lecture SQLite: {exc}") from exc

        data: Dict[str, List[dict]] = {}
        for row in rows:
            (
                did,
                dtype,
                name,
                ip,
                description,
                notify,
                id_teamviewer,
                subtype,
                action_double_click,
                web_url,
                ssh_user,
                custom_data,
            ) = row
            entry = {
                "id": str(did),
                "name": str(name),
                "ip": str(ip),
                "description": str(description),
                "notify": bool(notify),
            }
            try:
                parsed_custom_data = json.loads(str(custom_data or "")) if str(custom_data or "").strip() else {}
            except Exception:
                parsed_custom_data = {}
            if isinstance(parsed_custom_data, dict):
                entry["custom_data"] = {str(k): str(v) for k, v in parsed_custom_data.items()}
            has_remote_payload = any(
                str(v or "").strip()
                for v in (id_teamviewer, subtype, action_double_click, web_url, ssh_user)
            )
            if str(dtype) == "server" or has_remote_payload:
                entry["id_Teamviewer"] = str(id_teamviewer or "")
                entry["type"] = str(subtype or "")
                entry["action_double_click"] = str(action_double_click or "")
                entry["web_url"] = str(web_url or "")
                entry["ssh_user"] = str(ssh_user or "")
            data.setdefault(str(dtype), []).append(entry)

        data.setdefault("switch", [])
        data.setdefault("server", [])
        return data

    def list_device_types(self) -> List[dict]:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT code, label, icon, monitoring_enabled, is_system, sort_order
                    FROM device_types
                    ORDER BY sort_order, label
                    """
                ).fetchall()
        return [
            {
                "code": str(code),
                "label": str(label),
                "icon": str(icon or ""),
                "monitoring_enabled": bool(monitoring_enabled),
                "is_system": bool(is_system),
                "sort_order": int(sort_order),
            }
            for code, label, icon, monitoring_enabled, is_system, sort_order in rows
        ]

    def list_type_fields(self, type_code: str) -> List[dict]:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT field_key, label, field_kind, required, options, default_value, sort_order
                    FROM device_type_fields
                    WHERE type_code = ?
                    ORDER BY sort_order, id
                    """,
                    (type_code,),
                ).fetchall()
        return [
            {
                "field_key": str(field_key),
                "label": str(label),
                "field_kind": str(field_kind),
                "required": bool(required),
                "options": str(options or ""),
                "default_value": str(default_value or ""),
                "sort_order": int(sort_order),
            }
            for field_key, label, field_kind, required, options, default_value, sort_order in rows
        ]

    def list_type_actions(self, type_code: str) -> List[dict]:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    FROM device_type_actions
                    WHERE type_code = ?
                    ORDER BY sort_order, id
                    """,
                    (type_code,),
                ).fetchall()
        return [
            {
                "action_key": str(action_key),
                "label": str(label),
                "target_kind": str(target_kind),
                "target_value": str(target_value or ""),
                "os_scope": str(os_scope or ""),
                "sort_order": int(sort_order),
                "is_default": bool(is_default),
            }
            for action_key, label, target_kind, target_value, os_scope, sort_order, is_default in rows
        ]

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
        rebuild_schema: bool = False,
    ) -> str:
        normalized_code = self._normalize_type_code(code)
        if not normalized_code:
            raise ValueError("Code de type invalide.")
        cleaned_label = str(label or "").strip()
        if not cleaned_label:
            raise ValueError("Libelle de type requis.")

        template = self._normalize_type_code(template_code or "") or "switch"
        if template not in {"switch", "server"}:
            template = "switch"

        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                existing = conn.execute(
                    "SELECT icon, is_system, sort_order FROM device_types WHERE code = ?",
                    (normalized_code,),
                ).fetchone()
                if existing is None:
                    next_order = conn.execute(
                        "SELECT COALESCE(MAX(sort_order), 0) + 10 FROM device_types"
                    ).fetchone()[0]
                    sort_order = int(next_order or 10)
                    conn.execute(
                        """
                        INSERT INTO device_types(code, label, icon, monitoring_enabled, is_system, sort_order)
                        VALUES (?, ?, ?, ?, 0, ?)
                        """,
                        (
                            normalized_code,
                            cleaned_label,
                            template,
                            1 if monitoring_enabled else 0,
                            sort_order,
                        ),
                    )
                    self._clone_type_schema(conn, template, normalized_code)
                else:
                    current_icon, is_system, sort_order = existing
                    if not template_code:
                        template = str(current_icon or "switch").strip().lower() or "switch"
                    if bool(is_system):
                        template = str(current_icon or template).strip().lower() or template
                    conn.execute(
                        """
                        UPDATE device_types
                        SET label = ?, icon = ?, monitoring_enabled = ?, sort_order = ?
                        WHERE code = ?
                        """,
                        (
                            cleaned_label,
                            template,
                            1 if monitoring_enabled else 0,
                            int(sort_order or 0),
                            normalized_code,
                        ),
                    )
                    should_rebuild = (
                        rebuild_schema
                        or (
                            bool(template_code)
                            and str(current_icon or "").strip().lower() != template
                            and not bool(is_system)
                        )
                    )
                    if should_rebuild:
                        self._clone_type_schema(conn, template, normalized_code)
                conn.commit()

        return normalized_code

    def delete_device_type(self, code: str) -> bool:
        normalized_code = self._normalize_type_code(code)
        if not normalized_code:
            return False
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT is_system FROM device_types WHERE code = ?",
                    (normalized_code,),
                ).fetchone()
                if row is None:
                    return False
                if bool(row[0]):
                    raise ValueError("Impossible de supprimer un type systeme.")
                used = conn.execute(
                    "SELECT COUNT(*) FROM devices WHERE dtype = ?",
                    (normalized_code,),
                ).fetchone()[0]
                if int(used or 0) > 0:
                    raise ValueError("Ce type est utilise par des equipements existants.")
                conn.execute("DELETE FROM device_types WHERE code = ?", (normalized_code,))
                conn.commit()
                return True

    def replace_type_schema(
        self,
        *,
        type_code: str,
        fields: List[dict],
        actions: List[dict],
    ) -> None:
        normalized_code = self._normalize_type_code(type_code)
        if not normalized_code:
            raise ValueError("Code de type invalide.")

        cleaned_fields: list[dict] = []
        seen_field_keys: set[str] = set()
        for idx, field in enumerate(fields):
            field_key = str(field.get("field_key", "")).strip()
            label = str(field.get("label", "")).strip()
            field_kind = str(field.get("field_kind", "text")).strip().lower() or "text"
            options = str(field.get("options", "") or "")
            default_value = str(field.get("default_value", "") or "")
            required = 1 if bool(field.get("required", False)) else 0
            sort_order = int(field.get("sort_order", (idx + 1) * 10) or (idx + 1) * 10)

            if not field_key or not label:
                continue
            if field_key in seen_field_keys:
                raise ValueError(f"Champ duplique: {field_key}")
            seen_field_keys.add(field_key)
            cleaned_fields.append(
                {
                    "field_key": field_key,
                    "label": label,
                    "field_kind": field_kind,
                    "required": required,
                    "options": options,
                    "default_value": default_value,
                    "sort_order": sort_order,
                }
            )

        required_keys = {"name", "description", "type"}
        monitoring_enabled = True
        for t in self.list_device_types():
            if str(t.get("code", "")) == normalized_code:
                monitoring_enabled = bool(t.get("monitoring_enabled", True))
                break
        if monitoring_enabled:
            required_keys.add("ip")
        missing_required = [key for key in required_keys if key not in seen_field_keys]
        if missing_required:
            raise ValueError(
                "Champs obligatoires manquants dans le schema: " + ", ".join(missing_required)
            )

        cleaned_actions: list[dict] = []
        seen_action_keys: set[str] = set()
        default_seen = False
        for idx, action in enumerate(actions):
            action_key = str(action.get("action_key", "")).strip().lower()
            label = str(action.get("label", "")).strip()
            target_kind = str(action.get("target_kind", "builtin")).strip().lower() or "builtin"
            target_value = str(action.get("target_value", "") or "")
            os_scope = str(action.get("os_scope", "") or "")
            sort_order = int(action.get("sort_order", (idx + 1) * 10) or (idx + 1) * 10)
            is_default = bool(action.get("is_default", False))

            if not action_key or not label:
                continue
            if action_key in seen_action_keys:
                raise ValueError(f"Action dupliquee: {action_key}")
            if is_default and default_seen:
                is_default = False
            if is_default:
                default_seen = True
            seen_action_keys.add(action_key)
            cleaned_actions.append(
                {
                    "action_key": action_key,
                    "label": label,
                    "target_kind": target_kind,
                    "target_value": target_value,
                    "os_scope": os_scope,
                    "sort_order": sort_order,
                    "is_default": 1 if is_default else 0,
                }
            )

        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT code FROM device_types WHERE code = ?",
                    (normalized_code,),
                ).fetchone()
                if row is None:
                    raise ValueError("Type introuvable.")

                conn.execute("DELETE FROM device_type_fields WHERE type_code = ?", (normalized_code,))
                conn.execute("DELETE FROM device_type_actions WHERE type_code = ?", (normalized_code,))

                conn.executemany(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            normalized_code,
                            field["field_key"],
                            field["label"],
                            field["field_kind"],
                            field["required"],
                            field["options"],
                            field["default_value"],
                            field["sort_order"],
                        )
                        for field in cleaned_fields
                    ],
                )
                conn.executemany(
                    """
                    INSERT INTO device_type_actions(
                        type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            normalized_code,
                            action["action_key"],
                            action["label"],
                            action["target_kind"],
                            action["target_value"],
                            action["os_scope"],
                            action["sort_order"],
                            action["is_default"],
                        )
                        for action in cleaned_actions
                    ],
                )
                conn.commit()

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
        with SQLiteFileManager._lock:
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

        with SQLiteFileManager._lock:
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
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                cur = conn.execute(query, args)
                conn.commit()
                return int(cur.rowcount or 0)

    def upsert_device(self, *, dtype: str, item: dict) -> None:
        payload = (
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
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO devices (
                        id, dtype, name, ip, description, notify,
                        id_teamviewer, subtype, action_double_click, web_url, ssh_user, custom_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        dtype=excluded.dtype,
                        name=excluded.name,
                        ip=excluded.ip,
                        description=excluded.description,
                        notify=excluded.notify,
                        id_teamviewer=excluded.id_teamviewer,
                        subtype=excluded.subtype,
                        action_double_click=excluded.action_double_click,
                        web_url=excluded.web_url,
                        ssh_user=excluded.ssh_user,
                        custom_data=excluded.custom_data
                    """,
                    payload,
                )
                conn.commit()

    def delete_device(self, *, device_id: str) -> int:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                cur = conn.execute("DELETE FROM devices WHERE id = ?", (str(device_id),))
                conn.commit()
                return int(cur.rowcount or 0)

    def write_devices_map(self, data: Dict[str, List[dict]]) -> None:
        with SQLiteFileManager._lock:
            self._ensure_database()
            with self._connect() as conn:
                conn.execute("DELETE FROM devices")
                rows: List[tuple] = []
                for dtype, items in data.items():
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
                conn.executemany(
                    """
                    INSERT INTO devices (
                        id, dtype, name, ip, description, notify,
                        id_teamviewer, subtype, action_double_click, web_url, ssh_user, custom_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                conn.commit()
                log_with_timestamp(f"Ecriture SQLite reussie ({len(rows)} equipements).")
