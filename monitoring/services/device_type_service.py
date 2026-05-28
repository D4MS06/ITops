from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path
from typing import Iterable

from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.utils.config_files import _sanitize_path_part
from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.ui.utils.action_compat import normalize_platform


class DeviceTypeService:
    """Service metier autour des types d'equipements et de leurs schemas."""

    def __init__(self, manager: MariaDBFileManager | None = None) -> None:
        self._mgr = manager or MariaDBFileManager()
        self._config_storage = ConfigStorageService()

    @staticmethod
    def slugify(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.strip().lower()).strip("_")
        return slug or "type"

    def generate_unique_code(self, label: str) -> str:
        base = self.slugify(label)
        existing = {str(t.get("code", "")).strip().lower() for t in self.list_types()}
        candidate = base
        idx = 2
        while candidate in existing:
            candidate = f"{base}_{idx}"
            idx += 1
        return candidate

    def list_types(self) -> list[dict]:
        rows = [dict(item) for item in self._mgr.list_device_types()]
        for row in rows:
            code = str(row.get("code", "")).strip().lower()
            credentials_enabled = False
            if code:
                try:
                    credentials_enabled = self._credentials_enabled_for_type(code)
                except Exception:
                    credentials_enabled = False
            row["credentials_enabled"] = bool(credentials_enabled)
        return rows

    def get_type(self, code: str) -> dict | None:
        normalized = str(code or "").strip().lower()
        if not normalized:
            return None
        return next(
            (
                item
                for item in self.list_types()
                if str(item.get("code", "")).strip().lower() == normalized
            ),
            None,
        )

    def list_fields(self, type_code: str) -> list[dict]:
        fields = list(self._mgr.list_type_fields(str(type_code or "").strip().lower()))
        return sorted(fields, key=lambda x: int(x.get("sort_order", 0)))

    def list_actions(self, type_code: str) -> list[dict]:
        actions = list(self._mgr.list_type_actions(str(type_code or "").strip().lower()))
        return sorted(actions, key=lambda x: int(x.get("sort_order", 0)))

    def load_schema(self, type_code: str) -> tuple[list[dict], list[dict]]:
        fields = self.list_fields(type_code)
        actions = self.list_actions(type_code)
        scope_seed = self._scope_seed_from_fields(fields)
        for action in actions:
            scope = str(action.get("os_scope", "")).strip()
            if scope:
                continue
            action["os_scope"] = self._format_os_scope(scope_seed)
        return fields, actions

    def save_type(
        self,
        *,
        code: str,
        label: str,
        monitoring_enabled: bool,
        config_backups_enabled: bool | None = None,
    ) -> str:
        normalized_code = str(code or "").strip().lower()
        normalized_label = str(label or "").strip()
        previous = next((item for item in self.list_types() if str(item.get("code", "")).strip().lower() == normalized_code), None)
        previous_cfg = self._is_config_enabled(previous) if previous else False
        previous_label = str(previous.get("label", "")).strip() if previous else normalized_label
        previous_monitoring = bool(previous.get("monitoring_enabled", True)) if previous else True

        saved_code = self._mgr.save_device_type(
            code=normalized_code,
            label=normalized_label,
            monitoring_enabled=bool(monitoring_enabled),
            config_backups_enabled=config_backups_enabled,
        )

        next_cfg = self._is_config_enabled(
            {
                "code": normalized_code,
                "label": normalized_label,
                "config_backups_enabled": config_backups_enabled,
            }
        )
        if previous_cfg and not next_cfg:
            # Purge both old/new labels to cover rename + disable in one operation.
            labels = {previous_label, normalized_label}
            for type_label in labels:
                self._purge_type_config_files(type_label=type_label)
        if previous_monitoring and not bool(monitoring_enabled):
            try:
                self._mgr.delete_status_logs(dtype=normalized_code)
            except Exception:
                pass
        return saved_code

    def create_type(
        self,
        *,
        label: str,
        monitoring_enabled: bool,
        config_backups_enabled: bool | None = None,
    ) -> str:
        generated_code = self.generate_unique_code(label)
        return self.save_type(
            code=generated_code,
            label=label,
            monitoring_enabled=monitoring_enabled,
            config_backups_enabled=config_backups_enabled,
        )

    def count_devices(self, code: str) -> int:
        return int(self._mgr.count_devices_by_type(str(code or "").strip().lower()) or 0)

    def delete_type(self, code: str, *, cascade_devices: bool = False) -> bool:
        return bool(
            self._mgr.delete_device_type(
                str(code or "").strip().lower(),
                cascade_devices=bool(cascade_devices),
            )
        )

    def count_type_config_files(self, *, type_label: str) -> int:
        target_name = _sanitize_path_part(str(type_label or ""))
        if not target_name:
            return 0
        local_root = self._config_storage.local_versions_root_dir()
        target_dir = Path(local_root) / target_name
        try:
            if not target_dir.is_dir():
                return 0
        except OSError:
            return 0
        count = 0
        for candidate in target_dir.rglob("*"):
            try:
                if candidate.is_file() and not candidate.name.startswith("."):
                    count += 1
            except OSError:
                continue
        return int(count)

    def count_type_logs(self, *, type_code: str) -> int:
        return int(self._mgr.count_status_logs(dtype=str(type_code or "").strip().lower()) or 0)

    def replace_schema(self, *, type_code: str, fields: Iterable[dict], actions: Iterable[dict]) -> None:
        self._mgr.replace_type_schema(
            type_code=str(type_code or "").strip().lower(),
            fields=list(fields),
            actions=list(actions),
        )

    @staticmethod
    def _scope_seed_from_fields(fields: Iterable[dict]) -> list[str]:
        for field in fields or []:
            key = str(field.get("field_key", "")).strip().lower()
            if key not in {"type", "device_subtype"}:
                continue
            options = [
                str(item or "").strip()
                for item in str(field.get("options", "") or "").split(",")
                if str(item or "").strip()
            ]
            if options:
                return options
        return ["windows", "linux", "firmware", "autre"]

    @staticmethod
    def _normalize_os(value: str) -> str:
        return normalize_platform(value)

    @classmethod
    def _format_os_scope(cls, scope_values: Iterable[str]) -> str:
        ordered = []
        seen: set[str] = set()
        for item in scope_values:
            key = cls._normalize_os(str(item))
            if key in seen:
                continue
            seen.add(key)
            ordered.append(key)
        return ",".join(ordered)

    @staticmethod
    def _is_config_enabled(item: dict | None) -> bool:
        if not item:
            return False
        cfg_flag = item.get("config_backups_enabled", None)
        if cfg_flag is None:
            return str(item.get("icon", "")).strip().lower() == "switch"
        return bool(cfg_flag)

    def _credentials_enabled_for_type(self, type_code: str) -> bool:
        fields = self.list_fields(type_code)
        keys = {
            str(field.get("field_key", "")).strip().lower()
            for field in fields
            if isinstance(field, dict)
        }
        return "device_login" in keys and "device_password" in keys

    def _purge_type_config_files(self, *, type_label: str) -> None:
        target_name = _sanitize_path_part(str(type_label or ""))
        if not target_name:
            return
        local_root = self._config_storage.local_versions_root_dir()
        backup_root = self._config_storage.backup_root_dir()
        local_dir = Path(local_root) / target_name
        backup_dir = Path(backup_root) / target_name
        try:
            if local_dir.is_dir():
                shutil.rmtree(local_dir, ignore_errors=True)
        except OSError:
            pass
        try:
            if backup_dir.is_dir():
                shutil.rmtree(backup_dir, ignore_errors=True)
        except OSError:
            pass
        try:
            self._mgr.delete_config_file_versions_by_type_label(device_type_label=str(type_label))
        except Exception:
            pass
