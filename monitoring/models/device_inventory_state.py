from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from monitoring.models.device import Device


@dataclass
class DeviceInventoryState:
    type_definitions: Dict[str, dict] = field(default_factory=dict)
    device_data: Dict[str, Dict[str, Device]] = field(default_factory=dict)
    do_run: Dict[str, bool] = field(default_factory=dict)
    notify_flags: Dict[str, Dict[str, bool]] = field(default_factory=dict)

    def sync_type_definitions(self, type_definitions: Dict[str, dict]) -> None:
        self.type_definitions = dict(type_definitions)
        active_types = set(self.type_definitions.keys())
        monitored_types = {
            dtype for dtype, meta in self.type_definitions.items() if bool(meta.get("monitoring_enabled", True))
        }
        self.device_data = {dtype: devices for dtype, devices in self.device_data.items() if dtype in active_types}
        self.notify_flags = {dtype: flags for dtype, flags in self.notify_flags.items() if dtype in active_types}
        self.do_run = {dtype: bool(self.do_run.get(dtype, False)) for dtype in monitored_types}
        for dtype, meta in self.type_definitions.items():
            self.device_data.setdefault(dtype, {})
            self.notify_flags.setdefault(dtype, {})
            if bool(meta.get("monitoring_enabled", True)):
                self.do_run.setdefault(dtype, False)

    def replace_inventory(
        self,
        *,
        type_definitions: Dict[str, dict],
        device_data: Dict[str, Dict[str, Device]],
        notify_flags: Dict[str, Dict[str, bool]],
    ) -> None:
        self.sync_type_definitions(type_definitions)
        self.device_data = dict(device_data)
        self.notify_flags = dict(notify_flags)
        for dtype, meta in self.type_definitions.items():
            self.device_data.setdefault(dtype, {})
            self.notify_flags.setdefault(dtype, {})
            if bool(meta.get("monitoring_enabled", True)):
                self.do_run.setdefault(dtype, False)

    def device_notify_flag(self, device_type: str, device_id: str, default: bool = True) -> bool:
        return bool(self.notify_flags.get(device_type, {}).get(str(device_id), default))

    def device(self, device_type: str, device_id: str) -> Device | None:
        return self.device_data.get(device_type, {}).get(str(device_id))

    def remember_device(self, *, device_type: str, device_id: str, device: Device, notify: bool) -> None:
        if bool(self.type_definitions.get(device_type, {}).get("monitoring_enabled", False)):
            self.do_run.setdefault(device_type, False)
        self.device_data.setdefault(device_type, {})[str(device_id)] = device
        self.notify_flags.setdefault(device_type, {})[str(device_id)] = bool(notify)

    def update_notify_flag(self, device_type: str, device_id: str, notify: bool) -> None:
        self.notify_flags.setdefault(device_type, {})[str(device_id)] = bool(notify)

    def forget_device(self, device_type: str, device_id: str) -> bool:
        normalized_id = str(device_id)
        if normalized_id not in self.device_data.get(device_type, {}):
            return False
        del self.device_data[device_type][normalized_id]
        self.notify_flags.setdefault(device_type, {}).pop(normalized_id, None)
        return True

    def reset_status(self, device_type: str | None = None) -> List[str]:
        targets = [device_type] if device_type in self.do_run else list(self.device_data.keys())
        for dtype in targets:
            for device in self.device_data.get(dtype, {}).values():
                device.status = "idle"
        return targets

    def build_status_snapshot(self) -> Dict[str, List[dict]]:
        snapshot: Dict[str, List[dict]] = {}
        for dtype, devices in self.device_data.items():
            entries: List[dict] = []
            for device_id, device in devices.items():
                entries.append(
                    {
                        "id": str(device_id),
                        "type": str(dtype),
                        "name": str(getattr(device, "name", "")),
                        "ip": str(getattr(device, "ip", "")),
                        "description": str(getattr(device, "description", "")),
                        "status": str(getattr(device, "status", "idle")),
                        "notify": self.device_notify_flag(dtype, str(device_id), default=False),
                        "subtype": str(getattr(device, "type", "")),
                        "teamviewer_id": str(getattr(device, "id_Teamviewer", "")),
                        "action_double_click": str(getattr(device, "action_double_click", "")),
                        "web_url": str(getattr(device, "web_url", "")),
                        "ssh_user": str(getattr(device, "ssh_user", "")),
                    }
                )
            snapshot[dtype] = entries
        return snapshot
