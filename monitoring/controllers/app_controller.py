from __future__ import annotations

import asyncio
import os
import platform
import shutil
import subprocess
import threading
import time
import tkinter.messagebox as mb
from typing import Any, Dict, Protocol, Set, runtime_checkable

try:
    import aioping  # type: ignore
except ImportError:
    aioping = None  # mode dev hors reseau

from monitoring.models.devices_model import DevicesModel
from monitoring.utils.logger import log_with_timestamp
from monitoring.utils.notifications import send_alert_email


@runtime_checkable
class _IView(Protocol):
    parent: Any

    def disable_start_button(self) -> None: ...
    def enable_start_button(self) -> None: ...
    def disable_stop_button(self) -> None: ...
    def enable_stop_button(self) -> None: ...
    def update_display(self) -> None: ...


class AppController:
    """Orchestre les taches de monitoring reseau (ping + GUI), avec notifications."""

    def __init__(self, model: DevicesModel, view: _IView | None = None) -> None:
        self.model: DevicesModel = model
        self.model.add_observer(self._refresh_all_views)
        self.view: _IView | None = view
        self.views: Set[_IView] = set()
        if view is not None:
            self.views.add(view)
        self.monitoring_tasks: Dict[str, threading.Thread] = {}
        self.offline_delay_seconds: int = 5
        self.show_status_popup: bool = True
        self._use_aioping: bool = aioping is not None

    def register_view(self, view: _IView) -> None:
        self.views.add(view)

    def set_offline_delay_seconds(self, seconds: int) -> None:
        self.offline_delay_seconds = max(1, int(seconds or 5))

    def set_show_status_popup(self, enabled: bool) -> None:
        self.show_status_popup = bool(enabled)

    def _refresh_all_views(self) -> None:
        for v in list(self.views):
            try:
                self._schedule_ui_call(v, v.update_display)
            except Exception:
                continue

    @staticmethod
    def _ui_widget_for_view(view: _IView):
        widget = getattr(view, "parent", None)
        if widget is not None and hasattr(widget, "after"):
            return widget
        widget = getattr(view, "root", None)
        if widget is not None and hasattr(widget, "after"):
            return widget
        return None

    def _schedule_ui_call(self, view: _IView, fn) -> None:
        widget = self._ui_widget_for_view(view)
        if widget is not None:
            widget.after(0, fn)
            return
        # Dernier recours si aucune racine UI n'est accessible.
        fn()

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

        log_with_timestamp(f"Monitoring demarre pour {dtype}")
        self._buttons_disable_start_enable_stop()
        self._refresh_all_views()

    def stop_monitoring(self, dtype: str) -> None:
        try:
            self.model.do_run[dtype] = False
            if dtype in self.monitoring_tasks:
                self.monitoring_tasks[dtype].join(timeout=5.0)

            self.model.reset_devices_status(dtype)
            log_with_timestamp(f"Monitoring arrete pour {dtype}")

            self._buttons_enable_start_disable_stop()
            self._refresh_all_views()
        except Exception as exc:
            log_with_timestamp(f"Erreur arret monitoring {dtype}: {exc}")

    def stop_all_monitoring(self) -> None:
        for dt in list(self.monitoring_tasks):
            self.stop_monitoring(dt)

    async def _monitor_devices(self, dtype: str) -> None:
        """Boucle de ping et mise a jour, avec delai de passage hors ligne configurable."""
        failure_since: Dict[str, float] = {}

        while self.model.do_run.get(dtype, False):
            devices = list(self.model.device_data.get(dtype, {}).values())
            prev_statuses = {dev.id: dev.status for dev in devices}

            checks = await asyncio.gather(*[self._is_device_reachable(dev) for dev in devices])

            known_ids = {str(dev.id) for dev in devices}
            for did in list(failure_since):
                if did not in known_ids:
                    failure_since.pop(did, None)

            delay = float(max(1, int(self.offline_delay_seconds or 5)))
            now = time.monotonic()

            for dev, is_reachable in zip(devices, checks):
                dev_id = str(dev.id)
                old_status = prev_statuses.get(dev.id, "idle")

                if is_reachable is None:
                    dev.status = "idle"
                    failure_since.pop(dev_id, None)
                    continue

                if is_reachable:
                    dev.status = "online"
                    failure_since.pop(dev_id, None)
                    continue

                start = failure_since.get(dev_id)
                if start is None:
                    failure_since[dev_id] = now
                    dev.status = "offline" if old_status == "offline" else old_status
                    continue

                if (now - start) >= delay:
                    dev.status = "offline"
                else:
                    dev.status = "offline" if old_status == "offline" else old_status

            for dev in devices:
                old = prev_statuses.get(dev.id)
                new = dev.status
                if ((old == "online" and new == "offline") or (old == "offline" and new == "online")):
                    if self.model.notify_flags.get(dtype, {}).get(dev.id, False):
                        title = "Changement de statut"
                        msg = f'{dtype.capitalize()} "{dev.name}" est passe de {old} -> {new}'
                        if self.show_status_popup:
                            try:
                                target_view = self.view if self.view is not None else dev
                                widget = self._ui_widget_for_view(target_view) if self.view is not None else None
                                if widget is not None:
                                    widget.after(0, lambda t=title, m=msg: mb.showinfo(t, m))
                                else:
                                    mb.showinfo(title, msg)
                            except Exception:
                                try:
                                    mb.showinfo(title, msg)
                                except Exception:
                                    pass
                        try:
                            await asyncio.to_thread(send_alert_email, title, msg)
                        except Exception:
                            pass

            has_status_change = any(prev_statuses.get(dev.id) != dev.status for dev in devices)
            if has_status_change:
                for v in list(self.views):
                    try:
                        self._schedule_ui_call(v, v.update_display)
                    except Exception:
                        try:
                            self._schedule_ui_call(v, v.update_display)
                        except Exception:
                            pass

            await asyncio.sleep(1)

    @staticmethod
    def _ping_with_system_command(ip: str, timeout_seconds: int = 2) -> bool | None:
        system = platform.system().lower()
        is_win = system.startswith("win")
        if is_win:
            system_root = os.environ.get("SystemRoot", r"C:\Windows")
            cmd = None
            for candidate in (
                os.path.join(system_root, "System32", "ping.exe"),
                os.path.join(system_root, "Sysnative", "ping.exe"),
            ):
                if os.path.isfile(candidate):
                    cmd = candidate
                    break
            if not cmd:
                cmd = shutil.which("ping") or "ping"
            args = [cmd, "-n", "1", "-w", str(int(timeout_seconds * 1000)), ip]
        else:
            args = ["ping", "-c", "1", "-W", str(timeout_seconds), ip]
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if is_win else 0
        startup_info = None
        if is_win:
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = 0  # SW_HIDE
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=False,
                timeout=max(3, timeout_seconds + 1),
                check=False,
                creationflags=creation_flags,
                startupinfo=startup_info,
            )
            return proc.returncode == 0
        except FileNotFoundError:
            log_with_timestamp(f"Commande ping introuvable pour l'IP {ip}", level="ERROR")
            return None
        except Exception as exc:
            log_with_timestamp(f"Erreur ping systeme ({ip}): {exc}", level="ERROR")
            return False

    async def _is_device_reachable(self, device) -> bool | None:
        """Retourne True/False selon le ping; fallback ping systeme si aioping indisponible."""
        if self._use_aioping and aioping is not None:
            try:
                await aioping.ping(device.ip, timeout=2)
                return True
            except (PermissionError, OSError) as exc:
                self._use_aioping = False
                log_with_timestamp(
                    f"aioping indisponible ({exc}), bascule vers ping systeme.",
                    level="WARNING",
                )
            except Exception:
                pass
        return await asyncio.to_thread(self._ping_with_system_command, str(device.ip), 2)
