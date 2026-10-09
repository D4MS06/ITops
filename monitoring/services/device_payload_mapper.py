from __future__ import annotations

from monitoring.models.device import Device


class DevicePayloadMapper:
    @classmethod
    def deserialize_device(cls, *, dtype: str, item: dict, device_id: str) -> Device:
        device = Device(
            ip=str(item.get("ip", "")).strip(),
            name=str(item.get("name", "")).strip(),
            description=str(item.get("description", "")).strip(),
            device_type=str(dtype),
            device_id=str(device_id),
        )
        cls.apply_remote_fields(device, item)
        cls.apply_custom_fields(device, item.get("custom_data", {}))
        return device

    @classmethod
    def serialize_device(cls, *, device_id: str, device: Device, notify: bool | None) -> dict:
        raw_password = str(getattr(device, "device_password", "") or "")
        has_password = bool(raw_password)
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
            "device_login": str(getattr(device, "device_login", "")),
            "device_password": raw_password,
            "has_device_password": has_password,
            "device_password_masked": "****" if has_password else "",
            "custom_data": cls.extract_custom_data(device),
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
            "device_login",
            "device_password",
            "has_device_password",
            "device_password_masked",
        }
        return {
            str(key): str(value)
            for key, value in vars(device).items()
            if str(key) not in base_keys and not str(key).startswith("_")
        }

    @staticmethod
    def apply_remote_fields(device: Device, item: dict) -> None:
        device.id_Teamviewer = str(item.get("id_Teamviewer", "") or "")
        device.type = str(item.get("type", "") or "")
        device.action_double_click = str(item.get("action_double_click", "") or "")
        device.web_url = str(item.get("web_url", "") or "")
        device.ssh_user = str(item.get("ssh_user", "") or "")
        device.device_login = str(item.get("device_login", "") or "")
        device.device_password = str(item.get("device_password", "") or "")

    @staticmethod
    def apply_custom_fields(device: Device, custom_data: dict) -> None:
        if not isinstance(custom_data, dict):
            return
        for key, value in custom_data.items():
            normalized_key = str(key).strip()
            if not normalized_key:
                continue
            setattr(device, normalized_key, str(value))

    @classmethod
    def replace_custom_fields(cls, device: Device, custom_data: dict) -> None:
        for key in list(cls.extract_custom_data(device).keys()):
            try:
                delattr(device, key)
            except AttributeError:
                continue
        cls.apply_custom_fields(device, custom_data or {})
