from __future__ import annotations

from monitoring.storage.sqlite_manager import SQLiteFileManager


class DeviceFormService:
    """Service de lecture des metadonnees de formulaire device."""

    def __init__(self, manager: SQLiteFileManager | None = None) -> None:
        self._mgr = manager or SQLiteFileManager()
        self._types: list[dict] = []
        self._fields_by_type: dict[str, list[dict]] = {}
        self._actions_by_type: dict[str, list[dict]] = {}
        self.reload()

    def reload(self) -> None:
        self._types = list(self._mgr.list_device_types())
        if not self._types:
            self._types = [
                {"code": "switch", "label": "Switch", "icon": "switch", "monitoring_enabled": True},
                {"code": "server", "label": "Serveur", "icon": "server", "monitoring_enabled": True},
            ]
        self._fields_by_type = {
            str(t["code"]): list(self._mgr.list_type_fields(str(t["code"])))
            for t in self._types
            if str(t.get("code", "")).strip()
        }
        self._actions_by_type = {
            str(t["code"]): list(self._mgr.list_type_actions(str(t["code"])))
            for t in self._types
            if str(t.get("code", "")).strip()
        }

    @property
    def types(self) -> list[dict]:
        return list(self._types)

    @property
    def fields_by_type(self) -> dict[str, list[dict]]:
        return dict(self._fields_by_type)

    @property
    def actions_by_type(self) -> dict[str, list[dict]]:
        return dict(self._actions_by_type)

    def action_options(self, *, type_code: str, platform_label: str) -> list[str]:
        code = str(type_code or "").strip().lower()
        actions = self._actions_by_type.get(code, [])
        platform = self._normalize_platform(platform_label)
        keys: list[str] = []
        for action in actions:
            action_key = str(action.get("action_key", "")).strip().lower()
            if not action_key:
                continue
            if not self._action_allows_os(str(action.get("os_scope", "")), platform):
                continue
            keys.append(action_key)
        return keys
    @staticmethod
    def _normalize_platform(value: str) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"windows", "linux", "firmware", "autre"}:
            return raw
        return "autre"

    @classmethod
    def _action_allows_os(cls, raw_scope: str, platform: str) -> bool:
        scope = {
            cls._normalize_platform(v)
            for v in str(raw_scope or "").split(",")
            if str(v).strip()
        }
        if not scope:
            return True
        return cls._normalize_platform(platform) in scope

