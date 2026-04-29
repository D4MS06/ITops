from __future__ import annotations

import asyncio
import threading
import tkinter.messagebox as mb
from typing import Any, Dict, Protocol, Set, runtime_checkable

from monitoring.config.settings import NotificationSettings
from monitoring.services import monitoring_service as monitoring_runtime
from monitoring.models.device import Device
from monitoring.models.devices_model import DevicesModel
from monitoring.services.monitoring_runtime_service import MonitoringRuntimeService
from monitoring.services.monitoring_service import MonitoringEvent, MonitoringService
from monitoring.utils.logger import log_with_timestamp
from monitoring.utils.notifications import send_alert_email

aioping = monitoring_runtime.aioping


@runtime_checkable
class _IView(Protocol):
    parent: Any

    def disable_start_button(self) -> None: ...
    def enable_start_button(self) -> None: ...
    def disable_stop_button(self) -> None: ...
    def enable_stop_button(self) -> None: ...
    def update_display(self) -> None: ...


class AppController:
    """Adaptateur Tkinter pour le moteur de monitoring."""

    def __init__(
        self,
        model: DevicesModel,
        view: _IView | None = None,
        *,
        monitoring_service: MonitoringService | None = None,
        monitoring_runtime_service: MonitoringRuntimeService | None = None,
    ) -> None:
        self.model: DevicesModel = model
        self.model.add_observer(self._refresh_all_views)
        self.view: _IView | None = view
        self.views: Set[_IView] = set()
        if view is not None:
            self.views.add(view)
        self.monitoring_tasks: Dict[str, threading.Thread] = {}
        self.show_status_popup: bool = True
        self._monitoring_service = monitoring_service or MonitoringService(
            model,
            logs_store=getattr(model, "manager", None),
            notifier=lambda title, message: send_alert_email(title, message),
        )
        self._monitoring_runtime_service = monitoring_runtime_service
        self._logs_store = self._monitoring_service.logs_store

    def register_view(self, view: _IView) -> None:
        self.views.add(view)

    def unregister_view(self, view: _IView) -> None:
        self.views.discard(view)

    def set_offline_delay_seconds(self, seconds: int) -> None:
        self._monitoring_service.set_offline_delay_seconds(seconds)

    def set_online_recovery_delay_seconds(self, seconds: int) -> None:
        self._monitoring_service.set_online_recovery_delay_seconds(seconds)

    def set_notification_cooldown_seconds(self, seconds: int) -> None:
        self._monitoring_service.set_notification_cooldown_seconds(seconds)

    def set_failures_for_offline(self, count: int) -> None:
        self._monitoring_service.set_failures_for_offline(count)

    def set_successes_for_online(self, count: int) -> None:
        self._monitoring_service.set_successes_for_online(count)

    def set_ping_timeout_ms(self, timeout_ms: int) -> None:
        self._monitoring_service.set_ping_timeout_ms(timeout_ms)

    def set_probe_interval_ms(self, interval_ms: int) -> None:
        self._monitoring_service.set_probe_interval_ms(interval_ms)

    def set_log_diagnostic_events(self, enabled: bool) -> None:
        self._monitoring_service.set_log_diagnostic_events(enabled)

    def set_show_status_popup(self, enabled: bool) -> None:
        self.show_status_popup = bool(enabled)

    def apply_notification_settings(self, settings: NotificationSettings) -> None:
        self._monitoring_service.apply_notification_settings(settings)
        self.set_show_status_popup(settings.show_status_popup)

    def _refresh_all_views(self) -> None:
        for v in list(self.views):
            if not self._view_is_alive(v):
                self.views.discard(v)
                continue
            try:
                self._schedule_ui_call(v, v.update_display)
            except Exception as exc:
                log_with_timestamp(f"Vue retiree apres echec refresh: {exc}", level="DEBUG")
                self.views.discard(v)
                continue

    def refresh_views(self) -> None:
        self._refresh_all_views()

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
            except Exception as exc:
                log_with_timestamp(f"Planification UI impossible, vue retiree: {exc}", level="DEBUG")
                self.views.discard(view)
            return
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
        if self._monitoring_runtime_service is not None:
            if self._monitoring_runtime_service.start_monitoring(dtype):
                self._buttons_disable_start_enable_stop()
                self._refresh_all_views()
            return
        self._monitoring_service.start_monitoring(dtype)

        if dtype in self.monitoring_tasks and self.monitoring_tasks[dtype].is_alive():
            return

        def task() -> None:
            asyncio.run(self._monitor_devices(dtype))

        thread = threading.Thread(target=task, daemon=True, name=f"Mon-{dtype}")
        thread.start()
        self.monitoring_tasks[dtype] = thread

        log_with_timestamp(f"Monitoring demarre pour {dtype}")
        self._buttons_disable_start_enable_stop()
        self._refresh_all_views()

    def stop_monitoring(self, dtype: str) -> None:
        if self._monitoring_runtime_service is not None:
            if self._monitoring_runtime_service.stop_monitoring(dtype):
                self._buttons_enable_start_disable_stop()
                self._refresh_all_views()
            return
        try:
            self._monitoring_service.stop_monitoring(dtype)
            if dtype in self.monitoring_tasks:
                self.monitoring_tasks[dtype].join(timeout=5.0)

            self.model.reset_devices_status(dtype)
            log_with_timestamp(f"Monitoring arrete pour {dtype}")

            self._buttons_enable_start_disable_stop()
            self._refresh_all_views()
        except Exception as exc:
            log_with_timestamp(f"Erreur arret monitoring {dtype}: {exc}")

    def stop_all_monitoring(self) -> None:
        if self._monitoring_runtime_service is not None:
            self._monitoring_runtime_service.stop_all()
            self._buttons_enable_start_disable_stop()
            self._refresh_all_views()
            return
        for dt in list(self.monitoring_tasks):
            self.stop_monitoring(dt)

    def shutdown(self) -> None:
        self.stop_all_monitoring()
        self._monitoring_service.shutdown()

    @staticmethod
    def _is_notifiable_status_transition(old_status: str | None, new_status: str | None) -> bool:
        return MonitoringService.is_notifiable_status_transition(old_status, new_status)

    async def _monitor_devices(self, dtype: str) -> None:
        await self._monitoring_service.monitor_devices(
            dtype,
            reachability_checker=self._is_device_reachable,
            on_event=self._handle_monitoring_event,
            on_notification=self._handle_notification,
            on_cycle_complete=self._handle_monitoring_cycle,
        )

    async def _handle_monitoring_event(self, event: MonitoringEvent) -> None:
        if event.event_kind == "status_change":
            self.refresh_views()

    async def _handle_monitoring_cycle(self, dtype: str, has_status_change: bool) -> None:
        if has_status_change:
            self.refresh_views()

    async def _handle_notification(self, title: str, message: str, dtype: str, device: Device) -> None:
        if not self.show_status_popup:
            return
        try:
            target_view = self.view if self.view is not None else device
            widget = self._ui_widget_for_view(target_view) if self.view is not None else None
            if widget is not None:
                widget.after(0, lambda t=title, m=message: mb.showinfo(t, m))
            else:
                mb.showinfo(title, message)
        except Exception as exc:
            log_with_timestamp(f"Affichage popup differe impossible: {exc}", level="DEBUG")
            try:
                mb.showinfo(title, message)
            except Exception as fallback_exc:
                log_with_timestamp(f"Affichage popup impossible: {fallback_exc}", level="DEBUG")

    @staticmethod
    def _ping_with_system_command(ip: str, timeout_seconds: float = 1.5) -> bool | None:
        return MonitoringService.ping_with_system_command(ip, timeout_seconds)

    async def _is_device_reachable(self, device) -> bool | None:
        monitoring_runtime.aioping = aioping
        return await self._monitoring_service.is_device_reachable(device)
