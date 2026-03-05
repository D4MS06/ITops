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
from monitoring.storage.sqlite_manager import SQLiteFileManager
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
        self.online_recovery_delay_seconds: int = 5
        self.notification_cooldown_seconds: int = 120
        self.failures_for_offline: int = 3
        self.successes_for_online: int = 2
        self.ping_timeout_ms: int = 1500
        self.probe_interval_ms: int = 1000
        self.log_diagnostic_events: bool = False
        self._last_notification_sent_at: Dict[str, Dict[str, float]] = {}
        self.show_status_popup: bool = True
        self._use_aioping: bool = aioping is not None
        self._logs_store = SQLiteFileManager()

    def register_view(self, view: _IView) -> None:
        self.views.add(view)

    def unregister_view(self, view: _IView) -> None:
        self.views.discard(view)

    def set_offline_delay_seconds(self, seconds: int) -> None:
        self.offline_delay_seconds = max(1, int(seconds or 5))

    def set_online_recovery_delay_seconds(self, seconds: int) -> None:
        self.online_recovery_delay_seconds = max(1, int(seconds or 5))

    def set_notification_cooldown_seconds(self, seconds: int) -> None:
        self.notification_cooldown_seconds = max(0, int(seconds or 0))

    def set_failures_for_offline(self, count: int) -> None:
        self.failures_for_offline = max(1, int(count or 1))

    def set_successes_for_online(self, count: int) -> None:
        self.successes_for_online = max(1, int(count or 1))

    def set_ping_timeout_ms(self, timeout_ms: int) -> None:
        self.ping_timeout_ms = max(250, int(timeout_ms or 1500))

    def set_probe_interval_ms(self, interval_ms: int) -> None:
        self.probe_interval_ms = max(250, int(interval_ms or 1000))

    def set_log_diagnostic_events(self, enabled: bool) -> None:
        self.log_diagnostic_events = bool(enabled)

    def set_show_status_popup(self, enabled: bool) -> None:
        self.show_status_popup = bool(enabled)

    def _refresh_all_views(self) -> None:
        for v in list(self.views):
            if not self._view_is_alive(v):
                self.views.discard(v)
                continue
            try:
                self._schedule_ui_call(v, v.update_display)
            except Exception:
                self.views.discard(v)
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

    @staticmethod
    def _widget_exists(widget: Any) -> bool:
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False

    def _view_is_alive(self, view: _IView) -> bool:
        widget = self._ui_widget_for_view(view)
        if widget is None:
            return True
        return self._widget_exists(widget)

    def _schedule_ui_call(self, view: _IView, fn) -> None:
        widget = self._ui_widget_for_view(view)
        if widget is not None:
            if not self._widget_exists(widget):
                self.views.discard(view)
                return
            try:
                widget.after(0, fn)
            except Exception:
                self.views.discard(view)
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

    @staticmethod
    def _is_notifiable_status_transition(old_status: str | None, new_status: str | None) -> bool:
        old = str(old_status or "").strip().lower()
        new = str(new_status or "").strip().lower()
        return (old == "online" and new == "offline") or (old == "offline" and new == "online")

    async def _monitor_devices(self, dtype: str) -> None:
        """Boucle de ping et mise a jour, avec delai de passage hors ligne configurable."""
        failure_since: Dict[str, float] = {}
        success_since: Dict[str, float] = {}
        consecutive_failures: Dict[str, int] = {}
        consecutive_successes: Dict[str, int] = {}
        diagnostic_failure_logged: Dict[str, bool] = {}

        while self.model.do_run.get(dtype, False):
            devices = list(self.model.device_data.get(dtype, {}).values())
            prev_statuses = {dev.id: dev.status for dev in devices}

            checks = await asyncio.gather(*[self._is_device_reachable(dev) for dev in devices])

            known_ids = {str(dev.id) for dev in devices}
            for did in list(failure_since):
                if did not in known_ids:
                    failure_since.pop(did, None)
            for did in list(success_since):
                if did not in known_ids:
                    success_since.pop(did, None)
            for did in list(consecutive_failures):
                if did not in known_ids:
                    consecutive_failures.pop(did, None)
            for did in list(consecutive_successes):
                if did not in known_ids:
                    consecutive_successes.pop(did, None)
            for did in list(diagnostic_failure_logged):
                if did not in known_ids:
                    diagnostic_failure_logged.pop(did, None)
            for did in list(self._last_notification_sent_at.get(dtype, {})):
                if did not in known_ids:
                    self._last_notification_sent_at.get(dtype, {}).pop(did, None)

            delay = float(max(1, int(self.offline_delay_seconds or 5)))
            recovery_delay = float(max(1, int(self.online_recovery_delay_seconds or delay)))
            failures_needed = max(1, int(self.failures_for_offline or 1))
            successes_needed = max(1, int(self.successes_for_online or 1))
            now = time.monotonic()

            for dev, is_reachable in zip(devices, checks):
                dev_id = str(dev.id)
                old_status = prev_statuses.get(dev.id, "idle")

                if is_reachable is None:
                    dev.status = "idle"
                    failure_since.pop(dev_id, None)
                    success_since.pop(dev_id, None)
                    consecutive_failures.pop(dev_id, None)
                    consecutive_successes.pop(dev_id, None)
                    diagnostic_failure_logged.pop(dev_id, None)
                    continue

                if is_reachable:
                    failure_since.pop(dev_id, None)
                    consecutive_failures.pop(dev_id, None)
                    consecutive_successes[dev_id] = consecutive_successes.get(dev_id, 0) + 1

                    if diagnostic_failure_logged.get(dev_id, False) and old_status == "online":
                        if self.log_diagnostic_events:
                            try:
                                self._logs_store.record_status_log(
                                    dtype=str(dtype),
                                    device_id=dev_id,
                                    device_name=str(dev.name),
                                    old_status=str(old_status),
                                    new_status=str(old_status),
                                    event_kind="diagnostic_recovered",
                                    details=f"Retour stable apres {consecutive_successes[dev_id]} succes(s) consecutif(s)",
                                )
                            except Exception:
                                pass
                        diagnostic_failure_logged[dev_id] = False

                    if old_status == "offline":
                        start = success_since.get(dev_id)
                        if start is None:
                            success_since[dev_id] = now
                            dev.status = "offline"
                        elif (now - start) >= recovery_delay and consecutive_successes.get(dev_id, 0) >= successes_needed:
                            dev.status = "online"
                            success_since.pop(dev_id, None)
                        else:
                            dev.status = "offline"
                    else:
                        dev.status = "online"
                        success_since.pop(dev_id, None)
                    continue

                success_since.pop(dev_id, None)
                consecutive_successes.pop(dev_id, None)
                consecutive_failures[dev_id] = consecutive_failures.get(dev_id, 0) + 1
                start = failure_since.get(dev_id)
                if start is None:
                    failure_since[dev_id] = now
                    dev.status = "offline" if old_status == "offline" else old_status
                    continue

                if (
                    (now - start) >= delay
                    and consecutive_failures.get(dev_id, 0) >= failures_needed
                ):
                    dev.status = "offline"
                else:
                    dev.status = "offline" if old_status == "offline" else old_status

                if (
                    self.log_diagnostic_events
                    and old_status == "online"
                    and not diagnostic_failure_logged.get(dev_id, False)
                    and consecutive_failures.get(dev_id, 0) >= failures_needed
                ):
                    try:
                        self._logs_store.record_status_log(
                            dtype=str(dtype),
                            device_id=dev_id,
                            device_name=str(dev.name),
                            old_status=str(old_status),
                            new_status=str(old_status),
                            event_kind="diagnostic_failure_burst",
                            details=f"{consecutive_failures[dev_id]} echec(s) consecutif(s), attente bascule hors ligne",
                        )
                    except Exception:
                        pass
                    diagnostic_failure_logged[dev_id] = True

            for dev in devices:
                old = prev_statuses.get(dev.id)
                new = dev.status
                if self._is_notifiable_status_transition(old, new):
                    dev_id = str(dev.id)
                    diagnostic_failure_logged[dev_id] = False
                    try:
                        self._logs_store.record_status_log(
                            dtype=str(dtype),
                            device_id=dev_id,
                            device_name=str(dev.name),
                            old_status=str(old),
                            new_status=str(new),
                            event_kind="status_change",
                            details="",
                        )
                    except Exception:
                        pass
                    notify_enabled = self.model.notify_flags.get(dtype, {}).get(
                        dev_id, self.model.notify_flags.get(dtype, {}).get(dev.id, False)
                    )
                    if notify_enabled:
                        cooldown = float(max(0, int(self.notification_cooldown_seconds or 0)))
                        sent_for_type = self._last_notification_sent_at.setdefault(dtype, {})
                        last_sent = sent_for_type.get(dev_id)
                        if last_sent is not None and cooldown > 0 and (now - last_sent) < cooldown:
                            continue
                        sent_for_type[dev_id] = now
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

            await asyncio.sleep(max(0.25, float(self.probe_interval_ms) / 1000.0))

    @staticmethod
    def _ping_with_system_command(ip: str, timeout_seconds: float = 1.5) -> bool | None:
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
            args = [cmd, "-n", "1", "-w", str(max(250, int(timeout_seconds * 1000))), ip]
        else:
            args = ["ping", "-c", "1", "-W", str(max(1, int(timeout_seconds))), ip]
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
                timeout=max(3, int(timeout_seconds) + 1),
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
        timeout_seconds = max(0.25, float(self.ping_timeout_ms) / 1000.0)
        if self._use_aioping and aioping is not None:
            try:
                await aioping.ping(device.ip, timeout=timeout_seconds)
                return True
            except (PermissionError, OSError) as exc:
                self._use_aioping = False
                log_with_timestamp(
                    f"aioping indisponible ({exc}), bascule vers ping systeme.",
                    level="WARNING",
                )
            except Exception:
                pass
        return await asyncio.to_thread(self._ping_with_system_command, str(device.ip), timeout_seconds)
