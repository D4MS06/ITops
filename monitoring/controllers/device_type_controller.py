from __future__ import annotations

from monitoring.services.device_type_service import DeviceTypeService


class DeviceTypeController:
    """Facade controller MVC pour la gestion des types/schemas."""

    def __init__(self, service: DeviceTypeService | None = None) -> None:
        self._service = service or DeviceTypeService()

    def list_types(self) -> list[dict]:
        return self._service.list_types()

    def find_type(self, code: str) -> dict | None:
        key = str(code or "").strip().lower()
        for item in self._service.list_types():
            if str(item.get("code", "")).strip().lower() == key:
                return item
        return None

    def save_type(self, *, code: str, label: str, monitoring_enabled: bool) -> str:
        return self._service.save_type(code=code, label=label, monitoring_enabled=monitoring_enabled)

    def create_type(self, *, label: str, monitoring_enabled: bool) -> str:
        return self._service.create_type(label=label, monitoring_enabled=monitoring_enabled)

    def delete_type(self, code: str) -> bool:
        return self._service.delete_type(code)

    def load_schema(self, type_code: str) -> tuple[list[dict], list[dict]]:
        return self._service.load_schema(type_code)

    def save_schema(self, *, type_code: str, fields: list[dict], actions: list[dict]) -> None:
        self._service.replace_schema(type_code=type_code, fields=fields, actions=actions)

    def generate_type_code(self, label: str) -> str:
        return self._service.generate_unique_code(label)

