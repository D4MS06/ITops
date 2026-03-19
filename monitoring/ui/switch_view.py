from __future__ import annotations

from tkinter import Frame

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.services.device_actions_service import DeviceActionService
from monitoring.services.settings_service import SettingsService
from monitoring.ui.type_devices_view import TypeDevicesView


class SwitchIHM(TypeDevicesView):
    """Vue switch specialisee sur la vue de type generique."""

    def __init__(
        self,
        parent: Frame,
        *,
        model: DevicesModel | None = None,
        controller: AppController | None = None,
        settings_service: SettingsService | None = None,
        device_actions_service: DeviceActionService | None = None,
    ) -> None:
        super().__init__(
            parent,
            device_type_code="switch",
            type_label="Switch",
            model=model,
            controller=controller,
            settings_service=settings_service,
            device_actions_service=device_actions_service,
        )

    def _on_selection_mutual(self, _evt=None) -> None:
        self._safe_clear_master_view_selection("server_view")
        self._safe_clear_master_view_selection("consolidated_app")
