from __future__ import annotations

import asyncio
import threading
import tkinter.messagebox as mb
from typing import Any, Dict, Protocol, Set, runtime_checkable

try:
    import aioping  # type: ignore
except ImportError:
    aioping = None  # mode dev hors réseau

from ..models.devices_model import DevicesModel
from ..utils.logger import log_with_timestamp
from ..utils.notifications import send_alert_email


@runtime_checkable
class _IView(Protocol):
    parent: Any

    def disable_start_button(self) -> None: ...
    def enable_start_button(self) -> None: ...
    def disable_stop_button(self) -> None: ...
    def enable_stop_button(self) -> None: ...
    def update_display(self) -> None: ...


class AppController:
    """Orchestre les tâches de monitoring réseau (ping + GUI), avec notifications."""

    def __init__(self, model: DevicesModel, view: _IView) -> None:
        self.model: DevicesModel = model
        self.model.add_observer(self._refresh_all_views)
        self.view: _IView = view
        self.views: Set[_IView] = {view}
        self.monitoring_tasks: Dict[str, threading.Thread] = {}

    def register_view(self, view: _IView) -> None:
        """Enregistre une vue pour qu’elle reçoive tous les refresh."""
        self.views.add(view)

    def _refresh_all_views(self) -> None:
        for v in list(self.views):
            try:
                v.update_display()
            except Exception:
                continue

    def _buttons_disable_start_enable_stop(self) -> None:
        for v in self.views:
            try:
                v.disable_start_button()
                v.enable_stop_button()
            except Exception:
                continue

    def _buttons_enable_start_disable_stop(self) -> None:
        for v in self.views:
            try:
                v.enable_start_button()
                v.disable_stop_button()
            except Exception:
                continue

    def start_monitoring(self, dtype: str) -> None:
        if not dtype:
            return
        self.model.do_run[dtype] = True

        if dtype in self.monitoring_tasks and self.monitoring_tasks[dtype].is_alive():
            return

        def task() -> None:
            asyncio.run(self._monitor_devices(dtype))

        t = threading.Thread(target=task, daemon=True, name=f"Mon-{dtype}")
        t.start()
        self.monitoring_tasks[dtype] = t

        log_with_timestamp(f"Monitoring démarré pour {dtype}")
        self._buttons_disable_start_enable_stop()
        self._refresh_all_views()

    def stop_monitoring(self, dtype: str) -> None:
        try:
            self.model.do_run[dtype] = False
            if dtype in self.monitoring_tasks:
                self.monitoring_tasks[dtype].join(timeout=5.0)

            # Remise à 'idle' après arrêt
            self.model.reset_devices_status(dtype)
            log_with_timestamp(f"Monitoring arrêté pour {dtype}")

            self._buttons_enable_start_disable_stop()
            self._refresh_all_views()
        except Exception as exc:
            log_with_timestamp(f"Erreur arrêt monitoring {dtype}: {exc}")

    def stop_all_monitoring(self) -> None:
        for dt in list(self.monitoring_tasks):
            self.stop_monitoring(dt)

    async def _monitor_devices(self, dtype: str) -> None:
        """
        Boucle de ping et mise à jour, avec détection et notification de changements.

        Args:
            dtype: Type d'appareil à monitorer ('server', 'switch', etc.).
        """
        while self.model.do_run.get(dtype, False):
            # Liste des objets Device
            devices = list(self.model.device_data.get(dtype, {}).values())

            # Sauvegarde des statuts précédents par device.id
            prev_statuses = {dev.id: dev.status for dev in devices}

            # Exécution des pings de manière asynchrone
            await asyncio.gather(*[self._check_device_status(dev) for dev in devices])

            # Détection des changements et notifications uniquement pour online/offline
            for dev in devices:
                old = prev_statuses.get(dev.id)
                new = dev.status
                # Notification seulement si transition online <-> offline
                if ((old == 'online' and new == 'offline') or (old == 'offline' and new == 'online')):
                    if self.model.notify_flags.get(dtype, {}).get(dev.id, False):
                        title = "Changement de statut"
                        msg = (
                            f"{dtype.capitalize()} « {dev.name} » "
                            f"est passé de {old} → {new}"
                        )
                        try:
                            self.view.parent.after(0, lambda t=title, m=msg: mb.showinfo(t, m))
                        except Exception:
                            try:
                                mb.showinfo(title, msg)
                            except Exception:
                                pass
                        try:
                            await asyncio.to_thread(send_alert_email, title, msg)
                        except Exception:
                            pass


            # Rafraîchissement thread-safe des vues
            for v in list(self.views):
                try:
                    v.parent.after(0, v.update_display)  # type: ignore[attr-defined]
                except Exception:
                    try:
                        v.update_display()
                    except Exception:
                        pass

            await asyncio.sleep(1)

    async def _check_device_status(self, device) -> str:
        """Ping l'appareil et met à jour son .status."""
        if aioping is None:
            device.status = "idle"
            return "idle"
        try:
            await aioping.ping(device.ip, timeout=2)
            device.status = "online"
        except Exception:
            device.status = "offline"
        return device.status
