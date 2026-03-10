from __future__ import annotations

from importlib import import_module

__all__ = ["Device", "DeviceReadingError", "Switch", "Server", "DevicesModel"]


def __getattr__(name: str):
    if name == "Device":
        return import_module("monitoring.models.device").Device
    if name == "DeviceReadingError":
        return import_module("monitoring.utils.exceptions").DeviceReadingError
    if name == "Switch":
        return import_module("monitoring.models.switch").Switch
    if name == "Server":
        return import_module("monitoring.models.server").Server
    if name == "DevicesModel":
        return import_module("monitoring.models.devices_model").DevicesModel
    raise AttributeError(name)
