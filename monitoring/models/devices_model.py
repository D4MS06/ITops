from __future__ import annotations

from typing import Callable, Dict, List, Optional

from monitoring.models.device import Device
from monitoring.services.device_service import DeviceService
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.utils.logger import log_with_timestamp


class DevicesModel:
    """Etat memoire des equipements, avec observateurs et delegation CRUD vers le service."""

    def __init__(
        self,
        *,
        manager: SQLiteFileManager | None = None,
        device_service: DeviceService | None = None,
    ) -> None:
        self._mgr = manager or SQLiteFileManager()
        self._device_service = device_service or DeviceService(self._mgr)
        self.type_definitions: Dict[str, dict] = {}
        self.device_data: Dict[str, Dict[str, Device]] = {}
        self.do_run: Dict[str, bool] = {}
        self.notify_flags: Dict[str, Dict[str, bool]] = {}
        self._observers: List[Callable[[], None]] = []

        self.refresh_type_definitions()
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
        self.type_definitions = self._device_service.list_type_definitions()

    def refresh_type_definitions(self) -> None:
        self._refresh_type_definitions()
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

    def _type_template(self, dtype: str) -> str:
        raw_icon = str(self.type_definitions.get(dtype, {}).get("icon", "")).strip().lower()
        if raw_icon in {"switch", "server"}:
            return raw_icon
        return "server" if dtype == "server" else "switch"

    def is_server_like_type(self, dtype: str) -> bool:
        return self._type_template(dtype) == "server"

    def is_config_download_type(self, dtype: str) -> bool:
        meta = self.type_definitions.get(dtype, {})
        config_backups_enabled = meta.get("config_backups_enabled", None)
        if config_backups_enabled is None:
            return self._type_template(dtype) == "switch"
        return bool(config_backups_enabled)

    @staticmethod
    def extract_custom_data(dev: Device) -> dict[str, str]:
        return DeviceService.extract_custom_data(dev)

    def print_global_device_data(self) -> None:
        for dtype, devices in self.device_data.items():
            log_with_timestamp(f"Type: {dtype}")
            for did, dev in devices.items():
                notif = "ON" if self.notify_flags.get(dtype, {}).get(did, False) else "OFF"
                if self.is_server_like_type(dtype):
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, "
                        f"Desc:{dev.description}, Type:{getattr(dev, 'type', '')}, "
                        f"TV:{getattr(dev, 'id_Teamviewer', '')}, "
                        f"Action:{getattr(dev, 'action_double_click', '')}, Notify:{notif}"
                    )
                else:
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, Desc:{dev.description}, Notify:{notif}"
                    )

    def read_devices(self) -> None:
        self.refresh_type_definitions()
        self.device_data, self.notify_flags = self._device_service.build_device_inventory(
            type_definitions=self.type_definitions
        )
        for dtype, meta in self.type_definitions.items():
            self.device_data.setdefault(dtype, {})
            self.notify_flags.setdefault(dtype, {})
            if bool(meta.get("monitoring_enabled", True)):
                self.do_run.setdefault(dtype, False)

    def update_json_file(self) -> None:
        self._device_service.write_devices_map(device_data=self.device_data, notify_flags=self.notify_flags)

    def list_devices(self, device_type: str | None = None) -> List[dict]:
        return self._device_service.list_devices(
            device_data=self.device_data,
            notify_flags=self.notify_flags,
            device_type=device_type,
        )

    def search_devices(self, query: str, device_type: str | None = None) -> List[dict]:
        return self._device_service.search_devices(
            device_data=self.device_data,
            notify_flags=self.notify_flags,
            query=query,
            device_type=device_type,
        )

    def _serialize_device_entry(self, device_type: str, device_id: str, dev: Device) -> dict:
        return self._device_service.serialize_device(
            device_type=device_type,
            device_id=device_id,
            device=dev,
            notify=self.notify_flags.get(device_type, {}).get(str(device_id), True),
        )

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
        try:
            result = self._device_service.create_device(
                type_definitions=self.type_definitions,
                existing_devices=self.device_data,
                device_type=device_type,
                name=name,
                ip=ip,
                description=description,
                id_Teamviewer=id_Teamviewer,
                device_subtype=device_subtype,
                action_double_click=action_double_click,
                web_url=web_url,
                ssh_user=ssh_user,
                custom_data=custom_data,
                notify=notify,
            )
        except ValueError as exc:
            if "Adresse IP deja utilisee" in str(exc):
                return None
            raise

        if result is None:
            return None

        if bool(self.type_definitions.get(device_type, {}).get("monitoring_enabled", False)):
            self.do_run.setdefault(device_type, False)
        self.device_data.setdefault(device_type, {})[result.device_id] = result.device
        self.notify_flags.setdefault(device_type, {})[result.device_id] = bool(notify)
        self._notify_observers()
        return result.device_id

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
        device_id = str(device_id)
        current_device = self.device_data.get(device_type, {}).get(device_id)
        if current_device is None:
            return False

        try:
            result = self._device_service.update_device(
                type_definitions=self.type_definitions,
                existing_devices=self.device_data,
                device_type=device_type,
                device_id=device_id,
                current_device=current_device,
                new_name=new_name,
                new_ip=new_ip,
                new_description=new_description,
                id_Teamviewer=id_Teamviewer,
                device_subtype=device_subtype,
                action_double_click=action_double_click,
                web_url=web_url,
                ssh_user=ssh_user,
                custom_data=custom_data,
                notify=notify if notify is not None else self.notify_flags.get(device_type, {}).get(device_id, True),
            )
        except ValueError:
            return False

        if result is None:
            return False

        self.device_data.setdefault(device_type, {})[device_id] = result.device
        if notify is not None:
            self.notify_flags.setdefault(device_type, {})[device_id] = bool(notify)
        self._notify_observers()
        return True

    def delete_device(self, device_type: str, device_id: str) -> bool:
        device_id = str(device_id)
        if device_id not in self.device_data.get(device_type, {}):
            return False
        if not self._device_service.delete_device(device_id=device_id):
            return False
        del self.device_data[device_type][device_id]
        self.notify_flags.setdefault(device_type, {}).pop(device_id, None)
        self._notify_observers()
        return True

    def reset_devices_status(self, device_type: Optional[str] = None) -> None:
        targets = [device_type] if device_type in self.do_run else list(self.device_data.keys())
        for dtype in targets:
            for dev in self.device_data.get(dtype, {}).values():
                dev.status = "idle"
        log_with_timestamp(f"reset_devices_status for {targets}")

    @staticmethod
    def generate_unique_id() -> str:
        return DeviceService.generate_unique_id()

    def build_status_snapshot(self) -> Dict[str, List[dict]]:
        snapshot: Dict[str, List[dict]] = {}
        for dtype, devices in self.device_data.items():
            entries: List[dict] = []
            for did, dev in devices.items():
                entries.append(
                    {
                        "id": str(did),
                        "type": str(dtype),
                        "name": str(getattr(dev, "name", "")),
                        "ip": str(getattr(dev, "ip", "")),
                        "description": str(getattr(dev, "description", "")),
                        "status": str(getattr(dev, "status", "idle")),
                        "notify": bool(self.notify_flags.get(dtype, {}).get(did, False)),
                        "subtype": str(getattr(dev, "type", "")),
                        "teamviewer_id": str(getattr(dev, "id_Teamviewer", "")),
                        "action_double_click": str(getattr(dev, "action_double_click", "")),
                        "web_url": str(getattr(dev, "web_url", "")),
                        "ssh_user": str(getattr(dev, "ssh_user", "")),
                    }
                )
            snapshot[dtype] = entries
        return snapshot
