from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional

from monitoring.models.device import Device
from monitoring.models.device_inventory_state import DeviceInventoryState
from monitoring.services.device_service import DeviceService
from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.utils.logger import log_with_timestamp


class DevicesModel:
    """Etat memoire des equipements, avec observateurs et delegation CRUD vers le service."""

    def __init__(
        self,
        *,
        manager: MariaDBFileManager | None = None,
        device_service: DeviceService | None = None,
    ) -> None:
        self._mgr = manager or MariaDBFileManager()
        self._device_service = device_service or DeviceService(self._mgr)
        self._lock = threading.RLock()
        self._state = DeviceInventoryState()
        self._observers: List[Callable[[], None]] = []

        self.refresh_type_definitions()
        self.read_devices()
        log_with_timestamp("Inventaire devices charge", level="DEBUG")

    @property
    def manager(self) -> MariaDBFileManager:
        return self._mgr

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    @property
    def type_definitions(self) -> Dict[str, dict]:
        return self._state.type_definitions

    @type_definitions.setter
    def type_definitions(self, value: Dict[str, dict]) -> None:
        self._state.type_definitions = value

    @property
    def device_data(self) -> Dict[str, Dict[str, Device]]:
        return self._state.device_data

    @device_data.setter
    def device_data(self, value: Dict[str, Dict[str, Device]]) -> None:
        self._state.device_data = value

    @property
    def do_run(self) -> Dict[str, bool]:
        return self._state.do_run

    @do_run.setter
    def do_run(self, value: Dict[str, bool]) -> None:
        self._state.do_run = value

    @property
    def notify_flags(self) -> Dict[str, Dict[str, bool]]:
        return self._state.notify_flags

    @notify_flags.setter
    def notify_flags(self, value: Dict[str, Dict[str, bool]]) -> None:
        self._state.notify_flags = value

    def add_observer(self, callback: Callable[[], None]) -> None:
        with self._lock:
            self._observers.append(callback)

    def _notify_observers(self) -> None:
        with self._lock:
            callbacks = list(self._observers)
        for cb in callbacks:
            try:
                cb()
            except Exception as exc:
                log_with_timestamp(f"Observer DevicesModel en erreur: {exc}", level="WARNING")
                continue

    def notify_state_changed(self) -> None:
        self._notify_observers()

    def _refresh_type_definitions(self) -> None:
        self._state.sync_type_definitions(self._device_service.list_type_definitions())

    def refresh_type_definitions(self) -> None:
        with self._lock:
            self._refresh_type_definitions()

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
            log_with_timestamp(f"Type: {dtype}", level="DEBUG")
            for did, dev in devices.items():
                notif = "ON" if self.notify_flags.get(dtype, {}).get(did, False) else "OFF"
                if self.is_server_like_type(dtype):
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, "
                        f"Desc:{dev.description}, Type:{getattr(dev, 'type', '')}, "
                        f"TV:{getattr(dev, 'id_Teamviewer', '')}, "
                        f"Action:{getattr(dev, 'action_double_click', '')}, Notify:{notif}",
                        level="DEBUG",
                    )
                else:
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, Desc:{dev.description}, Notify:{notif}",
                        level="DEBUG",
                    )

    def read_devices(self) -> None:
        with self._lock:
            self._refresh_type_definitions()
            device_data, notify_flags = self._device_service.build_device_inventory(
                type_definitions=self.type_definitions
            )
            self._state.replace_inventory(
                type_definitions=self.type_definitions,
                device_data=device_data,
                notify_flags=notify_flags,
            )

    def update_json_file(self) -> None:
        with self._lock:
            self._device_service.write_devices_map(device_data=self.device_data, notify_flags=self.notify_flags)

    def set_notify_flag(self, device_type: str, device_id: str, enabled: bool) -> bool:
        normalized_device_type = str(device_type or "").strip()
        normalized_device_id = str(device_id or "").strip()
        if not normalized_device_type or not normalized_device_id:
            return False
        with self._lock:
            if self._state.device(normalized_device_type, normalized_device_id) is None:
                return False
            self._state.update_notify_flag(normalized_device_type, normalized_device_id, bool(enabled))
            self._device_service.write_devices_map(device_data=self.device_data, notify_flags=self.notify_flags)
        self._notify_observers()
        return True

    def list_devices(self, device_type: str | None = None) -> List[dict]:
        with self._lock:
            return self._device_service.list_devices(
                device_data=self.device_data,
                notify_flags=self.notify_flags,
                device_type=device_type,
            )

    def search_devices(self, query: str, device_type: str | None = None) -> List[dict]:
        with self._lock:
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
            notify=self._state.device_notify_flag(device_type, str(device_id)),
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
            with self._lock:
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

        with self._lock:
            self._state.remember_device(
                device_type=device_type,
                device_id=result.device_id,
                device=result.device,
                notify=bool(notify),
            )
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
        with self._lock:
            current_device = self._state.device(device_type, device_id)
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

            self._state.remember_device(
                device_type=device_type,
                device_id=device_id,
                device=result.device,
                notify=(notify if notify is not None else result.notify),
            )
            if notify is not None:
                self._state.update_notify_flag(device_type, device_id, bool(notify))
        self._notify_observers()
        return True

    def delete_device(self, device_type: str, device_id: str) -> bool:
        device_id = str(device_id)
        with self._lock:
            if self._state.device(device_type, device_id) is None:
                return False
            if not self._device_service.delete_device(device_id=device_id):
                return False
            self._state.forget_device(device_type, device_id)
        self._notify_observers()
        return True

    def reset_devices_status(self, device_type: Optional[str] = None) -> None:
        with self._lock:
            targets = self._state.reset_status(device_type)
        log_with_timestamp(f"reset_devices_status for {targets}", level="DEBUG")

    @staticmethod
    def generate_unique_id() -> str:
        return DeviceService.generate_unique_id()

    def build_status_snapshot(self) -> Dict[str, List[dict]]:
        with self._lock:
            return self._state.build_status_snapshot()
