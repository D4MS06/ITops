from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from monitoring.storage.sqlite_manager import SQLiteFileManager


class DeviceTypeService:
    """Service metier autour des types d'equipements et de leurs schemas."""

    def __init__(self, manager: SQLiteFileManager | None = None) -> None:
        self._mgr = manager or SQLiteFileManager()

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
        return list(self._mgr.list_device_types())

    def list_fields(self, type_code: str) -> list[dict]:
        fields = list(self._mgr.list_type_fields(str(type_code or "").strip().lower()))
        return sorted(fields, key=lambda x: int(x.get("sort_order", 0)))

    def list_actions(self, type_code: str) -> list[dict]:
        actions = list(self._mgr.list_type_actions(str(type_code or "").strip().lower()))
        return sorted(actions, key=lambda x: int(x.get("sort_order", 0)))

    def load_schema(self, type_code: str) -> tuple[list[dict], list[dict]]:
        fields = self.list_fields(type_code)
        actions = self.list_actions(type_code)
        for action in actions:
            scope = str(action.get("os_scope", "")).strip()
            if scope:
                continue
            action["os_scope"] = self._format_os_scope(["windows", "linux", "firmware", "autre"])
        return fields, actions

    def save_type(self, *, code: str, label: str, monitoring_enabled: bool) -> str:
        return self._mgr.save_device_type(
            code=str(code or "").strip().lower(),
            label=str(label or "").strip(),
            monitoring_enabled=bool(monitoring_enabled),
        )

    def create_type(self, *, label: str, monitoring_enabled: bool) -> str:
        generated_code = self.generate_unique_code(label)
        return self.save_type(code=generated_code, label=label, monitoring_enabled=monitoring_enabled)

    def delete_type(self, code: str) -> bool:
        return bool(self._mgr.delete_device_type(str(code or "").strip().lower()))

    def replace_schema(self, *, type_code: str, fields: Iterable[dict], actions: Iterable[dict]) -> None:
        self._mgr.replace_type_schema(
            type_code=str(type_code or "").strip().lower(),
            fields=list(fields),
            actions=list(actions),
        )
    @staticmethod
    def _normalize_os(value: str) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"windows", "linux", "firmware", "autre"}:
            return raw
        return "autre"

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

