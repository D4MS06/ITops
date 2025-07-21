# main.py
"""
Point d’entrée de NetworkMonitoringProject.

– Configure le logging (console + fichier)
– Instancie UN modèle + UN contrôleur
– Lance le Dashboard Tkinter
"""

from tkinter import Tk
from monitoring.utils.logger import setup_logging
from monitoring.models.devices_model import DevicesModel
from monitoring.controllers.app_controller import AppController
from monitoring.ui.dashboard import DashboardIHM


def main() -> None:
    """Initialise l'application et démarre la boucle Tk."""
    # 1. Logging global
    setup_logging()

    # 2. Racine Tkinter
    root = Tk()

    # 3. Modèle + contrôleur uniques
    model = DevicesModel()
    controller = AppController(model, None)  # la vue sera branchée après création

    # 4. Vue principale (dashboard) à laquelle on passe model & controller
    dashboard = DashboardIHM(root, model=model, controller=controller)
    controller.view = dashboard  # on boucle la référence (MVC)

    # 5. On lance la boucle principale
    dashboard.run()


if __name__ == "__main__":
    main()
