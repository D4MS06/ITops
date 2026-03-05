from __future__ import annotations

import uuid
from typing import Callable, Dict, List, Optional

from monitoring.models.device import Device
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.utils.exceptions import DeviceReadingError
from monitoring.utils.logger import log_with_timestamp


class DevicesModel:
    """Store devices, notify observers, and track notification flags."""

    def __init__(self) -> None:
        self._mgr = SQLiteFileManager()
        self.type_definitions: Dict[str, dict] = {}
        self._refresh_type_definitions()

        self.device_data: Dict[str, Dict[str, Device]] = {}
        self.do_run: Dict[str, bool] = {
            dtype: False for dtype, meta in self.type_definitions.items() if bool(meta.get("monitoring_enabled", True))
        }
        self.notify_flags: Dict[str, Dict[str, bool]] = {dtype: {} for dtype in self.type_definitions}
        self._observers: List[Callable[[], None]] = []

        self.read_devices()
        log_with_timestamp("Global dictionary after init")
        self.print_global_device_data()

    def add_observer(self, callback: Callable[[], None]) -> None:
        self._observers.append(callback)

    def _notify_observers(self) -> None:
        for cb in list(self._observers):
            try:
                cb()
            except Exception:
                continue

    def _refresh_type_definitions(self) -> None:
        types = self._mgr.list_device_types()
        self.type_definitions = {str(t["code"]): t for t in types if str(t.get("code", "")).strip()}
        self.type_definitions.setdefault(
            "switch",
            {"code": "switch", "label": "Switch", "icon": "switch", "monitoring_enabled": True},
        )
        self.type_definitions.setdefault(
            "server",
            {"code": "server", "label": "Serveur", "icon": "server", "monitoring_enabled": True},
        )

    def refresh_type_definitions(self) -> None:
        self._refresh_type_definitions()
        for dtype, meta in self.type_definitions.items():
            if bool(meta.get("monitoring_enabled", True)):
                self.do_run.setdefault(dtype, False)
            self.notify_flags.setdefault(dtype, {})
            self.device_data.setdefault(dtype, {})

    def _type_template(self, dtype: str) -> str:
        raw_icon = str(self.type_definitions.get(dtype, {}).get("icon", "")).strip().lower()
        if raw_icon in {"switch", "server"}:
            return raw_icon
        return "server" if dtype == "server" else "switch"

    def is_server_like_type(self, dtype: str) -> bool:
        return self._type_template(dtype) == "server"

    def is_config_download_type(self, dtype: str) -> bool:
        return self._type_template(dtype) == "switch"

    @staticmethod
    def _apply_remote_fields(dev: Device, item: dict) -> None:
        dev.id_Teamviewer = str(item.get("id_Teamviewer", "") or "")
        dev.type = str(item.get("type", "") or "")
        dev.action_double_click = str(item.get("action_double_click", "") or "")
        dev.web_url = str(item.get("web_url", "") or "")
        dev.ssh_user = str(item.get("ssh_user", "") or "")

    @staticmethod
    def _apply_custom_fields(dev: Device, item: dict) -> None:
        custom_data = item.get("custom_data", {})
        if not isinstance(custom_data, dict):
            return
        for key, value in custom_data.items():
            k = str(key).strip()
            if not k:
                continue
            setattr(dev, k, str(value))

    @staticmethod
    def extract_custom_data(dev: Device) -> dict[str, str]:
        base_keys = {
            "id",
            "ip",
            "name",
            "description",
            "device_type",
            "status",
            "id_Teamviewer",
            "type",
            "action_double_click",
            "web_url",
            "ssh_user",
        }
        return {
            str(k): str(v)
            for k, v in vars(dev).items()
            if str(k) not in base_keys and not str(k).startswith("_")
        }

    def print_global_device_data(self) -> None:
        for dtype, devices in self.device_data.items():
            log_with_timestamp(f"Type: {dtype}")
            for did, dev in devices.items():
                notif = "ON" if self.notify_flags[dtype].get(did, False) else "OFF"
                if self.is_server_like_type(dtype):
                    stype = getattr(dev, "type", "")
                    tv_id = getattr(dev, "id_Teamviewer", "")
                    action = getattr(dev, "action_double_click", "")
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, "
                        f"Desc:{dev.description}, Type:{stype}, TV:{tv_id}, "
                        f"Action:{action}, Notify:{notif}"
                    )
                else:
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, Desc:{dev.description}, Notify:{notif}"
                    )

    def read_devices(self) -> None:
        """Load devices and notify flags from SQLite."""
        self._refresh_type_definitions()
        data = self._mgr.read_devices_map()
        if not isinstance(data, dict):
            raise DeviceReadingError("Unexpected data format.")

        for dtype, meta in self.type_definitions.items():
            if bool(meta.get("monitoring_enabled", True)):
                self.do_run.setdefault(dtype, False)
            self.notify_flags.setdefault(dtype, {})
            self.device_data.setdefault(dtype, {})

        for dtype, items in data.items():
            self.do_run.setdefault(dtype, False)
            self.device_data[dtype] = {}
            self.notify_flags[dtype] = {}
            for item in items:
                did = str(item["id"])
                dev = Device(
                    ip=item["ip"],
                    name=item["name"],
                    description=item["description"],
                    device_type=dtype,
                    device_id=did,
                )
                self._apply_remote_fields(dev, item)
                self._apply_custom_fields(dev, item)
                self.device_data[dtype][did] = dev
                self.notify_flags[dtype][did] = bool(item.get("notify", True))

    def update_json_file(self) -> None:
        """Backwards compatibility helper: write current state to SQLite."""
        data: Dict[str, List[dict]] = {}
        for dtype, devices in self.device_data.items():
            entries: List[dict] = []
            for did, dev in devices.items():
                entry = {
                    "id": did,
                    "name": dev.name,
                    "ip": dev.ip,
                    "description": dev.description,
                    "notify": self.notify_flags.get(dtype, {}).get(did, True),
                }
                entry["id_Teamviewer"] = getattr(dev, "id_Teamviewer", "")
                entry["type"] = getattr(dev, "type", "")
                entry["action_double_click"] = getattr(dev, "action_double_click", "")
                entry["web_url"] = getattr(dev, "web_url", "")
                entry["ssh_user"] = getattr(dev, "ssh_user", "")
                entry["custom_data"] = self.extract_custom_data(dev)
                entries.append(entry)
            data[dtype] = entries
        self._mgr.write_devices_map(data)

    def add_device(
        self,
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
    ) -> Optional[str]:
        """Add a device. Return ID or None if duplicate IP in the same type."""
        normalized_ip = str(ip or "").strip()
        if normalized_ip:
            for dev in self.device_data.get(device_type, {}).values():
                if str(getattr(dev, "ip", "")).strip() == normalized_ip:
                    return None

        new_id = self.generate_unique_id()
        new_dev = Device(
            ip=normalized_ip,
            name=str(name or "").strip(),
            description=str(description or "").strip(),
            device_type=device_type,
            device_id=new_id,
        )
        self._apply_remote_fields(
            new_dev,
            {
                "id_Teamviewer": id_Teamviewer or "",
                "type": device_subtype or "",
                "action_double_click": action_double_click or "",
                "web_url": web_url or "",
                "ssh_user": ssh_user or "",
            },
        )
        self._apply_custom_fields(new_dev, {"custom_data": custom_data or {}})

        new_dev.status = "idle"
        if bool(self.type_definitions.get(device_type, {}).get("monitoring_enabled", True)):
            self.do_run.setdefault(device_type, False)
        self.device_data.setdefault(device_type, {})[new_id] = new_dev
        self.notify_flags.setdefault(device_type, {})[new_id] = notify

        self.update_json_file()
        self._notify_observers()
        return new_id

    def update_device(
        self,
        device_type: str,
        device_id: str,
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
    ) -> bool:
        """Update a device and notify observers."""
        device_id = str(device_id)
        dev = self.device_data.get(device_type, {}).get(device_id)
        if not dev:
            return False

        dev.name = new_name
        dev.ip = new_ip
        dev.description = new_description
        if id_Teamviewer is not None:
            dev.id_Teamviewer = id_Teamviewer
        if device_subtype is not None:
            dev.type = device_subtype
        if action_double_click is not None:
            dev.action_double_click = action_double_click
        if web_url is not None:
            dev.web_url = web_url
        if ssh_user is not None:
            dev.ssh_user = ssh_user
        if custom_data is not None:
            self._apply_custom_fields(dev, {"custom_data": custom_data})

        if notify is not None:
            self.notify_flags.setdefault(device_type, {})[device_id] = notify

        self.update_json_file()
        self._notify_observers()
        return True

    def delete_device(self, device_type: str, device_id: str) -> bool:
        """Delete a device and notify observers."""
        device_id = str(device_id)
        if device_id in self.device_data.get(device_type, {}):
            del self.device_data[device_type][device_id]
            self.notify_flags.setdefault(device_type, {}).pop(device_id, None)
            self.update_json_file()
            self._notify_observers()
            return True
        return False

    def reset_devices_status(self, device_type: Optional[str] = None) -> None:
        targets = [device_type] if device_type in self.do_run else list(self.device_data.keys())
        for dtype in targets:
            for dev in self.device_data.get(dtype, {}).values():
                dev.status = "idle"
        log_with_timestamp(f"reset_devices_status for {targets}")

    @staticmethod
    def generate_unique_id() -> str:
        return str(uuid.uuid4())

    def build_status_snapshot(self) -> Dict[str, List[dict]]:
        """Return a JSON-ready snapshot of all devices."""
        snapshot: Dict[str, List[dict]] = {}
        for dtype, devices in self.device_data.items():
            entries: List[dict] = []
            for did, dev in devices.items():
                record = {
                    "id": str(did),
                    "type": str(dtype),
                    "name": str(getattr(dev, "name", "")),
                    "ip": str(getattr(dev, "ip", "")),
                    "description": str(getattr(dev, "description", "")),
                    "status": str(getattr(dev, "status", "idle")),
                    "notify": bool(self.notify_flags.get(dtype, {}).get(did, False)),
                }
                record.update(
                    {
                        "subtype": str(getattr(dev, "type", "")),
                        "teamviewer_id": str(getattr(dev, "id_Teamviewer", "")),
                        "action_double_click": str(getattr(dev, "action_double_click", "")),
                        "web_url": str(getattr(dev, "web_url", "")),
                        "ssh_user": str(getattr(dev, "ssh_user", "")),
                    }
                )
                entries.append(record)
            snapshot[dtype] = entries
        return snapshot
