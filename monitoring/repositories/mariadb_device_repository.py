from __future__ import annotations

import json
from typing import Dict, List

from monitoring.repositories.mariadb_base import MariaDBRepository
from monitoring.utils.exceptions import DeviceReadingError
from monitoring.utils.logger import log_with_timestamp


class DeviceRepository(MariaDBRepository):
    def read_devices_map(self) -> Dict[str, List[dict]]:
        try:
            with self._lock:
                self._ensure_database()
                with self._connect() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT id, dtype, name, ip, description, notify,
                                   id_teamviewer, subtype, action_double_click, web_url, ssh_user,
                                   device_login, device_password, custom_data
                            FROM devices
                            ORDER BY dtype, name
                            """
                        )
                        rows = cursor.fetchall()
        except Exception as exc:
            raise DeviceReadingError(f"Erreur lecture MariaDB: {exc}") from exc

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
                device_login,
                device_password,
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
            entry["device_login"] = str(device_login or "")
            entry["device_password"] = str(device_password or "")
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
            str(item.get("device_login", "")),
            str(item.get("device_password", "")),
            json.dumps(item.get("custom_data", {}), ensure_ascii=False),
        )
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO devices (
                            id, dtype, name, ip, description, notify,
                            id_teamviewer, subtype, action_double_click, web_url, ssh_user,
                            device_login, device_password, custom_data
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                            device_login=VALUES(device_login),
                            device_password=VALUES(device_password),
                            custom_data=VALUES(custom_data)
                        """,
                        payload,
                    )
                conn.commit()

    def delete_device(self, *, device_id: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM devices WHERE id = %s", (str(device_id),))
                    deleted = int(cursor.rowcount or 0)
                conn.commit()
                return deleted

    def set_device_notify(self, *, device_id: str, notify: bool) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE devices SET notify = %s WHERE id = %s",
                        (1 if bool(notify) else 0, str(device_id)),
                    )
                    updated = int(cursor.rowcount or 0)
                conn.commit()
                return updated

    def purge_device_credentials_by_type(self, *, dtype: str) -> int:
        normalized_dtype = str(dtype or "").strip().lower()
        if not normalized_dtype:
            return 0
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE devices
                        SET device_login = '', device_password = ''
                        WHERE dtype = %s
                          AND (COALESCE(device_login, '') <> '' OR COALESCE(device_password, '') <> '')
                        """,
                        (normalized_dtype,),
                    )
                    updated = int(cursor.rowcount or 0)
                conn.commit()
                return updated

    def write_devices_map(self, data: Dict[str, List[dict]]) -> None:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM devices")
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
                                    str(item.get("device_login", "")),
                                    str(item.get("device_password", "")),
                                    json.dumps(item.get("custom_data", {}), ensure_ascii=False),
                                )
                            )
                    if rows:
                        cursor.executemany(
                            """
                            INSERT INTO devices (
                                id, dtype, name, ip, description, notify,
                                id_teamviewer, subtype, action_double_click, web_url, ssh_user,
                                device_login, device_password, custom_data
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            rows,
                        )
                conn.commit()
