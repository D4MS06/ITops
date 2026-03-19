from monitoring.ui.dialogs.technical_logs_viewer import TechnicalLogsViewer
from monitoring.utils.logger import get_log_file_path


def test_get_log_file_path_ends_with_monitoring_log():
    path = get_log_file_path()
    assert path.endswith("NetworkMonitoringProject\\logs\\monitoring.log")


def test_technical_logs_viewer_filters_by_level_text_and_monitoring_scope():
    lines = [
        "2026-03-19 10:00:00 - monitoring.services.monitoring_service - INFO - monitoring started\n",
        "2026-03-19 10:00:01 - monitoring.ui.dashboard - DEBUG - ui detail\n",
        "2026-03-19 10:00:02 - monitoring.services.monitoring_runtime_service - WARNING - runtime warning\n",
    ]

    filtered = TechnicalLogsViewer._filter_lines(
        lines,
        text_filter="warning",
        level_filter="WARNING",
        monitoring_only=True,
    )

    assert filtered == [
        "2026-03-19 10:00:02 - monitoring.services.monitoring_runtime_service - WARNING - runtime warning\n"
    ]
