from __future__ import annotations

from importlib import import_module

__all__ = ["BaseWindow", "resource_path", "DashboardIHM", "SwitchIHM", "ServerIHM"]


def __getattr__(name: str):
    if name in {"BaseWindow", "resource_path"}:
        module = import_module("monitoring.ui.base_window")
        return getattr(module, name)
    if name == "DashboardIHM":
        module = import_module("monitoring.ui.dashboard")
        return getattr(module, name)
    if name == "SwitchIHM":
        module = import_module("monitoring.ui.switch_view")
        return getattr(module, name)
    if name == "ServerIHM":
        module = import_module("monitoring.ui.server_view")
        return getattr(module, name)
    raise AttributeError(name)
