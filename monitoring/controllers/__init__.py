"""Controllers package.

Do not eagerly import desktop-only controllers here, otherwise Linux server mode
tries to import tkinter transitively.
"""

from __future__ import annotations

from importlib import import_module

__all__ = ["AppController", "DeviceTypeController", "NetworkToolsController"]


def __getattr__(name: str):
    if name == "AppController":
        return import_module("monitoring.controllers.app_controller").AppController
    if name == "DeviceTypeController":
        return import_module("monitoring.controllers.device_type_controller").DeviceTypeController
    if name == "NetworkToolsController":
        return import_module("monitoring.controllers.network_tools_controller").NetworkToolsController
    raise AttributeError(name)

