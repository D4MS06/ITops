"""
Point d'entree de ITops.

- mode `server` uniquement: API HTTP FastAPI/uvicorn sans interface graphique
"""

from __future__ import annotations

import argparse
import os
from monitoring.config.settings import load_settings
from monitoring.config.hebergement_web import load_hebergement_web_config
from monitoring.utils.logger import setup_logging


def build_cli_parser() -> argparse.ArgumentParser:
    hebergement = load_hebergement_web_config()
    parser = argparse.ArgumentParser(description="ITops launcher")
    parser.add_argument("--mode", choices=("server",), default="server", help="Mode de lancement (server uniquement).")
    parser.add_argument(
        "--host",
        default=str(getattr(hebergement, "hote_ecoute", "0.0.0.0") or "0.0.0.0"),
        help="Adresse d'ecoute du mode server.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(getattr(hebergement, "port_ecoute", 8080) or 8080),
        help="Port d'ecoute du mode server.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Active le reload uvicorn en mode server.",
    )
    return parser


def run_server(*, host: str, port: int, reload: bool = False) -> None:
    import uvicorn

    from monitoring.api.app import create_app
    from monitoring.backend import build_application_backend

    backend = build_application_backend()
    app = create_app(backend=backend)
    uvicorn.run(app, host=str(host), port=int(port), reload=bool(reload), log_config=None)


def _is_truthy_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_falsy_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"0", "false", "no", "off"}


def _apply_local_dev_defaults() -> None:
    auto_flag = os.environ.get("NMP_DEV_LOCAL_AUTO_SETUP")
    if _is_falsy_env(auto_flag):
        return
    auto_enabled = _is_truthy_env(auto_flag)
    if not auto_enabled:
        in_pycharm_windows = os.name == "nt" and str(os.environ.get("PYCHARM_HOSTED") or "").strip() == "1"
        auto_enabled = bool(in_pycharm_windows)
    if not auto_enabled:
        return
    os.environ.setdefault("NMP_DEV_SKIP_SETUP_WIZARD", "1")
    os.environ.setdefault("NMP_SETUP_SKIP_MARIADB_PROVISION", "1")
    os.environ.setdefault("NMP_SETUP_SKIP_REVERSE_PROXY_SETUP", "1")


def main(argv: list[str] | None = None) -> None:
    """Initialise l'application et demarre le mode choisi."""
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    _apply_local_dev_defaults()
    setup_logging(load_settings())
    run_server(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
