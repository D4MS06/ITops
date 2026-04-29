from __future__ import annotations

from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.ui.utils.action_compat import action_allows_os, normalize_platform


class DeviceFormService:
    """Service de lecture des metadonnees de formulaire device."""

    def __init__(self, manager: MariaDBFileManager | None = None) -> None:
        self._mgr = manager or MariaDBFileManager()
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
        platform = normalize_platform(platform_label)
        keys: list[str] = []
        for action in actions:
            action_key = str(action.get("action_key", "")).strip().lower()
            if not action_key:
                continue
            if not action_allows_os(str(action.get("os_scope", "")), platform):
                continue
            keys.append(action_key)
        return keys
