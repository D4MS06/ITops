from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional

try:
    import aioping  # type: ignore
except ImportError:
    aioping = None

from monitoring.models.device import Device
from monitoring.models.devices_model import DevicesModel
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.utils.logger import log_with_timestamp
from monitoring.utils.notifications import send_alert_email


@dataclass
class MonitoringEvent:
    dtype: str
    device: Device
    old_status: str
    new_status: str
    event_kind: str
    details: str = ""


class MonitoringService:
    """Moteur de supervision independant de Tkinter."""

    def __init__(
        self,
        model: DevicesModel,
        *,
        logs_store: SQLiteFileManager | None = None,
        notifier: Callable[[str, str], None] | None = None,
    ) -> None:
        self.model = model
        self.offline_delay_seconds: int = 5
        self.online_recovery_delay_seconds: int = 5
        self.notification_cooldown_seconds: int = 120
        self.failures_for_offline: int = 3
        self.successes_for_online: int = 2
        self.ping_timeout_ms: int = 1500
        self.probe_interval_ms: int = 1000
        self.log_diagnostic_events: bool = False
        self._last_notification_sent_at: Dict[str, Dict[str, float]] = {}
        self._use_aioping: bool = aioping is not None and not platform.system().lower().startswith("win")
        self._logs_store = logs_store or SQLiteFileManager()
        self._notifier = notifier or send_alert_email
        self._clock = time.monotonic
        self._ping_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(16, min(128, (os.cpu_count() or 4) * 8)),
            thread_name_prefix="PingProbe",
        )

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

    def start_monitoring(self, dtype: str) -> None:
        if dtype:
            with self.model.lock:
                self.model.do_run[dtype] = True

    def stop_monitoring(self, dtype: str) -> None:
        if dtype:
            with self.model.lock:
                self.model.do_run[dtype] = False

    @staticmethod
    def is_notifiable_status_transition(old_status: str | None, new_status: str | None) -> bool:
        old = str(old_status or "").strip().lower()
        new = str(new_status or "").strip().lower()
        return (old == "online" and new == "offline") or (old == "offline" and new == "online")

    async def monitor_devices(
        self,
        dtype: str,
        *,
        reachability_checker: Optional[Callable[[Device], Awaitable[bool | None]]] = None,
        on_event: Optional[Callable[[MonitoringEvent], object]] = None,
        on_notification: Optional[Callable[[str, str, str, Device], object]] = None,
        on_cycle_complete: Optional[Callable[[str, bool], object]] = None,
    ) -> None:
        failure_since: Dict[str, float] = {}
        success_since: Dict[str, float] = {}
        consecutive_failures: Dict[str, int] = {}
        consecutive_successes: Dict[str, int] = {}
        diagnostic_failure_logged: Dict[str, bool] = {}
        checker = reachability_checker or self.is_device_reachable

        while True:
            with self.model.lock:
                if not self.model.do_run.get(dtype, False):
                    break
                devices = list(self.model.device_data.get(dtype, {}).values())
                prev_statuses = {dev.id: dev.status for dev in devices}
            checks = await asyncio.gather(*[checker(dev) for dev in devices])

            known_ids = {str(dev.id) for dev in devices}
            self._prune_tracking_maps(
                dtype=dtype,
                known_ids=known_ids,
                failure_since=failure_since,
                success_since=success_since,
                consecutive_failures=consecutive_failures,
                consecutive_successes=consecutive_successes,
                diagnostic_failure_logged=diagnostic_failure_logged,
            )

            delay = float(max(1, int(self.offline_delay_seconds or 5)))
            recovery_delay = float(max(1, int(self.online_recovery_delay_seconds or delay)))
            failures_needed = max(1, int(self.failures_for_offline or 1))
            successes_needed = max(1, int(self.successes_for_online or 1))
            now = self._clock()

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
                            await self._record_event(
                                MonitoringEvent(
                                    dtype=str(dtype),
                                    device=dev,
                                    old_status=str(old_status),
                                    new_status=str(old_status),
                                    event_kind="diagnostic_recovered",
                                    details=f"Retour stable apres {consecutive_successes[dev_id]} succes(s) consecutif(s)",
                                ),
                                on_event=on_event,
                            )
                        diagnostic_failure_logged[dev_id] = False

                    if old_status == "online":
                        dev.status = "online"
                        success_since.pop(dev_id, None)
                    elif old_status == "offline":
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
                        if consecutive_successes.get(dev_id, 0) >= successes_needed:
                            dev.status = "online"
                            success_since.pop(dev_id, None)
                        else:
                            success_since.setdefault(dev_id, now)
                            dev.status = old_status if old_status not in {"", "online"} else "idle"
                    continue

                success_since.pop(dev_id, None)
                consecutive_successes.pop(dev_id, None)
                consecutive_failures[dev_id] = consecutive_failures.get(dev_id, 0) + 1
                start = failure_since.get(dev_id)
                if start is None:
                    failure_since[dev_id] = now
                    dev.status = "offline" if old_status == "offline" else old_status
                    continue

                if (now - start) >= delay and consecutive_failures.get(dev_id, 0) >= failures_needed:
                    dev.status = "offline"
                else:
                    dev.status = "offline" if old_status == "offline" else old_status

                if (
                    self.log_diagnostic_events
                    and old_status == "online"
                    and not diagnostic_failure_logged.get(dev_id, False)
                    and consecutive_failures.get(dev_id, 0) >= failures_needed
                ):
                    await self._record_event(
                        MonitoringEvent(
                            dtype=str(dtype),
                            device=dev,
                            old_status=str(old_status),
                            new_status=str(old_status),
                            event_kind="diagnostic_failure_burst",
                            details=f"{consecutive_failures[dev_id]} echec(s) consecutif(s), attente bascule hors ligne",
                        ),
                        on_event=on_event,
                    )
                    diagnostic_failure_logged[dev_id] = True

            has_status_change = any(prev_statuses.get(dev.id) != dev.status for dev in devices)
            for dev in devices:
                old = prev_statuses.get(dev.id)
                new = dev.status
                if not self.is_notifiable_status_transition(old, new):
                    continue
                diagnostic_failure_logged[str(dev.id)] = False
                event = MonitoringEvent(
                    dtype=str(dtype),
                    device=dev,
                    old_status=str(old),
                    new_status=str(new),
                    event_kind="status_change",
                    details="",
                )
                await self._record_event(event, on_event=on_event)
                with self.model.lock:
                    notify_enabled = self.model.notify_flags.get(dtype, {}).get(str(dev.id), False)
                if not notify_enabled:
                    continue
                if not self._should_send_notification(dtype=dtype, device_id=str(dev.id), now=now):
                    continue
                title = "Changement de statut"
                message = f'{dtype.capitalize()} "{dev.name}" est passe de {old} -> {new}'
                await self._emit_notification(
                    title=title,
                    message=message,
                    dtype=str(dtype),
                    device=dev,
                    on_notification=on_notification,
                )

            if on_cycle_complete is not None:
                await self._maybe_await(on_cycle_complete(str(dtype), has_status_change))
            await asyncio.sleep(max(0.25, float(self.probe_interval_ms) / 1000.0))

    def _prune_tracking_maps(
        self,
        *,
        dtype: str,
        known_ids: set[str],
        failure_since: Dict[str, float],
        success_since: Dict[str, float],
        consecutive_failures: Dict[str, int],
        consecutive_successes: Dict[str, int],
        diagnostic_failure_logged: Dict[str, bool],
    ) -> None:
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

    def _should_send_notification(self, *, dtype: str, device_id: str, now: float) -> bool:
        cooldown = float(max(0, int(self.notification_cooldown_seconds or 0)))
        sent_for_type = self._last_notification_sent_at.setdefault(dtype, {})
        last_sent = sent_for_type.get(device_id)
        if last_sent is not None and cooldown > 0 and (now - last_sent) < cooldown:
            return False
        sent_for_type[device_id] = now
        return True

    async def _record_event(
        self,
        event: MonitoringEvent,
        *,
        on_event: Optional[Callable[[MonitoringEvent], object]],
    ) -> None:
        try:
            self._logs_store.record_status_log(
                dtype=event.dtype,
                device_id=str(event.device.id),
                device_name=str(event.device.name),
                old_status=event.old_status,
                new_status=event.new_status,
                event_kind=event.event_kind,
                details=event.details,
            )
        except Exception:
            pass
        if on_event is not None:
            await self._maybe_await(on_event(event))

    async def _emit_notification(
        self,
        *,
        title: str,
        message: str,
        dtype: str,
        device: Device,
        on_notification: Optional[Callable[[str, str, str, Device], object]],
    ) -> None:
        if on_notification is not None:
            await self._maybe_await(on_notification(title, message, dtype, device))
        try:
            await asyncio.to_thread(self._notifier, title, message)
        except Exception:
            pass

    @staticmethod
    async def _maybe_await(result: object) -> None:
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def ping_with_system_command(ip: str, timeout_seconds: float = 1.5) -> bool | None:
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
            startup_info.wShowWindow = 0
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

    async def is_device_reachable(self, device: Device) -> bool | None:
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
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._ping_executor,
            self.ping_with_system_command,
            str(device.ip),
            timeout_seconds,
        )
