"""
Point d'entree de NetworkMonitoringProject.

- mode `desktop` par defaut: dashboard Tkinter
- mode `server`: API HTTP FastAPI/uvicorn sans interface graphique
"""

from __future__ import annotations

import argparse
from tkinter import Tk

import uvicorn

from monitoring.api.app import create_app
from monitoring.backend import build_application_backend
from monitoring.controllers.app_controller import AppController
from monitoring.ui.dashboard import DashboardIHM
from monitoring.utils.logger import setup_logging


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NetworkMonitoringProject launcher")
    parser.add_argument(
        "--mode",
        choices=("desktop", "server"),
        default="desktop",
        help="Mode de lancement. `desktop` garde Tkinter, `server` lance uniquement l'API HTTP.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Adresse d'ecoute du mode server.")
    parser.add_argument("--port", type=int, default=8000, help="Port d'ecoute du mode server.")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Active le reload uvicorn en mode server.",
    )
    return parser


def run_desktop() -> None:
    root = Tk()

    backend = build_application_backend()
    controller = AppController(
        backend.model,
        monitoring_service=backend.monitoring_service,
        monitoring_runtime_service=backend.monitoring_runtime_service,
    )

    dashboard = DashboardIHM(root, model=backend.model, controller=controller, backend=backend)
    controller.view = dashboard
    dashboard.run()


def run_server(*, host: str, port: int, reload: bool = False) -> None:
    backend = build_application_backend()
    app = create_app(backend=backend)
    uvicorn.run(app, host=str(host), port=int(port), reload=bool(reload), log_config=None)


def main(argv: list[str] | None = None) -> None:
    """Initialise l'application et demarre le mode choisi."""
    setup_logging()
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    if args.mode == "server":
        run_server(host=args.host, port=args.port, reload=args.reload)
        return

    run_desktop()


if __name__ == "__main__":
    main()
