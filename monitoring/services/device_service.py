from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from monitoring.models.device import Device
from monitoring.config.settings import _secrets_store
from monitoring.services.device_action_policy import validate_action_double_click
from monitoring.services.device_payload_mapper import DevicePayloadMapper
from monitoring.services.device_validation import validate_device_fields, validate_device_type
from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.utils.exceptions import DeviceReadingError


@dataclass(frozen=True)
class DeviceMutationResult:
    device_id: str
    device: Device
    notify: bool


class DeviceService:
    """Source unique de l'inventaire réseau.

    Le module Équipements réseau possède le CRUD, les types, configurations et
    identifiants. Monitoring consomme le même modèle en lecture pour sonder ces
    équipements : il ne maintient ni copie métier ni table parallèle.
    """

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

    def __init__(self, manager: MariaDBFileManager | None = None) -> None:
        self._mgr = manager or MariaDBFileManager()

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
        # Migration is lazy and transactional in spirit: never erase the legacy
        # database value until it has been written and read back from the vault.
        secrets = _secrets_store()
        for dtype, items in data.items():
            for item in items:
                device_id = str(item.get("id") or "").strip()
                if not device_id:
                    continue
                account = self._device_secret_account(dtype, device_id)
                legacy_password = str(item.get("device_password") or "")
                if legacy_password:
                    secrets.set_or_delete_password(account, legacy_password)
                    if secrets.get_password(account) != legacy_password:
                        raise DeviceReadingError(f"Migration coffre impossible pour l'equipement {device_id}.")
                    self._mgr.clear_device_password(device_id=device_id)
                item["device_password"] = secrets.get_password(account)
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
        for dtype, devices in device_data.items():
            if device_type is not None and str(dtype) != str(device_type):
                continue
            for device_id, device in devices.items():
                item = self.serialize_device(
                    device_type=dtype,
                    device_id=str(device_id),
                    device=device,
                    notify=notify_flags.get(dtype, {}).get(str(device_id), True),
                )
                item["device_type"] = str(dtype)
                custom_blob = " ".join(str(value) for value in item.get("custom_data", {}).values()).lower()
                haystack = " ".join(
                    [
                        str(item.get("name", "")),
                        str(item.get("ip", "")),
                        str(item.get("description", "")),
                        str(item.get("device_type", "")),
                        str(item.get("device_login", "")),
                        custom_blob,
                    ]
                ).lower()
                if needle in haystack:
                    matches.append(item)
        return matches

    def deserialize_device(self, *, dtype: str, item: dict) -> Device:
        did = str(item.get("id", "")).strip() or self.generate_unique_id()
        return DevicePayloadMapper.deserialize_device(dtype=dtype, item=item, device_id=did)

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
        device_login: Optional[str] = None,
        device_password: Optional[str] = None,
        custom_data: Optional[dict] = None,
        notify: bool = True,
    ) -> DeviceMutationResult | None:
        normalized_type = validate_device_type(device_type, type_definitions)
        normalized_name = str(name or "").strip()
        normalized_ip = str(ip or "").strip()
        normalized_description = str(description or "").strip()
        validate_device_fields(
            device_type=normalized_type,
            type_definitions=type_definitions,
            existing_devices=existing_devices,
            name=normalized_name,
            ip=normalized_ip,
        )
        schema_fields = list(self._mgr.list_type_fields(normalized_type))
        schema_actions = list(self._mgr.list_type_actions(normalized_type))
        validate_action_double_click(
            fields=schema_fields,
            actions=schema_actions,
            device_subtype=str(device_subtype or ""),
            action_double_click=str(action_double_click or ""),
        )

        device_id = self.generate_unique_id()
        device = Device(
            ip=normalized_ip,
            name=normalized_name,
            description=normalized_description,
            device_type=normalized_type,
            device_id=device_id,
        )
        DevicePayloadMapper.apply_remote_fields(
            device,
            {
                "id_Teamviewer": id_Teamviewer,
                "type": device_subtype,
                "action_double_click": action_double_click,
                "web_url": web_url,
                "ssh_user": ssh_user,
                "device_login": device_login,
                "device_password": device_password,
            },
        )
        DevicePayloadMapper.apply_custom_fields(device, custom_data or {})
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
        device_login: Optional[str] = None,
        device_password: Optional[str] = None,
        custom_data: Optional[dict] = None,
        notify: Optional[bool] = None,
    ) -> DeviceMutationResult | None:
        normalized_type = validate_device_type(device_type, type_definitions)
        if current_device is None:
            return None

        normalized_name = str(new_name or "").strip()
        normalized_ip = str(new_ip or "").strip()
        normalized_description = str(new_description or "").strip()
        validate_device_fields(
            device_type=normalized_type,
            type_definitions=type_definitions,
            existing_devices=existing_devices,
            name=normalized_name,
            ip=normalized_ip,
            exclude_device_id=str(device_id),
        )
        effective_subtype = (
            device_subtype
            if device_subtype is not None
            else getattr(current_device, "type", "")
        )
        effective_action = (
            action_double_click
            if action_double_click is not None
            else getattr(current_device, "action_double_click", "")
        )
        schema_fields = list(self._mgr.list_type_fields(normalized_type))
        schema_actions = list(self._mgr.list_type_actions(normalized_type))
        validate_action_double_click(
            fields=schema_fields,
            actions=schema_actions,
            device_subtype=str(effective_subtype or ""),
            action_double_click=str(effective_action or ""),
        )

        current_device.name = normalized_name
        current_device.ip = normalized_ip
        current_device.description = normalized_description
        DevicePayloadMapper.apply_remote_fields(
            current_device,
            {
                "id_Teamviewer": id_Teamviewer if id_Teamviewer is not None else getattr(current_device, "id_Teamviewer", ""),
                "type": device_subtype if device_subtype is not None else getattr(current_device, "type", ""),
                "action_double_click": action_double_click if action_double_click is not None else getattr(current_device, "action_double_click", ""),
                "web_url": web_url if web_url is not None else getattr(current_device, "web_url", ""),
                "ssh_user": ssh_user if ssh_user is not None else getattr(current_device, "ssh_user", ""),
                "device_login": device_login if device_login is not None else getattr(current_device, "device_login", ""),
                "device_password": device_password if device_password is not None else getattr(current_device, "device_password", ""),
            },
        )
        if custom_data is not None:
            DevicePayloadMapper.replace_custom_fields(current_device, custom_data)

        self.save_device(dtype=normalized_type, device=current_device, notify=(notify if notify is not None else None))
        return DeviceMutationResult(
            device_id=str(device_id),
            device=current_device,
            notify=True if notify is None else bool(notify),
        )

    def save_device(self, *, dtype: str, device: Device, notify: bool | None) -> None:
        payload = self.serialize_device(device_type=dtype, device_id=str(device.id), device=device, notify=notify)
        password = str(payload.get("device_password") or "")
        account = self._device_secret_account(dtype, str(device.id))
        secrets = _secrets_store()
        if password:
            secrets.set_or_delete_password(account, password)
            if secrets.get_password(account) != password:
                raise RuntimeError("Ecriture du mot de passe equipement dans le coffre impossible.")
        else:
            secrets.delete_password(account)
        # MariaDB deliberately retains no device password after this migration.
        payload["device_password"] = ""
        self._mgr.upsert_device(dtype=dtype, item=payload)

    def delete_device(self, *, dtype: str, device_id: str) -> bool:
        deleted = bool(self._mgr.delete_device(device_id=str(device_id)))
        if deleted:
            _secrets_store().delete_password(self._device_secret_account(dtype, device_id))
        return deleted

    def set_device_notify(self, *, device_id: str, notify: bool) -> bool:
        return bool(self._mgr.set_device_notify(device_id=str(device_id), notify=bool(notify)))

    def delete_vault_credentials(self, *, dtype: str, device_id: str) -> None:
        _secrets_store().delete_password(self._device_secret_account(dtype, device_id))

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
        secrets = _secrets_store()
        for dtype, items in serialized.items():
            for item in items:
                device_id = str(item.get("id") or "").strip()
                password = str(item.get("device_password") or "")
                if device_id:
                    secrets.set_or_delete_password(self._device_secret_account(dtype, device_id), password)
                item["device_password"] = ""
        self._mgr.write_devices_map(serialized)

    def serialize_device(self, *, device_type: str, device_id: str, device: Device, notify: bool | None) -> dict:
        return DevicePayloadMapper.serialize_device(device_id=device_id, device=device, notify=notify)

    @staticmethod
    def _device_secret_account(dtype: str, device_id: str) -> str:
        return f"__device_credential__{str(dtype or '').strip().lower()}__{str(device_id or '').strip()}"

    @staticmethod
    def extract_custom_data(device: Device) -> dict[str, str]:
        return DevicePayloadMapper.extract_custom_data(device)

    @staticmethod
    def generate_unique_id() -> str:
        return str(uuid.uuid4())
