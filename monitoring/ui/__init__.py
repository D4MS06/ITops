# monitoring/ui/__init__.py

from .base_window import BaseWindow, resource_path
from .dashboard import DashboardIHM
from .switch_view import SwitchIHM
from .server_view import ServerIHM

__all__ = [
    "BaseWindow",
    "resource_path",
    "DashboardIHM",
    "SwitchIHM",
    "ServerIHM",
]
