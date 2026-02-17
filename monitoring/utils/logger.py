# monitoring/utils/logger.py
import logging
import os
import sys
from datetime import datetime


def _configure_stream_handlers() -> list[logging.Handler]:
    """Crée deux handlers console : stdout pour < ERROR, stderr pour >= ERROR."""
    # Handler stdout : DEBUG/INFO/WARNING
    out_handler = logging.StreamHandler(sys.stdout)
    out_handler.setLevel(logging.DEBUG)            # vous filtrez ensuite
    out_handler.addFilter(lambda record: record.levelno < logging.ERROR)

    # Handler stderr : ERROR/CRITICAL
    err_handler = logging.StreamHandler(sys.stderr)
    err_handler.setLevel(logging.ERROR)

    return [out_handler, err_handler]


def setup_logging() -> None:
    """Configure le logging global (fichier + console couleur PyCharm friendly)."""
    app_data_root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    log_dir = os.path.join(app_data_root, "NetworkMonitoringProject", "logs")
    os.makedirs(log_dir, exist_ok=True)

    file_path = os.path.join(log_dir, "monitoring.log")
    file_handler = logging.FileHandler(file_path, encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[file_handler, *_configure_stream_handlers()],
        force=True,           # écrase une config précédente si elle existe
    )


def log_with_timestamp(message: str, level: str = "INFO") -> None:
    """Petit helper conservé pour le contrôleur."""
    logger = logging.getLogger(__name__)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    getattr(logger, level.lower(), logger.info)(f"[{timestamp}] {message}")
