from __future__ import annotations

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
            conn.commit()

            self._seed_default_device_types(conn)

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
                    )
                )

        if not rows:
            return

        conn.executemany(
            """
            INSERT OR REPLACE INTO devices (
                id, dtype, name, ip, description, notify,
                id_teamviewer, subtype, action_double_click, web_url, ssh_user
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

        conn.executemany(
            """
            INSERT OR IGNORE INTO device_type_fields(
                type_code, field_key, label, field_kind, required, options, default_value, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("switch", "name", "Nom", "text", 1, "", "", 10),
                ("switch", "ip", "IP", "ip", 1, "", "", 20),
                ("switch", "description", "Description", "text", 0, "", "", 30),
                ("server", "name", "Nom", "text", 1, "", "", 10),
                ("server", "ip", "IP", "ip", 1, "", "", 20),
                ("server", "description", "Description", "text", 0, "", "", 30),
                ("server", "type", "Type OS", "choice", 0, "Windows,DSM,Linux,Autre", "", 40),
                ("server", "id_Teamviewer", "ID TeamViewer", "text", 0, "", "", 50),
                ("server", "action_double_click", "Action double-clic", "choice", 0, "ssh,web,teamviewer,remote_desktop", "", 60),
                ("server", "web_url", "URL interface web", "url", 0, "", "", 70),
                ("server", "ssh_user", "SSH user", "text", 0, "", "", 80),
            ],
        )

        conn.executemany(
            """
            INSERT OR IGNORE INTO device_type_actions(
                type_code, action_key, label, target_kind, target_value, sort_order, is_default
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("switch", "web", "Ouvrir IP", "builtin", "web", 10, 1),
                ("server", "ssh", "SSH", "builtin", "ssh", 10, 0),
                ("server", "web", "Web", "builtin", "web", 20, 0),
                ("server", "teamviewer", "TeamViewer", "builtin", "teamviewer", 30, 0),
                ("server", "remote_desktop", "Remote Desktop", "builtin", "remote_desktop", 40, 1),
            ],
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
                               id_teamviewer, subtype, action_double_click, web_url, ssh_user
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
            ) = row
            entry = {
                "id": str(did),
                "name": str(name),
                "ip": str(ip),
                "description": str(description),
                "notify": bool(notify),
            }
            if dtype == "server":
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
                    SELECT action_key, label, target_kind, target_value, sort_order, is_default
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
                "sort_order": int(sort_order),
                "is_default": bool(is_default),
            }
            for action_key, label, target_kind, target_value, sort_order, is_default in rows
        ]

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
                            )
                        )
                conn.executemany(
                    """
                    INSERT INTO devices (
                        id, dtype, name, ip, description, notify,
                        id_teamviewer, subtype, action_double_click, web_url, ssh_user
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                conn.commit()
                log_with_timestamp(f"Ecriture SQLite reussie ({len(rows)} equipements).")
