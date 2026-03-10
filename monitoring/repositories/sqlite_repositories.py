from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Dict, List

from monitoring.utils.exceptions import DeviceReadingError


class _SQLiteRepository:
    def __init__(
        self,
        *,
        connect: Callable[[], sqlite3.Connection],
        ensure_database: Callable[[], None],
        lock: threading.Lock,
    ) -> None:
        self._connect = connect
        self._ensure_database = ensure_database
        self._lock = lock


class DeviceTypeRepository(_SQLiteRepository):
    def __init__(
        self,
        *,
        connect: Callable[[], sqlite3.Connection],
        ensure_database: Callable[[], None],
        lock: threading.Lock,
        normalize_type_code: Callable[[str], str],
        clone_type_schema: Callable[[sqlite3.Connection, str, str], None],
        list_device_types_callback: Callable[[], List[dict]],
    ) -> None:
        super().__init__(connect=connect, ensure_database=ensure_database, lock=lock)
        self._normalize_type_code = normalize_type_code
        self._clone_type_schema = clone_type_schema
        self._list_device_types_callback = list_device_types_callback

    def list_device_types(self) -> List[dict]:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order
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
                "config_backups_enabled": (None if config_backups_enabled is None else bool(config_backups_enabled)),
                "is_system": bool(is_system),
                "sort_order": int(sort_order),
            }
            for code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order in rows
        ]

    def list_type_fields(self, type_code: str) -> List[dict]:
        with self._lock:
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
        with self._lock:
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
        normalized_code = self._normalize_type_code(code)
        if not normalized_code:
            raise ValueError("Code de type invalide.")
        cleaned_label = str(label or "").strip()
        if not cleaned_label:
            raise ValueError("Libelle de type requis.")

        template = self._normalize_type_code(template_code or "") or "switch"
        if template not in {"switch", "server"}:
            template = "switch"

        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                existing = conn.execute(
                    "SELECT icon, config_backups_enabled, is_system, sort_order FROM device_types WHERE code = ?",
                    (normalized_code,),
                ).fetchone()
                if existing is None:
                    next_order = conn.execute(
                        "SELECT COALESCE(MAX(sort_order), 0) + 10 FROM device_types"
                    ).fetchone()[0]
                    sort_order = int(next_order or 10)
                    cfg_backups = config_backups_enabled
                    if cfg_backups is None:
                        cfg_backups = template == "switch"
                    conn.execute(
                        """
                        INSERT INTO device_types(
                            code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order
                        )
                        VALUES (?, ?, ?, ?, ?, 0, ?)
                        """,
                        (
                            normalized_code,
                            cleaned_label,
                            template,
                            1 if monitoring_enabled else 0,
                            1 if bool(cfg_backups) else 0,
                            sort_order,
                        ),
                    )
                    self._clone_type_schema(conn, template, normalized_code)
                else:
                    current_icon, current_cfg_backups, is_system, sort_order = existing
                    if not template_code:
                        template = str(current_icon or "switch").strip().lower() or "switch"
                    if bool(is_system):
                        template = str(current_icon or template).strip().lower() or template
                    cfg_backups = config_backups_enabled
                    if cfg_backups is None:
                        if current_cfg_backups is None:
                            cfg_backups = template == "switch"
                        else:
                            cfg_backups = bool(current_cfg_backups)
                    conn.execute(
                        """
                        UPDATE device_types
                        SET label = ?, icon = ?, monitoring_enabled = ?, config_backups_enabled = ?, sort_order = ?
                        WHERE code = ?
                        """,
                        (
                            cleaned_label,
                            template,
                            1 if monitoring_enabled else 0,
                            1 if bool(cfg_backups) else 0,
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

    def count_devices_by_type(self, code: str) -> int:
        normalized_code = self._normalize_type_code(code)
        if not normalized_code:
            return 0
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                used = conn.execute(
                    "SELECT COUNT(*) FROM devices WHERE dtype = ?",
                    (normalized_code,),
                ).fetchone()[0]
                return int(used or 0)

    def delete_device_type(self, code: str, *, cascade_devices: bool = False) -> bool:
        normalized_code = self._normalize_type_code(code)
        if not normalized_code:
            return False
        with self._lock:
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
                used_count = int(used or 0)
                if used_count > 0 and not bool(cascade_devices):
                    raise ValueError("Ce type est utilise par des equipements existants.")
                if used_count > 0:
                    conn.execute("DELETE FROM devices WHERE dtype = ?", (normalized_code,))
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
        for t in self._list_device_types_callback():
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

        with self._lock:
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

class DeviceRepository(_SQLiteRepository):
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


class StatusLogRepository(_SQLiteRepository):
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
        with self._lock:
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

        with self._lock:
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
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                cur = conn.execute(query, args)
                conn.commit()
                return int(cur.rowcount or 0)


class ConfigVersionRepository(_SQLiteRepository):
    def upsert_config_file_version(
        self,
        *,
        file_path: str,
        device_type_label: str,
        device_name: str,
        filename: str,
        detail: str = "",
    ) -> None:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO config_file_versions(
                        file_path, device_type_label, device_name, filename, detail, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(file_path) DO UPDATE SET
                        device_type_label=excluded.device_type_label,
                        device_name=excluded.device_name,
                        filename=excluded.filename,
                        detail=excluded.detail,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        str(file_path),
                        str(device_type_label),
                        str(device_name),
                        str(filename),
                        str(detail or ""),
                    ),
                )
                conn.commit()

    def list_config_file_versions(
        self,
        *,
        device_type_label: str,
        device_name: str,
    ) -> List[dict]:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT file_path, filename, detail, created_at, updated_at
                    FROM config_file_versions
                    WHERE device_type_label = ? AND device_name = ?
                    ORDER BY updated_at DESC, id DESC
                    """,
                    (str(device_type_label), str(device_name)),
                ).fetchall()
        return [
            {
                "file_path": str(file_path),
                "filename": str(filename),
                "detail": str(detail or ""),
                "created_at": str(created_at or ""),
                "updated_at": str(updated_at or ""),
            }
            for file_path, filename, detail, created_at, updated_at in rows
        ]

    def delete_config_file_version(self, *, file_path: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM config_file_versions WHERE file_path = ?",
                    (str(file_path),),
                )
                conn.commit()
                return int(cur.rowcount or 0)

    def rename_config_file_version(self, *, old_file_path: str, new_file_path: str, new_filename: str) -> int:
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    UPDATE config_file_versions
                    SET file_path = ?, filename = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE file_path = ?
                    """,
                    (str(new_file_path), str(new_filename), str(old_file_path)),
                )
                conn.commit()
                return int(cur.rowcount or 0)
