from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass

from monitoring.models.devices_model import DevicesModel
from monitoring.services.monitoring_service import MonitoringService
from monitoring.utils.logger import log_with_timestamp


@dataclass(frozen=True)
class MonitoringRuntimeState:
    running_types: list[str]
    monitored_types: list[str]
    running_any: bool
    running_all: bool


class MonitoringRuntimeService:
    """Orchestration de supervision hors Tkinter pour mode serveur/API."""

    def __init__(
        self,
        model: DevicesModel,
        monitoring_service: MonitoringService,
    ) -> None:
        self.model = model
        self.monitoring_service = monitoring_service
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._state_condition = threading.Condition(self._lock)
        self._state_version = 0
        self.model.add_observer(self._handle_model_state_changed)

    def _handle_model_state_changed(self) -> None:
        with self._state_condition:
            self._state_version += 1
            self._state_condition.notify_all()

    def monitored_types(self) -> list[str]:
        with self.model.lock:
            return [
                str(dtype)
                for dtype, meta in self.model.type_definitions.items()
                if bool(meta.get("monitoring_enabled", True))
            ]

    def running_types(self) -> list[str]:
        with self.model.lock:
            monitored = self.monitored_types()
            return [dtype for dtype in monitored if bool(self.model.do_run.get(dtype, False))]

    def state(self) -> MonitoringRuntimeState:
        monitored = self.monitored_types()
        running = self.running_types()
        return MonitoringRuntimeState(
            running_types=running,
            monitored_types=monitored,
            running_any=bool(running),
            running_all=bool(monitored) and len(running) == len(monitored),
        )

    def start_monitoring(self, dtype: str) -> bool:
        normalized = str(dtype or "").strip().lower()
        if normalized not in self.monitored_types():
            return False

        self.monitoring_service.start_monitoring(normalized)
        with self._lock:
            thread = self._threads.get(normalized)
            if thread is not None and thread.is_alive():
                return True

            def _task() -> None:
                asyncio.run(
                    self.monitoring_service.monitor_devices(
                        normalized,
                        on_cycle_complete=self._handle_monitoring_cycle,
                    )
                )

            thread = threading.Thread(target=_task, daemon=True, name=f"ApiMon-{normalized}")
            thread.start()
            self._threads[normalized] = thread

        log_with_timestamp(f"Monitoring runtime demarre pour {normalized}")
        self.model.notify_state_changed()
        return True

    def stop_monitoring(self, dtype: str) -> bool:
        normalized = str(dtype or "").strip().lower()
        if normalized not in self.monitored_types():
            return False

        self.monitoring_service.stop_monitoring(normalized)
        with self._lock:
            thread = self._threads.get(normalized)
        if thread is not None:
            thread.join(timeout=5.0)
        self.model.reset_devices_status(normalized)
        log_with_timestamp(f"Monitoring runtime arrete pour {normalized}")
        self.model.notify_state_changed()
        return True

    async def _handle_monitoring_cycle(self, _dtype: str, has_status_change: bool) -> None:
        if has_status_change:
            self.model.notify_state_changed()

    def state_version(self) -> int:
        with self._state_condition:
            return self._state_version

    def wait_for_change(self, last_version: int, timeout_seconds: float) -> int:
        timeout = max(0.1, float(timeout_seconds))
        with self._state_condition:
            if self._state_version != last_version:
                return self._state_version
            self._state_condition.wait(timeout=timeout)
            return self._state_version

    def start_all(self) -> list[str]:
        started: list[str] = []
        for dtype in self.monitored_types():
            if self.start_monitoring(dtype):
                started.append(dtype)
        return started

    def stop_all(self) -> list[str]:
        stopped: list[str] = []
        for dtype in list(self.monitored_types()):
            if self.stop_monitoring(dtype):
                stopped.append(dtype)
        return stopped
