"""Controllers package (web runtime)."""

from __future__ import annotations

from importlib import import_module

__all__ = ["DeviceTypeController", "NetworkToolsController"]


def __getattr__(name: str):
    if name == "DeviceTypeController":
        return import_module("monitoring.controllers.device_type_controller").DeviceTypeController
    if name == "NetworkToolsController":
        return import_module("monitoring.controllers.network_tools_controller").NetworkToolsController
    raise AttributeError(name)

