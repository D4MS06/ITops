from __future__ import annotations

from typing import TYPE_CHECKING

from monitoring.config.settings import NotificationSettings, load_settings, save_settings

if TYPE_CHECKING:
    from monitoring.ui.dashboard_contracts import DashboardMixinContract


class DashboardLifecycleMixin:
    def _build_config_storage_service(self: "DashboardMixinContract"):
        from monitoring.services.config_storage_service import ConfigStorageService

        return ConfigStorageService(settings_provider=self._load_settings)

    def _load_settings(self: "DashboardMixinContract") -> NotificationSettings:
        if self.settings_service is not None:
            return self.settings_service.get()
        return load_settings()

    def _save_settings(self: "DashboardMixinContract") -> NotificationSettings:
        if self.settings_service is not None:
            return self.settings_service.save(self.notification_settings)
        save_settings(self.notification_settings)
        return self.notification_settings

    def _build_ui(self: "DashboardMixinContract") -> None:
        self.root.geometry("1300x900")
        self.root.configure(bg=self.theme.colors["app_bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._create_menu()
        self._create_topbar()
        self._create_kpi_cards()
        self._create_monitoring_bar()
        self._create_detail_area()

        self._show_dashboard()
        self.update_display()
        self._apply_theme()
        self._maybe_sync_public_web_proxy()
        self._maybe_autostart_web_server()
        self.root.after(150, lambda: self._apply_window_chrome_theme(self.theme.key == "dark"))
        self.root.after(1800, self._check_updates_on_startup)
        self.root.after(2800, self._schedule_config_auto_sync)

    def _apply_notification_settings_to_controller(self: "DashboardMixinContract") -> None:
        self.controller.apply_notification_settings(self.notification_settings)

    def _on_closing(self: "DashboardMixinContract") -> None:
        try:
            self.controller.shutdown()
            self.web_server_manager.stop()
            self._stop_public_web_proxy_on_shutdown()
            if self.backend is not None:
                self.backend.monitoring_service.shutdown()
        finally:
            self.root.destroy()
