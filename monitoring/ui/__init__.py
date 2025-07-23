# monitoring/ui/__init__.py

from monitoring.ui.base_window import BaseWindow, resource_path
from monitoring.ui.dashboard import DashboardIHM
from monitoring.ui.switch_view import SwitchIHM
from monitoring.ui.server_view import ServerIHM

__all__ = [
    "BaseWindow",
    "resource_path",
    "DashboardIHM",
    "SwitchIHM",
    "ServerIHM",
]
