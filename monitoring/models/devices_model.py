from __future__ import annotations

import uuid
from typing import Callable, Dict, List, Optional

from monitoring.storage.json_manager import JSONFileManager
from monitoring.utils.logger import log_with_timestamp
from monitoring.utils.exceptions import DeviceReadingError
from .device import Device
from .server import Server
from .switch import Switch


class DevicesModel:
    """Stocke les équipements, notifie ses observateurs et gère un flag notify."""

    def __init__(self) -> None:
        # Dict[str, Dict[str, Device]]
        self.device_data: Dict[str, Dict[str, Device]] = {}
        # Indique si le monitoring tourne pour chaque type
        self.do_run: Dict[str, bool] = {"switch": False, "server": False}
        # Flag de notification par device_type puis device_id
        self.notify_flags: Dict[str, Dict[str, bool]] = {"switch": {}, "server": {}}
        # Observers
        self._observers: List[Callable[[], None]] = []

        # Chargement initial depuis JSON
        self.read_devices()
        log_with_timestamp("Dictionnaire global après initialisation")
        self.print_global_device_data()

    # ------------------------------------------------------------------ Observers
    def add_observer(self, callback: Callable[[], None]) -> None:
        self._observers.append(callback)

    def _notify_observers(self) -> None:
        for cb in list(self._observers):
            try:
                cb()
            except Exception:
                continue

    # ------------------------------------------------------------------ Debug/log
    def print_global_device_data(self) -> None:
        for dtype, devices in self.device_data.items():
            log_with_timestamp(f"Type: {dtype}")
            for did, dev in devices.items():
                notif = "🔔 ON" if self.notify_flags[dtype].get(did, False) else "🔕 OFF"
                if dtype == "server":
                    stype = getattr(dev, "type", "Non spécifié")
                    tv_id = getattr(dev, "id_Teamviewer", "Non spécifié")
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, "
                        f"Desc:{dev.description}, Type:{stype}, TV:{tv_id}, {notif}"
                    )
                else:
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, "
                        f"Desc:{dev.description}, {notif}"
                    )

    # ------------------------------------------------------------------ I/O JSON
    def read_devices(self) -> None:
        """Charge les équipements et leur flag notify depuis le JSON."""
        mgr = JSONFileManager()
        data = mgr.read_json_file()
        if not isinstance(data, dict):
            raise DeviceReadingError("Format JSON inattendu.")

        for dtype, items in data.items():
            self.device_data[dtype] = {}
            self.notify_flags[dtype] = {}
            for item in items:
                did = item["id"]
                # Création de l’objet
                if dtype == "server":
                    dev = Server(
                        ip=item["ip"],
                        name=item["name"],
                        description=item["description"],
                        id_Teamviewer=item.get("id_Teamviewer", ""),
                        subtype=item.get("type", ""),
                        device_id=did,
                    )
                else:
                    dev = Switch(
                        ip=item["ip"],
                        name=item["name"],
                        description=item["description"],
                        device_id=did,
                    )
                self.device_data[dtype][did] = dev
                # notification flag, défaut True
                self.notify_flags[dtype][did] = item.get("notify", True)

    def update_json_file(self) -> None:
        """Écrit l’état courant et le flag notify dans le JSON."""
        mgr = JSONFileManager()
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
                if dtype == "server":
                    entry["id_Teamviewer"] = getattr(dev, "id_Teamviewer", "")
                    entry["type"] = getattr(dev, "type", "")
                entries.append(entry)
            data[dtype] = entries
        mgr.write_to_json_file(data)

    # ------------------------------------------------------------------ CRUD
    def add_device(
        self,
        device_type: str,
        name: str,
        ip: str,
        description: str,
        id_Teamviewer: Optional[str] = None,
        device_subtype: Optional[str] = None,
        notify: bool = True,
    ) -> Optional[str]:
        """Ajoute un équipement. Retourne l’ID ou None si IP dupliquée."""
        # unicité IP
        for dev in self.device_data.get(device_type, {}).values():
            if dev.ip == ip:
                return None

        new_id = self.generate_unique_id()
        if device_type == "server":
            new_dev = Server(ip, name, description, id_Teamviewer, device_subtype, device_id=new_id)
        else:
            new_dev = Switch(ip, name, description, device_id=new_id)

        new_dev.status = "idle"
        self.device_data.setdefault(device_type, {})[new_id] = new_dev
        # Flag notify initialisé d’après le formulaire
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
        notify: Optional[bool] = None,
    ) -> bool:
        """Modifie un équipement existant et notifie les observateurs."""
        dev = self.device_data.get(device_type, {}).get(device_id)
        if not dev:
            return False

        dev.name = new_name
        dev.ip = new_ip
        dev.description = new_description
        if device_type == "server":
            dev.id_Teamviewer = id_Teamviewer or dev.id_Teamviewer
            dev.type = device_subtype or dev.type

        # mise à jour du flag si fourni
        if notify is not None:
            self.notify_flags[device_type][device_id] = notify

        self.update_json_file()
        self._notify_observers()
        return True

    def delete_device(self, device_type: str, device_id: str) -> bool:
        """Supprime un équipement et notifie les observateurs."""
        if device_id in self.device_data.get(device_type, {}):
            del self.device_data[device_type][device_id]
            self.notify_flags[device_type].pop(device_id, None)
            self.update_json_file()
            self._notify_observers()
            return True
        return False

    # ------------------------------------------------------------------ Utilities
    def reset_devices_status(self, device_type: Optional[str] = None) -> None:
        targets = (
            [device_type]
            if device_type in {"switch", "server"}
            else list(self.device_data.keys())
        )
        for dtype in targets:
            for dev in self.device_data.get(dtype, {}).values():
                dev.status = "idle"
        log_with_timestamp(f"reset_devices_status pour {targets}")

    @staticmethod
    def generate_unique_id() -> str:
        return str(uuid.uuid4())
