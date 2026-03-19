from __future__ import annotations

import json
import sqlite3
from typing import Dict, List

from monitoring.repositories.sqlite_base import SQLiteRepository
from monitoring.utils.exceptions import DeviceReadingError
from monitoring.utils.logger import log_with_timestamp


class DeviceRepository(SQLiteRepository):
    def read_devices_map(self) -> Dict[str, List[dict]]:
        try:
            with self._lock:
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
            except (TypeError, ValueError) as exc:
                log_with_timestamp(f"custom_data JSON invalide pour device {did}: {exc}", level="WARNING")
                parsed_custom_data = {}
            if isinstance(parsed_custom_data, dict):
                entry["custom_data"] = {str(k): str(v) for k, v in parsed_custom_data.items()}
            has_remote_payload = any(str(v or "").strip() for v in (id_teamviewer, subtype, action_double_click, web_url, ssh_user))
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
        with self._lock:
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
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                cur = conn.execute("DELETE FROM devices WHERE id = ?", (str(device_id),))
                conn.commit()
                return int(cur.rowcount or 0)

    def write_devices_map(self, data: Dict[str, List[dict]]) -> None:
        with self._lock:
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
