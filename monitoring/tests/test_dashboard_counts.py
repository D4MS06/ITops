from types import SimpleNamespace

from monitoring.ui.dashboard import DashboardIHM


class _DummyLabel:
    def __init__(self):
        self.props = {}

    def config(self, **kwargs):
        self.props.update(kwargs)


def _build_card_def():
    return {
        "status_widgets": {
            "lbl_up": _DummyLabel(),
            "val_up": _DummyLabel(),
            "lbl_down": _DummyLabel(),
            "val_down": _DummyLabel(),
        }
    }


def test_dashboard_counts_only_explicit_offline_and_running_types():
    fake = SimpleNamespace()
    fake.model = SimpleNamespace(
        device_data={
            "server": {
                "a": SimpleNamespace(status="online"),
                "b": SimpleNamespace(status="idle"),
                "c": SimpleNamespace(status="offline"),
            },
            "switch": {
                "d": SimpleNamespace(status="online"),
            },
        },
        do_run={"server": True, "switch": False},
        type_definitions={
            "server": {"label": "Serveur", "monitoring_enabled": True},
            "switch": {"label": "Switch", "monitoring_enabled": True},
        },
    )
    fake.theme = SimpleNamespace(
        colors={
            "text_secondary": "#111111",
            "text_muted": "#222222",
            "kpi_total_accent": "#333333",
        }
    )
    fake.card_values = {
        "server_status": _DummyLabel(),
        "switch_status": _DummyLabel(),
        "all_total": _DummyLabel(),
        "monitoring_state": _DummyLabel(),
    }
    fake.card_subs = {
        "server_status": _DummyLabel(),
        "switch_status": _DummyLabel(),
        "all_total": _DummyLabel(),
        "monitoring_state": _DummyLabel(),
    }
    fake.card_defs = {
        "server_status": _build_card_def(),
        "switch_status": _build_card_def(),
        "all_total": _build_card_def(),
    }
    fake.btn_mon_global = object()
    fake.type_monitor_buttons = {"server": object(), "switch": object()}
    fake._ordered_type_codes = lambda: ["server", "switch"]
    fake._monitored_type_codes = lambda: ["server", "switch"]
    fake._update_monitoring_buttons = lambda: None
    fake._apply_active_tree_filter = lambda: None

    DashboardIHM.update_display(fake)

    assert fake.card_defs["server_status"]["status_widgets"]["val_up"].props["text"] == "1"
    assert fake.card_defs["server_status"]["status_widgets"]["val_down"].props["text"] == "1"
    assert fake.card_defs["switch_status"]["status_widgets"]["val_up"].props["text"] == ""
    assert fake.card_defs["all_total"]["status_widgets"]["val_up"].props["text"] == "1"
    assert fake.card_defs["all_total"]["status_widgets"]["val_down"].props["text"] == "1"
