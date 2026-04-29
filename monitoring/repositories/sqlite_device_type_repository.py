from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable
from typing import List

from monitoring.repositories.device_type_schema_normalizer import (
    ensure_required_schema_fields,
    normalize_type_schema_payload,
)
from monitoring.repositories.sqlite_base import SQLiteRepository
from monitoring.repositories.sqlite_device_type_helpers import clone_type_schema, normalize_type_code


class DeviceTypeRepository(SQLiteRepository):
    def __init__(
        self,
        *,
        connect: Callable[[], sqlite3.Connection],
        ensure_database: Callable[[], None],
        lock: threading.Lock,
    ) -> None:
        super().__init__(connect=connect, ensure_database=ensure_database, lock=lock)

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
        normalized_code = normalize_type_code(code)
        if not normalized_code:
            raise ValueError("Code de type invalide.")
        cleaned_label = str(label or "").strip()
        if not cleaned_label:
            raise ValueError("Libelle de type requis.")

        template = normalize_type_code(template_code or "") or "switch"
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
                    next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 10 FROM device_types").fetchone()[0]
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
                    clone_type_schema(conn, template, normalized_code)
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
                        clone_type_schema(conn, template, normalized_code)
                conn.commit()
        return normalized_code

    def count_devices_by_type(self, code: str) -> int:
        normalized_code = normalize_type_code(code)
        if not normalized_code:
            return 0
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                used = conn.execute("SELECT COUNT(*) FROM devices WHERE dtype = ?", (normalized_code,)).fetchone()[0]
                return int(used or 0)

    def delete_device_type(self, code: str, *, cascade_devices: bool = False) -> bool:
        normalized_code = normalize_type_code(code)
        if not normalized_code:
            return False
        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                row = conn.execute("SELECT is_system FROM device_types WHERE code = ?", (normalized_code,)).fetchone()
                if row is None:
                    return False
                if bool(row[0]):
                    raise ValueError("Impossible de supprimer un type systeme.")
                used = conn.execute("SELECT COUNT(*) FROM devices WHERE dtype = ?", (normalized_code,)).fetchone()[0]
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
        normalized_code = normalize_type_code(type_code)
        if not normalized_code:
            raise ValueError("Code de type invalide.")

        cleaned_fields, cleaned_actions, seen_field_keys = normalize_type_schema_payload(
            fields=fields,
            actions=actions,
        )

        with self._lock:
            self._ensure_database()
            with self._connect() as conn:
                row = conn.execute("SELECT code FROM device_types WHERE code = ?", (normalized_code,)).fetchone()
                if row is None:
                    raise ValueError("Type introuvable.")
                monitoring_enabled_row = conn.execute(
                    "SELECT monitoring_enabled FROM device_types WHERE code = ?",
                    (normalized_code,),
                ).fetchone()
                monitoring_enabled = bool(monitoring_enabled_row[0]) if monitoring_enabled_row is not None else True
                ensure_required_schema_fields(
                    seen_field_keys=seen_field_keys,
                    monitoring_enabled=monitoring_enabled,
                )

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
