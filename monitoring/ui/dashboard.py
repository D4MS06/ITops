# src/monitoring/ui/dashboard.py

from __future__ import annotations

import logging
from tkinter import Tk

from monitoring.config.settings import NotificationSettings
from monitoring.api.app import create_app
from monitoring.backend.app_backend import ApplicationBackend
from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.services.caddy_manager import CaddyManager
from monitoring.services.web_server_manager import WebServerManager
from monitoring.ui.base_window import BaseWindow
from monitoring.ui.dashboard_config_sync_mixin import DashboardConfigSyncMixin
from monitoring.ui.dashboard_lifecycle_mixin import DashboardLifecycleMixin
from monitoring.ui.dashboard_menu_actions_mixin import DashboardMenuActionsMixin
from monitoring.ui.dashboard_monitoring_mixin import DashboardMonitoringMixin
from monitoring.ui.dashboard_structure_mixin import DashboardStructureMixin
from monitoring.ui.dashboard_topbar_mixin import DashboardTopbarMixin
from monitoring.ui.dashboard_menu_mixin import DashboardMenuMixin
from monitoring.ui.dashboard_cards_mixin import DashboardCardsMixin
from monitoring.ui.dashboard_detail_mixin import DashboardDetailMixin
from monitoring.ui.dashboard_web_server_mixin import DashboardWebServerMixin
from monitoring.ui.dashboard_theme_mixin import DashboardThemeMixin
from monitoring.ui.dashboard_update_mixin import DashboardUpdateMixin
from monitoring.ui.dashboard_watermark_mixin import DashboardWatermarkMixin
from monitoring.ui.theme_manager import resolve_theme

try:
    from monitoring import __version__ as APP_VERSION
except Exception:
    try:
        from __init__ import __version__ as APP_VERSION
    except Exception:
        APP_VERSION = "unknown"


class DashboardIHM(
    DashboardLifecycleMixin,
    DashboardStructureMixin,
    DashboardMenuMixin,
    DashboardMenuActionsMixin,
    DashboardCardsMixin,
    DashboardDetailMixin,
    DashboardMonitoringMixin,
    DashboardTopbarMixin,
    DashboardConfigSyncMixin,
    DashboardWebServerMixin,
    DashboardThemeMixin,
    DashboardUpdateMixin,
    DashboardWatermarkMixin,
    BaseWindow,
):
    """Fenetre principale: dashboard tuiles + vues detaillees a la demande."""

    @staticmethod
    def _resolve_app_version() -> str:
        return APP_VERSION

    def _type_definitions_signature(self) -> tuple:
        normalized = []
        for code, meta in self.model.type_definitions.items():
            normalized.append(
                (
                    str(code).strip().lower(),
                    str(meta.get("label", "")).strip(),
                    bool(meta.get("monitoring_enabled", True)),
                    meta.get("config_backups_enabled", None),
                    int(meta.get("sort_order", 0) or 0),
                    str(meta.get("icon", "") or "").strip().lower(),
                )
            )
        normalized.sort(key=lambda x: (x[4], x[1].lower(), x[0]))
        return tuple(normalized)

    def _on_model_state_changed(self) -> None:
        try:
            if not bool(self.root.winfo_exists()):
                return
            new_signature = self._type_definitions_signature()
            if new_signature == self._last_type_signature:
                return
            self._last_type_signature = new_signature
            if self._type_rebuild_pending:
                return
            self._type_rebuild_pending = True
            self.root.after(0, self._apply_type_change_rebuild)
        except Exception as exc:
            self.logger.debug("Detection changement types ignoree: %s", exc)

    def _apply_type_change_rebuild(self) -> None:
        self._type_rebuild_pending = False
        try:
            if not bool(self.root.winfo_exists()):
                return
            self._rebuild_dynamic_sections()
        except Exception as exc:
            self.logger.debug("Rebuild apres changement types impossible: %s", exc)

    def __init__(
        self,
        root: Tk,
        *,
        model: DevicesModel,
        controller: AppController,
        backend: ApplicationBackend | None = None,
    ) -> None:
        self.app_version = self._resolve_app_version()
        super().__init__(root, title=f"Tableau de bord Monitoring v{self.app_version}")
        self.logger = logging.getLogger(__name__)

        self.model = model
        self.controller = controller
        self.backend = backend
        self.settings_service = (
            backend.settings_service
            if backend is not None
            else None
        )
        self.device_actions_service = (
            backend.device_actions_service
            if backend is not None
            else None
        )

        self.current_detail = "dashboard"
        self.active_tree_filter: tuple[str, str | None] | None = None
        self._type_rebuild_pending = False
        self.notification_settings: NotificationSettings = self._load_settings()
        self.config_storage = (
            backend.config_storage_service
            if backend is not None
            else self._build_config_storage_service()
        )
        self.caddy_manager = CaddyManager()
        self.web_server_manager = WebServerManager(
            app_factory=(
                lambda: create_app(backend=self.backend, stop_runtime_on_shutdown=False)
            ) if self.backend is not None else None
        )
        self.theme = resolve_theme(getattr(self.notification_settings, "ui_theme", "light"))
        self._apply_notification_settings_to_controller()

        self._build_ui()
        self.controller.register_view(self)
        self._last_type_signature = self._type_definitions_signature()
        self.model.add_observer(self._on_model_state_changed)
        self.center_window()

    def _ordered_type_codes(self) -> list[str]:
        items = list(self.model.type_definitions.items())
        items.sort(key=lambda kv: (int(kv[1].get("sort_order", 0) or 0), str(kv[1].get("label", kv[0])).lower()))
        return [str(code) for code, _meta in items]

    def _monitored_type_codes(self) -> list[str]:
        return [code for code in self._ordered_type_codes() if bool(self.model.type_definitions.get(code, {}).get("monitoring_enabled", True))]

    def _on_switch_select(self, _evt) -> None:
        return

    def _on_server_select(self, _evt) -> None:
        return








