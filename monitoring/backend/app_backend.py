from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from monitoring.config.settings import NotificationSettings, load_settings, save_settings
from monitoring.models.devices_model import DevicesModel
from monitoring.services.auth_service import AuthService
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.services.device_service import DeviceService
from monitoring.services.device_type_service import DeviceTypeService
from monitoring.services.monitoring_service import MonitoringService
from monitoring.storage.sqlite_manager import SQLiteFileManager


@dataclass
class ApplicationBackend:
    manager: SQLiteFileManager
    model: DevicesModel
    device_service: DeviceService
    device_type_service: DeviceTypeService
    monitoring_service: MonitoringService
    auth_service: AuthService
    config_storage_service: ConfigStorageService
    settings_loader: Callable[[], NotificationSettings]
    settings_saver: Callable[[NotificationSettings], None]


def build_application_backend(
    *,
    manager: SQLiteFileManager | None = None,
    settings_loader: Callable[[], NotificationSettings] = load_settings,
    settings_saver: Callable[[NotificationSettings], None] = save_settings,
) -> ApplicationBackend:
    shared_manager = manager or SQLiteFileManager()
    device_service = DeviceService(shared_manager)
    model = DevicesModel(manager=shared_manager, device_service=device_service)
    device_type_service = DeviceTypeService(shared_manager)
    monitoring_service = MonitoringService(model, logs_store=shared_manager)
    auth_service = AuthService()
    config_storage_service = ConfigStorageService(settings_provider=settings_loader)
    return ApplicationBackend(
        manager=shared_manager,
        model=model,
        device_service=device_service,
        device_type_service=device_type_service,
        monitoring_service=monitoring_service,
        auth_service=auth_service,
        config_storage_service=config_storage_service,
        settings_loader=settings_loader,
        settings_saver=settings_saver,
    )
