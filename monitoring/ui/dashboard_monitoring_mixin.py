from __future__ import annotations

from typing import TYPE_CHECKING
from tkinter import LEFT, X, Button, Frame

from monitoring.ui.theme_utils import bind_blue_hover

if TYPE_CHECKING:
    from monitoring.ui.dashboard_contracts import DashboardMixinContract


class DashboardMonitoringMixin:
    def _create_monitoring_bar(self: "DashboardMixinContract") -> None:
        self.mon_wrap = Frame(self.root, bg=self.theme.colors["app_bg"])
        self.mon_wrap.pack(fill=X, padx=10, pady=(0, 8))
        mon = Frame(
            self.mon_wrap,
            bg=self.theme.colors["surface_bg"],
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.theme.colors["placeholder_border"],
        )
        mon.pack(fill=X, padx=0, pady=0)
        self.mon_panel = mon

        self.btn_mon_global = Button(
            mon,
            text="Monitoring Globale",
            width=16,
            command=lambda: self._toggle_monitoring_target("global"),
            bd=1,
            relief="flat",
        )
        self.btn_mon_global.pack(side=LEFT, padx=6, pady=6)

        self.type_monitor_buttons: dict[str, Button] = {}
        for dtype in self._monitored_type_codes():
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            btn = Button(
                mon,
                text=f"Monitoring {label}",
                width=16,
                command=lambda dt=dtype: self._toggle_monitoring_target(dt),
                bd=1,
                relief="flat",
            )
            btn.pack(side=LEFT, padx=6, pady=6)
            self.type_monitor_buttons[dtype] = btn

        for btn in [self.btn_mon_global, *self.type_monitor_buttons.values()]:
            bind_blue_hover(btn, lambda: self.theme.colors)

    def _device_status_counts(self: "DashboardMixinContract", dtype: str) -> tuple[int, int, int]:
        devices = list(self.model.device_data.get(dtype, {}).values())
        total = len(devices)
        up = sum(1 for device in devices if str(getattr(device, "status", "")).strip().lower() == "online")
        down = sum(1 for device in devices if str(getattr(device, "status", "")).strip().lower() == "offline")
        return total, up, down

    def _apply_card_status_widgets(self: "DashboardMixinContract", card_key: str, *, up: int, down: int, running: bool) -> None:
        status_widgets = self.card_defs.get(card_key, {}).get("status_widgets") or {}
        if not isinstance(status_widgets, dict):
            return
        muted = self.theme.colors["text_muted"]
        lbl_up = status_widgets.get("lbl_up")
        val_up = status_widgets.get("val_up")
        lbl_down = status_widgets.get("lbl_down")
        val_down = status_widgets.get("val_down")
        if running:
            if lbl_up is not None:
                lbl_up.config(text="En ligne:", fg=muted)
            if lbl_down is not None:
                lbl_down.config(text="Hors ligne:", fg=muted)
            if val_up is not None:
                val_up.config(text=str(up), fg="#16a34a")
            if val_down is not None:
                val_down.config(text=str(down), fg="#dc2626")
            return
        for widget in (lbl_up, lbl_down, val_up, val_down):
            if widget is None:
                continue
            widget.config(text="", fg=muted)

    def _dashboard_metrics(self: "DashboardMixinContract") -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
        totals: dict[str, int] = {}
        ups: dict[str, int] = {}
        downs: dict[str, int] = {}
        for dtype in self._ordered_type_codes():
            total, up, down = DashboardMonitoringMixin._device_status_counts(self, dtype)
            totals[dtype] = total
            ups[dtype] = up
            downs[dtype] = down
        return totals, ups, downs

    def update_display(self: "DashboardMixinContract") -> None:
        if not all(
            hasattr(self, attr)
            for attr in ("card_values", "card_subs", "card_defs", "btn_mon_global", "type_monitor_buttons")
        ):
            return
        totals, ups, downs = DashboardMonitoringMixin._dashboard_metrics(self)
        for dtype in self._ordered_type_codes():
            total = totals[dtype]
            up = ups[dtype]
            down = downs[dtype]
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            self.card_values[f"{dtype}_status"].config(text=str(total), fg=self.theme.colors.get("kpi_total_accent", self.theme.colors["text_secondary"]))
            self.card_subs[f"{dtype}_status"].config(text=f"Inventaire {label.lower()}")
            running = bool(self.model.do_run.get(dtype, False))
            DashboardMonitoringMixin._apply_card_status_widgets(self, f"{dtype}_status", up=up, down=down, running=running)

        all_total = sum(totals.values())
        monitored = self._monitored_type_codes()
        running_any = any(bool(self.model.do_run.get(dtype, False)) for dtype in monitored)
        running_all = bool(monitored) and all(bool(self.model.do_run.get(dtype, False)) for dtype in monitored)
        visible_up = sum(ups[dtype] for dtype in monitored if bool(self.model.do_run.get(dtype, False)))
        visible_down = sum(downs[dtype] for dtype in monitored if bool(self.model.do_run.get(dtype, False)))
        self.card_values["all_total"].config(text=str(all_total))
        self.card_subs["all_total"].config(text="Inventaire global")
        DashboardMonitoringMixin._apply_card_status_widgets(self, "all_total", up=visible_up, down=visible_down, running=running_any)
        state = "Global" if running_all else ("Partiel" if running_any else "Arrete")
        self.card_values["monitoring_state"].config(text=state)
        self.card_subs["monitoring_state"].config(text="Etat des sondes")
        if hasattr(self, "web_server_manager") and "web_server_state" in self.card_values:
            web_state = self.web_server_manager.state()
            self.card_values["web_server_state"].config(
                text="Demarre" if web_state.running else "Arrete",
                fg="#16a34a" if web_state.running else "#dc2626",
            )
            self.card_subs["web_server_state"].config(text=f"{web_state.host}:{web_state.port}")
            web_card = self.card_defs.get("web_server_state", {})
            play_btn = web_card.get("action_play_button")
            stop_btn = web_card.get("action_stop_button")
            if play_btn is not None:
                play_btn.config(
                    text="Play",
                    bg=self.theme.colors["button_active_bg"] if web_state.running else self.theme.colors["button_inactive_bg"],
                    fg=self.theme.colors["button_active_fg"] if web_state.running else self.theme.colors["button_inactive_fg"],
                )
            if stop_btn is not None:
                stop_btn.config(
                    text="Stop",
                    state="normal" if web_state.running else "disabled",
                    bg="#dc2626" if web_state.running else self.theme.colors["button_inactive_bg"],
                    fg="#ffffff" if web_state.running else self.theme.colors["button_inactive_fg"],
                    activebackground="#b91c1c" if web_state.running else self.theme.colors["button_inactive_bg"],
                    activeforeground="#ffffff" if web_state.running else self.theme.colors["button_inactive_fg"],
                )

        self._update_monitoring_buttons()
        if (
            getattr(self, "current_detail", "dashboard") == "dashboard"
            and not getattr(self, "active_tree_filter", None)
            and hasattr(self, "_show_dashboard")
        ):
            self._show_dashboard()
        self._apply_active_tree_filter()

    def _update_monitoring_buttons(self: "DashboardMixinContract") -> None:
        monitored = self._monitored_type_codes()
        for dtype, btn in self.type_monitor_buttons.items():
            running = bool(self.model.do_run.get(dtype, False))
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            btn.config(
                bg=self.theme.colors["button_active_bg"] if running else self.theme.colors["button_inactive_bg"],
                fg=self.theme.colors["button_active_fg"] if running else self.theme.colors["button_inactive_fg"],
                text=f"Monitoring {label}",
            )
        running_global = bool(monitored) and all(bool(self.model.do_run.get(dtype, False)) for dtype in monitored)
        self.btn_mon_global.config(
            bg=self.theme.colors["button_global_bg"] if running_global else self.theme.colors["button_inactive_bg"],
            fg=self.theme.colors["button_active_fg"] if running_global else self.theme.colors["button_inactive_fg"],
            text="Monitoring Globale",
        )
