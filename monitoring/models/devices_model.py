from __future__ import annotations

import uuid
from typing import Callable, Dict, List, Optional

from monitoring.models.device import Device
from monitoring.models.server import Server
from monitoring.models.switch import Switch
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.utils.exceptions import DeviceReadingError
from monitoring.utils.logger import log_with_timestamp


class DevicesModel:
    BASE_MONITORED_TYPES = ("switch", "server")
    """Stocke les équipements, notifie ses observateurs et gère un flag notify."""

    def __init__(self) -> None:
        # Dict[str, Dict[str, Device]]
        self.device_data: Dict[str, Dict[str, Device]] = {}
        # Indique si le monitoring tourne pour chaque type
        self.do_run: Dict[str, bool] = {dtype: False for dtype in self.BASE_MONITORED_TYPES}
        # Flag de notification par device_type puis device_id
        self.notify_flags: Dict[str, Dict[str, bool]] = {dtype: {} for dtype in self.BASE_MONITORED_TYPES}
        # Observers
        self._observers: List[Callable[[], None]] = []

        # Chargement initial depuis SQLite (avec migration auto depuis JSON si necessaire)
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
                    action = getattr(dev, "action_double_click", "")
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, "
                        f"Desc:{dev.description}, Type:{stype}, TV:{tv_id}, "
                        f"Action:{action}, {notif}"
                    )
                else:
                    log_with_timestamp(
                        f"  ID:{did}, Name:{dev.name}, IP:{dev.ip}, "
                        f"Desc:{dev.description}, {notif}"
                    )

    # ------------------------------------------------------------------ I/O data
    def read_devices(self) -> None:
        """Charge les equipements et leur flag notify depuis SQLite."""
        mgr = SQLiteFileManager()
        data = mgr.read_devices_map()
        if not isinstance(data, dict):
            raise DeviceReadingError("Format donnees inattendu.")

        for dtype, items in data.items():
            self.do_run.setdefault(dtype, False)
            self.device_data[dtype] = {}
            self.notify_flags[dtype] = {}
            for item in items:
                did = str(item["id"])
                if dtype == "server":
                    dev = Server(
                        ip=item["ip"],
                        name=item["name"],
                        description=item["description"],
                        id_Teamviewer=item.get("id_Teamviewer", ""),
                        subtype=item.get("type", ""),
                        action_double_click=item.get("action_double_click", ""),
                        web_url=item.get("web_url", ""),
                        ssh_user=item.get("ssh_user", ""),
                        device_id=did,
                    )
                elif dtype == "switch":
                    dev = Switch(
                        ip=item["ip"],
                        name=item["name"],
                        description=item["description"],
                        device_id=did,
                    )
                else:
                    dev = Device(
                        ip=item["ip"],
                        name=item["name"],
                        description=item["description"],
                        device_type=dtype,
                        device_id=did,
                    )
                self.device_data[dtype][did] = dev
                self.notify_flags[dtype][did] = item.get("notify", True)

    def update_json_file(self) -> None:
        """Compatibilite historique: persiste l'etat courant dans SQLite."""
        mgr = SQLiteFileManager()
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
                    entry["action_double_click"] = getattr(dev, "action_double_click", "")
                    entry["web_url"] = getattr(dev, "web_url", "")
                    entry["ssh_user"] = getattr(dev, "ssh_user", "")
                entries.append(entry)
            data[dtype] = entries
        mgr.write_devices_map(data)

    # ------------------------------------------------------------------ CRUD
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
        notify: bool = True,
    ) -> Optional[str]:
        """Ajoute un équipement. Retourne l'ID ou None si IP dupliquée."""
        for dev in self.device_data.get(device_type, {}).values():
            if dev.ip == ip:
                return None

        new_id = self.generate_unique_id()
        if device_type == "server":
            new_dev = Server(
                ip=ip,
                name=name,
                description=description,
                id_Teamviewer=id_Teamviewer or "",
                subtype=device_subtype or "",
                action_double_click=action_double_click or "",
                web_url=web_url or "",
                ssh_user=ssh_user or "",
                device_id=new_id,
            )
        else:
            new_dev = Switch(ip, name, description, device_id=new_id)

        new_dev.status = "idle"
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
        notify: Optional[bool] = None,
    ) -> bool:
        """Modifie un équipement existant et notifie les observateurs."""
        device_id = str(device_id)
        dev = self.device_data.get(device_type, {}).get(device_id)
        if not dev:
            return False

        dev.name = new_name
        dev.ip = new_ip
        dev.description = new_description
        if device_type == "server":
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

        if notify is not None:
            self.notify_flags[device_type][device_id] = notify

        self.update_json_file()
        self._notify_observers()
        return True

    def delete_device(self, device_type: str, device_id: str) -> bool:
        """Supprime un équipement et notifie les observateurs."""
        device_id = str(device_id)
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
            if device_type in self.do_run
            else list(self.device_data.keys())
        )
        for dtype in targets:
            for dev in self.device_data.get(dtype, {}).values():
                dev.status = "idle"
        log_with_timestamp(f"reset_devices_status pour {targets}")

    @staticmethod
    def generate_unique_id() -> str:
        return str(uuid.uuid4())

    def build_status_snapshot(self) -> Dict[str, List[dict]]:
        """Retourne un snapshot serialisable (JSON-ready) de tous les devices."""
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
                if dtype == "server":
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

