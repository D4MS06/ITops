from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable
from typing import List

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
        missing_required = [key for key in required_keys if key not in seen_field_keys]
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
                row = conn.execute("SELECT code FROM device_types WHERE code = ?", (normalized_code,)).fetchone()
                if row is None:
                    raise ValueError("Type introuvable.")
                monitoring_enabled_row = conn.execute(
                    "SELECT monitoring_enabled FROM device_types WHERE code = ?",
                    (normalized_code,),
                ).fetchone()
                monitoring_enabled = bool(monitoring_enabled_row[0]) if monitoring_enabled_row is not None else True
                if monitoring_enabled:
                    required_keys.add("ip")
                missing_required = [key for key in required_keys if key not in seen_field_keys]
                if missing_required:
                    raise ValueError("Champs obligatoires manquants dans le schema: " + ", ".join(missing_required))

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
