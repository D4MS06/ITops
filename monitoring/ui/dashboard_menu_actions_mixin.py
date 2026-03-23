from __future__ import annotations

from tkinter import messagebox

from monitoring.ui.dialogs.device_types_settings import DeviceTypesSettingsDialog


class DashboardMenuActionsMixin:
    def _supervision_menu_items(self) -> list[tuple[str, object]]:
        return [
            ("Notifications (email + popup)...", self._open_notification_dialog),
            ("Parametres de monitoring...", self._open_monitoring_dialog),
            (
                "Serveur web",
                [
                    ("Parametres...", self._open_web_server_dialog),
                    ("Exporter le certificat HTTPS...", self._export_https_root_certificate),
                ],
            ),
            ("Journaux", self._logs_menu_items()),
            ("Mises a jour...", self._open_update_settings_dialog),
        ]

    def _inventory_menu_items(self) -> list[tuple[str, object]]:
        can_open_backup = bool(self._can_open_switch_configs_root())
        return [
            ("Types d'equipements...", self._open_device_types_settings),
            (
                "Fichiers de configuration",
                [
                    ("Ouvrir dossier de configuration", self._open_local_config_root),
                    ("Ouvrir dossier de sauvegarde", self._open_switch_configs_root if can_open_backup else None),
                    ("Configurer sauvegarde...", self._open_config_storage_settings_dialog),
                    ("Sauvegarder maintenant", self._run_config_sync_now_interactive),
                ],
            ),
        ]

    def _display_menu_items(self) -> list[tuple[str, object]]:
        return [
            (
                "Theme",
                [
                    ("Clair", lambda: self._set_theme_from_menu("light")),
                    ("Sombre", lambda: self._set_theme_from_menu("dark")),
                ],
            ),
            (
                "Indicateurs de statut",
                [
                    ("Badge coche / croix", lambda: self._set_status_indicator_style_from_menu("badge")),
                    ("Pastille moderne", lambda: self._set_status_indicator_style_from_menu("dot")),
                ],
            ),
            ("Image de fond...", self._open_watermark_dialog),
        ]

    def _logs_menu_items(self) -> list[tuple[str, object]]:
        items: list[tuple[str, object]] = [
            ("Logs techniques...", self._open_technical_logs),
            ("Journal global des changements...", self._open_global_status_logs),
        ]
        for dtype in self._ordered_type_codes():
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            items.append((f"Journal {label}...", lambda dt=dtype: self._open_status_logs_by_type(dt)))
        return items

    def _help_menu_items(self) -> list[tuple[str, object]]:
        return [("A propos...", self._open_about_dialog)]

    def _open_device_types_settings(self) -> None:
        DeviceTypesSettingsDialog(self.root, on_changed=self._on_device_types_changed)

    def _on_device_types_changed(self) -> None:
        try:
            self.model.refresh_type_definitions()
            self.model.notify_state_changed()
            self._rebuild_dynamic_sections()
            self.controller.refresh_views()
        except Exception:
            self.logger.exception("Erreur rafraichissement types de devices")

    def _open_notification_dialog(self) -> None:
        from monitoring.ui.dialogs.notification_settings import NotificationSettingsDialog

        dlg = NotificationSettingsDialog(self.root, self.notification_settings)
        if dlg.result:
            self.notification_settings = dlg.result
            self._save_settings()
            self.controller.apply_notification_settings(self.notification_settings)

    def _open_monitoring_dialog(self) -> None:
        from monitoring.ui.dialogs.monitoring_settings import MonitoringSettingsDialog

        dlg = MonitoringSettingsDialog(
            self.root,
            self.notification_settings.offline_delay_seconds,
            self.notification_settings.online_recovery_delay_seconds,
            self.notification_settings.notification_cooldown_seconds,
            self.notification_settings.failures_for_offline,
            self.notification_settings.successes_for_online,
            self.notification_settings.ping_timeout_ms,
            self.notification_settings.probe_interval_ms,
            self.notification_settings.log_diagnostic_events,
        )
        if dlg.result is None:
            return
        self.notification_settings.offline_delay_seconds = max(
            1, int(dlg.result["offline_delay_seconds"])
        )
        self.notification_settings.online_recovery_delay_seconds = max(
            1, int(dlg.result["online_recovery_delay_seconds"])
        )
        self.notification_settings.notification_cooldown_seconds = max(
            0, int(dlg.result["notification_cooldown_seconds"])
        )
        self.notification_settings.failures_for_offline = max(
            1, int(dlg.result["failures_for_offline"])
        )
        self.notification_settings.successes_for_online = max(
            1, int(dlg.result["successes_for_online"])
        )
        self.notification_settings.ping_timeout_ms = max(250, int(dlg.result["ping_timeout_ms"]))
        self.notification_settings.probe_interval_ms = max(250, int(dlg.result["probe_interval_ms"]))
        self.notification_settings.log_diagnostic_events = bool(dlg.result["log_diagnostic_events"])
        self._save_settings()
        self.controller.apply_notification_settings(self.notification_settings)

    def _open_global_status_logs(self) -> None:
        from monitoring.ui.dialogs.status_logs_viewer import StatusLogsViewer

        StatusLogsViewer(
            self.root,
            title="Journal global des changements de statut",
            manager=self.model.manager,
        )

    def _open_technical_logs(self) -> None:
        from monitoring.ui.dialogs.technical_logs_viewer import TechnicalLogsViewer

        TechnicalLogsViewer(self.root)

    def _open_status_logs_by_type(self, dtype: str) -> None:
        from monitoring.ui.dialogs.status_logs_viewer import StatusLogsViewer

        StatusLogsViewer(
            self.root,
            title=f"Journal des changements - {dtype}",
            dtype=dtype,
            manager=self.model.manager,
        )

    def _open_about_dialog(self) -> None:
        messagebox.showinfo(
            "A propos",
            f"NetworkMonitoringProject\nVersion: {self.app_version}",
        )
