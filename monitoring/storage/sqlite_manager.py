from __future__ import annotations

import os
import sqlite3
import threading
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
            conn.commit()

            count = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
            if count == 0:
                self._seed_from_json(conn)

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
