from __future__ import annotations

from importlib import import_module

__all__ = [
    "AuthService",
    "DeviceFormService",
    "DeviceService",
    "DeviceTypeService",
    "MonitoringService",
    "MonitoringRuntimeService",
    "WebServerManager",
    "CaddyManager",
]


def __getattr__(name: str):
    if name == "DeviceFormService":
        return import_module("monitoring.services.device_form_service").DeviceFormService
    if name == "AuthService":
        return import_module("monitoring.services.auth_service").AuthService
    if name == "DeviceService":
        return import_module("monitoring.services.device_service").DeviceService
    if name == "DeviceTypeService":
        return import_module("monitoring.services.device_type_service").DeviceTypeService
    if name == "MonitoringService":
        return import_module("monitoring.services.monitoring_service").MonitoringService
    if name == "MonitoringRuntimeService":
        return import_module("monitoring.services.monitoring_runtime_service").MonitoringRuntimeService
    if name == "WebServerManager":
        return import_module("monitoring.services.web_server_manager").WebServerManager
    if name == "CaddyManager":
        return import_module("monitoring.services.caddy_manager").CaddyManager
    if name == "monitoring_service":
        return import_module("monitoring.services.monitoring_service")
    raise AttributeError(name)
