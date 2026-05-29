from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from inspect import currentframe


def _configure_stream_handlers() -> list[logging.Handler]:
    """Create stdout/stderr console handlers with split severity."""
    out_handler = logging.StreamHandler(sys.stdout)
    out_handler.setLevel(logging.DEBUG)
    out_handler.addFilter(lambda record: record.levelno < logging.ERROR)

    err_handler = logging.StreamHandler(sys.stderr)
    err_handler.setLevel(logging.ERROR)
    return [out_handler, err_handler]


def _normalize_level_name(value: object, default: str) -> str:
    normalized = str(value or default).strip().upper()
    if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        return default
    return normalized


def _apply_logger_levels(settings: object | None) -> None:
    monitoring_level = _normalize_level_name(getattr(settings, "monitoring_log_level", "INFO"), "INFO")
    web_level = _normalize_level_name(getattr(settings, "ui_log_level", "ERROR"), "ERROR")

    logging.getLogger("monitoring.services.monitoring_service").setLevel(monitoring_level)
    logging.getLogger("monitoring.services.monitoring_runtime_service").setLevel(monitoring_level)
    logging.getLogger("monitoring.web").setLevel(web_level)


def setup_logging(settings: object | None = None) -> None:
    """Configure global logging with file + console handlers."""
    file_path = get_log_file_path()
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    root_level = _normalize_level_name(getattr(settings, "log_level", "INFO"), "INFO")

    logging.basicConfig(
        level=root_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[file_handler, *_configure_stream_handlers()],
        force=True,
    )
    _apply_logger_levels(settings)


def get_log_file_path() -> str:
    app_data_root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    log_dir = os.path.join(app_data_root, "NetworkMonitoringProject", "logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "monitoring.log")


def _caller_logger_name(default: str = __name__) -> str:
    frame = currentframe()
    if frame is None or frame.f_back is None or frame.f_back.f_back is None:
        return default
    caller_globals = frame.f_back.f_back.f_globals
    return str(caller_globals.get("__name__", default))


def log_with_timestamp(message: str, level: str = "INFO", logger_name: str | None = None) -> None:
    logger = logging.getLogger(logger_name or _caller_logger_name())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    getattr(logger, level.lower(), logger.info)(f"[{timestamp}] {message}")
