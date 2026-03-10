"""
Point d'entree de NetworkMonitoringProject.

- Configure le logging (console + fichier)
- Construit un backend applicatif partage
- Lance le dashboard Tkinter
"""

from tkinter import Tk

from monitoring.backend import build_application_backend
from monitoring.controllers.app_controller import AppController
from monitoring.ui.dashboard import DashboardIHM
from monitoring.utils.logger import setup_logging


def main() -> None:
    """Initialise l'application et demarre la boucle Tk."""
    setup_logging()

    root = Tk()

    backend = build_application_backend()
    controller = AppController(
        backend.model,
        monitoring_service=backend.monitoring_service,
    )

    dashboard = DashboardIHM(root, model=backend.model, controller=controller)
    controller.view = dashboard
    dashboard.run()


if __name__ == "__main__":
    main()
