from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from monitoring.models.device import Device
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.utils.exceptions import DeviceReadingError


@dataclass(frozen=True)
class DeviceMutationResult:
    device_id: str
    device: Device
    notify: bool


class DeviceService:
    """Service metier pour le chargement, le CRUD et la serialisation des equipements."""

    _DEFAULT_TYPES = (
        {
            "code": "switch",
            "label": "Switch",
            "icon": "switch",
            "monitoring_enabled": True,
            "config_backups_enabled": True,
        },
        {
            "code": "server",
            "label": "Serveur",
            "icon": "server",
            "monitoring_enabled": True,
            "config_backups_enabled": False,
        },
    )

    def __init__(self, manager: SQLiteFileManager | None = None) -> None:
        self._mgr = manager or SQLiteFileManager()

    def list_type_definitions(self) -> Dict[str, dict]:
        types = {
            str(item["code"]): dict(item)
            for item in self._mgr.list_device_types()
            if str(item.get("code", "")).strip()
        }
        for fallback in self._DEFAULT_TYPES:
            types.setdefault(str(fallback["code"]), dict(fallback))
        return types

    def load_devices(self) -> Dict[str, List[dict]]:
        data = self._mgr.read_devices_map()
        if not isinstance(data, dict):
            raise DeviceReadingError("Unexpected data format.")
        return data

    def build_device_inventory(
        self,
        *,
        type_definitions: Dict[str, dict],
    ) -> tuple[Dict[str, Dict[str, Device]], Dict[str, Dict[str, bool]]]:
        device_data: Dict[str, Dict[str, Device]] = {dtype: {} for dtype in type_definitions}
        notify_flags: Dict[str, Dict[str, bool]] = {dtype: {} for dtype in type_definitions}

        for dtype, items in self.load_devices().items():
            device_data.setdefault(dtype, {})
            notify_flags.setdefault(dtype, {})
            for item in items:
                device = self.deserialize_device(dtype=dtype, item=item)
                device_data[dtype][device.id] = device
                notify_flags[dtype][device.id] = bool(item.get("notify", True))
        return device_data, notify_flags

    def list_devices(
        self,
        *,
        device_data: Dict[str, Dict[str, Device]],
        notify_flags: Dict[str, Dict[str, bool]],
        device_type: str | None = None,
    ) -> List[dict]:
        items: List[dict] = []
        for dtype, devices in device_data.items():
            if device_type is not None and str(dtype) != str(device_type):
                continue
            for device_id, device in devices.items():
                entry = self.serialize_device(
                    device_type=dtype,
                    device_id=str(device_id),
                    device=device,
                    notify=notify_flags.get(dtype, {}).get(str(device_id), True),
                )
                entry["device_type"] = str(dtype)
                items.append(entry)
        return items

    def search_devices(
        self,
        *,
        device_data: Dict[str, Dict[str, Device]],
        notify_flags: Dict[str, Dict[str, bool]],
        query: str,
        device_type: str | None = None,
    ) -> List[dict]:
        needle = str(query or "").strip().lower()
        if not needle:
            return self.list_devices(device_data=device_data, notify_flags=notify_flags, device_type=device_type)
        matches: List[dict] = []
        for item in self.list_devices(device_data=device_data, notify_flags=notify_flags, device_type=device_type):
            custom_blob = " ".join(str(value) for value in item.get("custom_data", {}).values()).lower()
            haystack = " ".join(
                [
                    str(item.get("name", "")),
                    str(item.get("ip", "")),
                    str(item.get("description", "")),
                    str(item.get("device_type", "")),
                    custom_blob,
                ]
            ).lower()
            if needle in haystack:
                matches.append(item)
        return matches

    def deserialize_device(self, *, dtype: str, item: dict) -> Device:
        did = str(item.get("id", "")).strip() or self.generate_unique_id()
        device = Device(
            ip=str(item.get("ip", "")).strip(),
            name=str(item.get("name", "")).strip(),
            description=str(item.get("description", "")).strip(),
            device_type=str(dtype),
            device_id=did,
        )
        self._apply_remote_fields(device, item)
        self._apply_custom_fields(device, item.get("custom_data", {}))
        return device

    def create_device(
        self,
        *,
        type_definitions: Dict[str, dict],
        existing_devices: Dict[str, Dict[str, Device]],
        device_type: str,
        name: str,
        ip: str,
        description: str,
        id_Teamviewer: Optional[str] = None,
        device_subtype: Optional[str] = None,
        action_double_click: Optional[str] = None,
        web_url: Optional[str] = None,
        ssh_user: Optional[str] = None,
        custom_data: Optional[dict] = None,
        notify: bool = True,
    ) -> DeviceMutationResult | None:
        normalized_type = self._validate_device_type(device_type, type_definitions)
        normalized_name = str(name or "").strip()
        normalized_ip = str(ip or "").strip()
        normalized_description = str(description or "").strip()
        self._validate_device_fields(
            device_type=normalized_type,
            type_definitions=type_definitions,
            existing_devices=existing_devices,
            name=normalized_name,
            ip=normalized_ip,
        )

        device_id = self.generate_unique_id()
        device = Device(
            ip=normalized_ip,
            name=normalized_name,
            description=normalized_description,
            device_type=normalized_type,
            device_id=device_id,
        )
        self._apply_remote_fields(
            device,
            {
                "id_Teamviewer": id_Teamviewer,
                "type": device_subtype,
                "action_double_click": action_double_click,
                "web_url": web_url,
                "ssh_user": ssh_user,
            },
        )
        self._apply_custom_fields(device, custom_data or {})
        self.save_device(dtype=normalized_type, device=device, notify=notify)
        return DeviceMutationResult(device_id=device_id, device=device, notify=bool(notify))

    def update_device(
        self,
        *,
        type_definitions: Dict[str, dict],
        existing_devices: Dict[str, Dict[str, Device]],
        device_type: str,
        device_id: str,
        current_device: Device | None,
        new_name: str,
        new_ip: str,
        new_description: str,
        id_Teamviewer: Optional[str] = None,
        device_subtype: Optional[str] = None,
        action_double_click: Optional[str] = None,
        web_url: Optional[str] = None,
        ssh_user: Optional[str] = None,
        custom_data: Optional[dict] = None,
        notify: Optional[bool] = None,
    ) -> DeviceMutationResult | None:
        normalized_type = self._validate_device_type(device_type, type_definitions)
        if current_device is None:
            return None

        normalized_name = str(new_name or "").strip()
        normalized_ip = str(new_ip or "").strip()
        normalized_description = str(new_description or "").strip()
        self._validate_device_fields(
            device_type=normalized_type,
            type_definitions=type_definitions,
            existing_devices=existing_devices,
            name=normalized_name,
            ip=normalized_ip,
            exclude_device_id=str(device_id),
        )

        current_device.name = normalized_name
        current_device.ip = normalized_ip
        current_device.description = normalized_description
        self._apply_remote_fields(
            current_device,
            {
                "id_Teamviewer": id_Teamviewer if id_Teamviewer is not None else getattr(current_device, "id_Teamviewer", ""),
                "type": device_subtype if device_subtype is not None else getattr(current_device, "type", ""),
                "action_double_click": action_double_click if action_double_click is not None else getattr(current_device, "action_double_click", ""),
                "web_url": web_url if web_url is not None else getattr(current_device, "web_url", ""),
                "ssh_user": ssh_user if ssh_user is not None else getattr(current_device, "ssh_user", ""),
            },
        )
        if custom_data is not None:
            self._replace_custom_fields(current_device, custom_data)

        self.save_device(dtype=normalized_type, device=current_device, notify=(notify if notify is not None else None))
        return DeviceMutationResult(
            device_id=str(device_id),
            device=current_device,
            notify=True if notify is None else bool(notify),
        )

    def save_device(self, *, dtype: str, device: Device, notify: bool | None) -> None:
        payload = self.serialize_device(device_type=dtype, device_id=str(device.id), device=device, notify=notify)
        self._mgr.upsert_device(dtype=dtype, item=payload)

    def delete_device(self, *, device_id: str) -> bool:
        return bool(self._mgr.delete_device(device_id=str(device_id)))

    def write_devices_map(
        self,
        *,
        device_data: Dict[str, Dict[str, Device]],
        notify_flags: Dict[str, Dict[str, bool]],
    ) -> None:
        serialized: Dict[str, List[dict]] = {}
        for dtype, devices in device_data.items():
            serialized[dtype] = [
                self.serialize_device(
                    device_type=dtype,
                    device_id=str(device_id),
                    device=device,
                    notify=notify_flags.get(dtype, {}).get(str(device_id), True),
                )
                for device_id, device in devices.items()
            ]
        self._mgr.write_devices_map(serialized)

    def serialize_device(self, *, device_type: str, device_id: str, device: Device, notify: bool | None) -> dict:
        return {
            "id": str(device_id),
            "name": str(device.name),
            "ip": str(device.ip),
            "description": str(device.description),
            "notify": True if notify is None else bool(notify),
            "id_Teamviewer": str(getattr(device, "id_Teamviewer", "")),
            "type": str(getattr(device, "type", "")),
            "action_double_click": str(getattr(device, "action_double_click", "")),
            "web_url": str(getattr(device, "web_url", "")),
            "ssh_user": str(getattr(device, "ssh_user", "")),
            "custom_data": self.extract_custom_data(device),
        }

    @staticmethod
    def extract_custom_data(device: Device) -> dict[str, str]:
        base_keys = {
            "id",
            "ip",
            "name",
            "description",
            "device_type",
            "status",
            "is_monitoring",
            "treeview_item",
            "id_Teamviewer",
            "type",
            "action_double_click",
            "web_url",
            "ssh_user",
        }
        return {
            str(key): str(value)
            for key, value in vars(device).items()
            if str(key) not in base_keys and not str(key).startswith("_")
        }

    @staticmethod
    def generate_unique_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _apply_remote_fields(device: Device, item: dict) -> None:
        device.id_Teamviewer = str(item.get("id_Teamviewer", "") or "")
        device.type = str(item.get("type", "") or "")
        device.action_double_click = str(item.get("action_double_click", "") or "")
        device.web_url = str(item.get("web_url", "") or "")
        device.ssh_user = str(item.get("ssh_user", "") or "")

    @staticmethod
    def _apply_custom_fields(device: Device, custom_data: dict) -> None:
        if not isinstance(custom_data, dict):
            return
        for key, value in custom_data.items():
            normalized_key = str(key).strip()
            if not normalized_key:
                continue
            setattr(device, normalized_key, str(value))

    def _replace_custom_fields(self, device: Device, custom_data: dict) -> None:
        for key in list(self.extract_custom_data(device).keys()):
            try:
                delattr(device, key)
            except AttributeError:
                continue
        self._apply_custom_fields(device, custom_data or {})

    def _validate_device_type(self, device_type: str, type_definitions: Dict[str, dict]) -> str:
        normalized_type = str(device_type or "").strip()
        if not normalized_type or normalized_type not in type_definitions:
            raise ValueError("Type d'equipement inconnu.")
        return normalized_type

    def _validate_device_fields(
        self,
        *,
        device_type: str,
        type_definitions: Dict[str, dict],
        existing_devices: Dict[str, Dict[str, Device]],
        name: str,
        ip: str,
        exclude_device_id: str | None = None,
    ) -> None:
        if not name:
            raise ValueError("Nom d'equipement requis.")
        if bool(type_definitions.get(device_type, {}).get("monitoring_enabled", True)) and not ip:
            raise ValueError("Adresse IP requise.")
        if not ip:
            return
        for current_id, device in existing_devices.get(device_type, {}).items():
            if exclude_device_id is not None and str(current_id) == str(exclude_device_id):
                continue
            if str(getattr(device, "ip", "")).strip() == ip:
                raise ValueError("Adresse IP deja utilisee pour ce type.")
