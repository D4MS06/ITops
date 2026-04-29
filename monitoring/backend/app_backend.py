from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from monitoring.config.settings import NotificationSettings, load_settings, save_settings
from monitoring.models.devices_model import DevicesModel
from monitoring.services.auth_service import AuthService
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.services.device_actions_service import DeviceActionService
from monitoring.services.device_service import DeviceService
from monitoring.services.device_type_service import DeviceTypeService
from monitoring.services.monitoring_runtime_service import MonitoringRuntimeService
from monitoring.services.monitoring_service import MonitoringService
from monitoring.services.settings_service import SettingsService
from monitoring.storage.mariadb_manager import MariaDBFileManager


@dataclass
class ApplicationBackend:
    manager: MariaDBFileManager
    model: DevicesModel
    device_service: DeviceService
    device_type_service: DeviceTypeService
    monitoring_service: MonitoringService
    monitoring_runtime_service: MonitoringRuntimeService
    auth_service: AuthService
    config_storage_service: ConfigStorageService
    device_actions_service: DeviceActionService
    settings_service: SettingsService
    settings_loader: Callable[[], NotificationSettings]
    settings_saver: Callable[[NotificationSettings], None]

    def shutdown(self) -> None:
        self.monitoring_runtime_service.stop_all()
        self.monitoring_service.shutdown()


def build_application_backend(
    *,
    manager: MariaDBFileManager | None = None,
    settings_loader: Callable[[], NotificationSettings] = load_settings,
    settings_saver: Callable[[NotificationSettings], None] = save_settings,
) -> ApplicationBackend:
    shared_manager = manager or MariaDBFileManager()
    auth_store_path = Path(getattr(shared_manager, "data_dir", Path.cwd())).parent / "config" / "auth.json"
    settings_service = SettingsService(loader=settings_loader, saver=settings_saver)
    device_service = DeviceService(shared_manager)
    model = DevicesModel(manager=shared_manager, device_service=device_service)
    device_type_service = DeviceTypeService(shared_manager)
    monitoring_service = MonitoringService(
        model,
        logs_store=shared_manager,
        notifier_settings_provider=settings_service.get,
    )
    monitoring_runtime_service = MonitoringRuntimeService(model, monitoring_service)
    auth_service = AuthService(session_store=shared_manager, password_store_path=auth_store_path)
    config_storage_service = ConfigStorageService(settings_provider=settings_service.get)
    device_actions_service = DeviceActionService()
    return ApplicationBackend(
        manager=shared_manager,
        model=model,
        device_service=device_service,
        device_type_service=device_type_service,
        monitoring_service=monitoring_service,
        monitoring_runtime_service=monitoring_runtime_service,
        auth_service=auth_service,
        config_storage_service=config_storage_service,
        device_actions_service=device_actions_service,
        settings_service=settings_service,
        settings_loader=settings_loader,
        settings_saver=settings_saver,
    )
