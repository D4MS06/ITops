# src/monitoring/ui/dashboard.py

from __future__ import annotations

import logging
from tkinter import BOTH, LEFT, RIGHT, TOP, X, Button, Frame, Label, Menu, Tk

from monitoring.config.settings import NotificationSettings, load_settings, save_settings
from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.base_window import BaseWindow
from monitoring.ui.consolidated_view import ConsolidatedView
from monitoring.ui.server_view import ServerIHM
from monitoring.ui.switch_view import SwitchIHM


class DashboardIHM(BaseWindow):
    """Fenetre principale: dashboard tuiles + vues detaillees a la demande."""

    def __init__(self, root: Tk, *, model: DevicesModel, controller: AppController) -> None:
        super().__init__(root, title="Tableau de bord Monitoring")
        self.logger = logging.getLogger(__name__)

        self.model = model
        self.controller = controller
        self.controller.register_view(self)

        self.current_detail = "dashboard"
        self.active_tree_filter: tuple[str, str | None] | None = None
        self.notification_settings: NotificationSettings = load_settings()
        self.controller.set_offline_delay_seconds(self.notification_settings.offline_delay_seconds)
        self.controller.set_show_status_popup(self.notification_settings.show_status_popup)

        self._build_ui()
        self.center_window()

    def _build_ui(self) -> None:
        self.root.geometry("1300x900")
        self.root.configure(bg="#e9edf2")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._create_menu()
        self._create_topbar()
        self._create_kpi_cards()
        self._create_monitoring_bar()
        self._create_detail_area()

        self._show_dashboard()
        self.update_display()

    def _create_menu(self) -> None:
        menubar = Menu(self.root)
        settings_menu = Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Notifications...", command=self._open_notification_dialog)

        monitoring_submenu = Menu(settings_menu, tearoff=0)
        monitoring_submenu.add_command(
            label="Delai hors ligne...",
            command=self._open_monitoring_dialog,
        )
        settings_menu.add_cascade(label="Monitoring", menu=monitoring_submenu)

        menubar.add_cascade(label="Parametres", menu=settings_menu)
        self.root.config(menu=menubar)

    def _create_topbar(self) -> None:
        bar = Frame(self.root, bg="#d9e0e8", height=86)
        bar.pack(fill=X, padx=10, pady=(10, 6))
        bar.pack_propagate(False)

        Label(
            bar,
            text="Tableau de bord Monitoring Reseau",
            font=("Segoe UI", 16, "bold"),
            fg="#0f172a",
            bg="#d9e0e8",
        ).pack(side=LEFT, padx=16)

        right_block = Frame(bar, bg="#d9e0e8")
        right_block.pack(side=RIGHT, padx=14)

        nav = Frame(right_block, bg="#d9e0e8")
        nav.pack(side=TOP, anchor="e", pady=(4, 2))

        self.btn_dashboard = Button(
            nav, text="Tableau de bord", command=self._show_dashboard, width=14
        )
        self.btn_dashboard.pack(side=LEFT, padx=3)
        self.btn_switch = Button(nav, text="Switchs", command=self._show_switch_detail, width=10)
        self.btn_switch.pack(side=LEFT, padx=3)
        self.btn_server = Button(nav, text="Serveurs", command=self._show_server_detail, width=10)
        self.btn_server.pack(side=LEFT, padx=3)
        self.btn_global = Button(nav, text="Globale", command=self._show_global_detail, width=10)
        self.btn_global.pack(side=LEFT, padx=3)

    def _create_monitoring_bar(self) -> None:
        self.mon_wrap = Frame(self.root, bg="#e9edf2")
        self.mon_wrap.pack(fill=X, padx=10, pady=(0, 8))
        mon = Frame(self.mon_wrap, bg="#d9e0e8", bd=1, relief="groove")
        mon.pack(fill=X, padx=0, pady=0)

        self.btn_mon_switch = Button(
            mon,
            text="Monitoring switch",
            width=16,
            command=lambda: self._toggle_monitoring_target("switch"),
        )
        self.btn_mon_switch.pack(side=LEFT, padx=6, pady=6)

        self.btn_mon_server = Button(
            mon,
            text="Monitoring Serveur",
            width=16,
            command=lambda: self._toggle_monitoring_target("server"),
        )
        self.btn_mon_server.pack(side=LEFT, padx=6, pady=6)

        self.btn_mon_global = Button(
            mon,
            text="Monitoring Global",
            width=16,
            command=lambda: self._toggle_monitoring_target("global"),
        )
        self.btn_mon_global.pack(side=LEFT, padx=6, pady=6)

    def _create_kpi_cards(self) -> None:
        self.cards_grid = Frame(self.root, bg="#e9edf2")
        self.cards_grid.pack(fill=X, padx=10, pady=(2, 8))

        self.card_values: dict[str, Label] = {}
        self.card_subs: dict[str, Label] = {}
        self.card_defs: dict[str, dict] = {}
        self.card_click_actions = {
            "switch_total": lambda: self._show_switch_filtered(None),
            "switch_up": lambda: self._show_switch_filtered("online"),
            "switch_down": lambda: self._show_switch_filtered("offline"),
            "server_total": lambda: self._show_server_filtered(None),
            "server_up": lambda: self._show_server_filtered("online"),
            "server_down": lambda: self._show_server_filtered("offline"),
            "all_total": self._show_global_filtered,
        }

        rows = [
            ("switch_total", "Total Switchs", "#334155"),
            ("switch_up", "Switchs en ligne", "#16a34a"),
            ("switch_down", "Switchs hors ligne", "#dc2626"),
            ("server_total", "Total Serveurs", "#334155"),
            ("server_up", "Serveurs en ligne", "#16a34a"),
            ("server_down", "Serveurs hors ligne", "#dc2626"),
            ("all_total", "Equipements", "#1d4ed8"),
            ("monitoring_state", "Monitoring", "#7c3aed"),
        ]

        for col in range(4):
            self.cards_grid.grid_columnconfigure(col, weight=1, uniform="kpi")

        for idx, (key, title, color) in enumerate(rows):
            row = idx // 4
            col = idx % 4
            self._create_card(self.cards_grid, key, title, color, row=row, col=col)

    def _show_summary_panels(self) -> None:
        self.cards_grid.pack(fill=X, padx=10, pady=(2, 8), before=self.detail_container)
        self.mon_wrap.pack(fill=X, padx=10, pady=(0, 8), before=self.detail_container)

    def _hide_summary_panels(self) -> None:
        self.cards_grid.pack_forget()
        self.mon_wrap.pack_forget()

    def _create_card(
        self,
        parent: Frame,
        key: str,
        title: str,
        accent: str,
        *,
        row: int,
        col: int,
    ) -> None:
        clickable = key != "monitoring_state"
        base_bg = "#f2f5f8"
        hover_bg = "#e8eef5"

        card = Frame(parent, bg=base_bg, bd=1, relief="groove", padx=8, pady=3, height=72)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=3)
        card.grid_propagate(False)

        title_lbl = Label(
            card,
            text=title,
            bg=base_bg,
            fg="#475569",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2" if clickable else "arrow",
        )
        title_lbl.pack(anchor="w")

        val = Label(
            card,
            text="-",
            bg=base_bg,
            fg=accent,
            font=("Segoe UI", 14, "bold"),
            cursor="hand2" if clickable else "arrow",
        )
        val.pack(anchor="w", pady=(1, 0))

        sub = Label(
            card,
            text="",
            bg=base_bg,
            fg="#64748b",
            font=("Segoe UI", 8),
            cursor="hand2" if clickable else "arrow",
        )
        sub.pack(anchor="w")

        self.card_values[key] = val
        self.card_subs[key] = sub
        self.card_defs[key] = {
            "frame": card,
            "labels": (title_lbl, val, sub),
            "base_bg": base_bg,
            "hover_bg": hover_bg,
            "clickable": clickable,
        }
        self._bind_card_interactions(key)

    def _bind_card_interactions(self, key: str) -> None:
        card_def = self.card_defs[key]
        if not card_def["clickable"]:
            return
        widgets = (card_def["frame"], *card_def["labels"])
        for widget in widgets:
            widget.bind("<Enter>", lambda _evt, k=key: self._set_card_hover(k, True))
            widget.bind("<Leave>", lambda _evt, k=key: self._set_card_hover(k, False))
            widget.bind("<Button-1>", lambda _evt, k=key: self._on_card_click(k))

    def _set_card_hover(self, key: str, hovered: bool) -> None:
        card_def = self.card_defs.get(key)
        if not card_def:
            return
        bg = card_def["hover_bg"] if hovered else card_def["base_bg"]
        relief = "raised" if hovered else "groove"
        card_def["frame"].config(bg=bg, relief=relief, bd=1)
        for lbl in card_def["labels"]:
            lbl.config(bg=bg)

    def _on_card_click(self, key: str) -> None:
        action = self.card_click_actions.get(key)
        if action:
            action()

    def _create_detail_area(self) -> None:
        self.detail_container = Frame(self.root, bg="#e9edf2")
        self.detail_container.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        self.placeholder = Label(
            self.detail_container,
            text="Vue tableau de bord active. Cliquez sur Switchs, Serveurs ou Globale pour afficher les details.",
            bg="#e9edf2",
            fg="#334155",
            font=("Segoe UI", 12, "bold"),
        )

        self.switch_detail_frame = Frame(self.detail_container, bg="#e9edf2")
        self.server_detail_frame = Frame(self.detail_container, bg="#e9edf2")
        self.global_detail_frame = Frame(self.detail_container, bg="#e9edf2")

        self.switch_app = SwitchIHM(
            self.switch_detail_frame,
            model=self.model,
            controller=self.controller,
        )
        self.switch_app.pack(fill=BOTH, expand=True)

        self.server_app = ServerIHM(
            self.server_detail_frame,
            model=self.model,
            controller=self.controller,
        )
        self.server_app.pack(fill=BOTH, expand=True)

        self.consolidated_app = ConsolidatedView(
            self.global_detail_frame,
            model=self.model,
            controller=self.controller,
        )
        self.consolidated_app.pack(fill=BOTH, expand=True)

        self.switch_app.tree.bind("<<TreeviewSelect>>", self._on_switch_select)
        self.server_app.tree.bind("<<TreeviewSelect>>", self._on_server_select)

    def _hide_details(self) -> None:
        self.placeholder.pack_forget()
        self.switch_detail_frame.pack_forget()
        self.server_detail_frame.pack_forget()
        self.global_detail_frame.pack_forget()

    def _show_dashboard(self) -> None:
        running_switch = self.model.do_run.get("switch", False)
        running_server = self.model.do_run.get("server", False)

        if running_switch and running_server:
            self._show_global_embedded()
            return
        if running_switch:
            self._show_switch_embedded()
            return
        if running_server:
            self._show_server_embedded()
            return

        self._show_summary_panels()
        self._hide_details()
        self.placeholder.pack(fill=BOTH, expand=True, pady=20)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()

    def _show_switch_detail(self) -> None:
        self._hide_summary_panels()
        self._hide_details()
        self.switch_app.set_local_monitoring_button_visible(True)
        self.switch_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "switch"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.switch_app.update_display()

    def _show_server_detail(self) -> None:
        self._hide_summary_panels()
        self._hide_details()
        self.server_app.set_local_monitoring_button_visible(True)
        self.server_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "server"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.server_app.update_display()

    def _show_global_detail(self) -> None:
        self._hide_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(True)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "global"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.consolidated_app.start_monitoring()

    def _show_switch_filtered(self, status: str | None) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.switch_app.set_local_monitoring_button_visible(False)
        self.switch_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = ("switch", status)
        self._update_nav_buttons()
        self.switch_app.update_display()
        self._apply_active_tree_filter()

    def _show_server_filtered(self, status: str | None) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.server_app.set_local_monitoring_button_visible(False)
        self.server_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = ("server", status)
        self._update_nav_buttons()
        self.server_app.update_display()
        self._apply_active_tree_filter()

    def _show_global_filtered(self) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(False)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = ("global", None)
        self._update_nav_buttons()
        self.consolidated_app.update_display()

    def _show_switch_embedded(self) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.switch_app.set_local_monitoring_button_visible(False)
        self.switch_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.switch_app.update_display()

    def _show_server_embedded(self) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.server_app.set_local_monitoring_button_visible(False)
        self.server_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.server_app.update_display()

    def _show_global_embedded(self) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(False)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.consolidated_app.start_monitoring()

    def _apply_active_tree_filter(self) -> None:
        if not self.active_tree_filter:
            return

        target, status_filter = self.active_tree_filter
        if target == "switch":
            self._filter_tree(self.switch_app.tree, self.model.device_data.get("switch", {}), status_filter)
        elif target == "server":
            self._filter_tree(self.server_app.tree, self.model.device_data.get("server", {}), status_filter)

    @staticmethod
    def _filter_tree(tree, devices: dict, status_filter: str | None) -> None:
        for did, dev in devices.items():
            iid = str(did)
            if not tree.exists(iid):
                continue
            status = getattr(dev, "status", "")
            if status_filter and status != status_filter:
                tree.detach(iid)
            else:
                tree.reattach(iid, "", "end")

    def _update_nav_buttons(self) -> None:
        base = "#cfd8e3"
        active = "#93c5fd"
        for name, btn in (
            ("dashboard", self.btn_dashboard),
            ("switch", self.btn_switch),
            ("server", self.btn_server),
            ("global", self.btn_global),
        ):
            btn.config(bg=active if self.current_detail == name else base, relief="sunken" if self.current_detail == name else "raised")

    def _toggle_monitoring_target(self, target: str) -> None:
        self.controller.view = self
        if target == "switch":
            self._show_switch_embedded()
        elif target == "server":
            self._show_server_embedded()
        elif target == "global":
            self._show_global_embedded()

        if target == "global":
            if any(self.model.do_run.values()):
                self.controller.stop_all_monitoring()
            else:
                self.controller.start_monitoring("switch")
                self.controller.start_monitoring("server")
            self.update_display()
            return

        if self.model.do_run.get(target, False):
            self.controller.stop_monitoring(target)
        else:
            self.controller.start_monitoring(target)
        self.update_display()

    def update_display(self) -> None:
        switches = list(self.model.device_data.get("switch", {}).values())
        servers = list(self.model.device_data.get("server", {}).values())

        sw_total = len(switches)
        srv_total = len(servers)
        sw_up = sum(1 for d in switches if getattr(d, "status", "") == "online")
        srv_up = sum(1 for d in servers if getattr(d, "status", "") == "online")
        sw_down = max(sw_total - sw_up, 0)
        srv_down = max(srv_total - srv_up, 0)
        all_total = sw_total + srv_total
        running_switch = self.model.do_run.get("switch", False)
        running_server = self.model.do_run.get("server", False)

        self.card_values["switch_total"].config(text=str(sw_total))
        self.card_subs["switch_total"].config(text="Inventaire switchs")

        self.card_values["switch_up"].config(text=str(sw_up))
        self.card_subs["switch_up"].config(text=f"{sw_total} total")

        if running_switch:
            self.card_values["switch_down"].config(text=str(sw_down), fg="#dc2626")
            self.card_subs["switch_down"].config(text=f"{sw_total} total")
        else:
            self.card_values["switch_down"].config(text="-", fg="#64748b")
            self.card_subs["switch_down"].config(text="Monitoring arrete")

        self.card_values["server_total"].config(text=str(srv_total))
        self.card_subs["server_total"].config(text="Inventaire serveurs")

        if running_server:
            self.card_values["server_up"].config(text=str(srv_up), fg="#16a34a")
            self.card_subs["server_up"].config(text=f"{srv_total} total")
        else:
            self.card_values["server_up"].config(text="-", fg="#64748b")
            self.card_subs["server_up"].config(text="Monitoring arrete")

        if running_server:
            self.card_values["server_down"].config(text=str(srv_down), fg="#dc2626")
            self.card_subs["server_down"].config(text=f"{srv_total} total")
        else:
            self.card_values["server_down"].config(text="-", fg="#64748b")
            self.card_subs["server_down"].config(text="Monitoring arrete")

        self.card_values["all_total"].config(text=str(all_total))
        down_parts = []
        if running_switch:
            down_parts.append(sw_down)
        if running_server:
            down_parts.append(srv_down)
        down_text = str(sum(down_parts)) if down_parts else "-"
        self.card_subs["all_total"].config(text=f"UP: {sw_up + srv_up}  DOWN: {down_text}")
        if running_switch and running_server:
            state = "Global"
        elif running_switch:
            state = "Switchs"
        elif running_server:
            state = "Serveurs"
        else:
            state = "Arrete"
        self.card_values["monitoring_state"].config(text=state)
        self.card_subs["monitoring_state"].config(text="Etat des sondes")

        self._update_monitoring_buttons(running_switch, running_server)
        self._apply_active_tree_filter()

    def _update_monitoring_buttons(self, running_switch: bool, running_server: bool) -> None:
        self.btn_mon_switch.config(
            bg="#16a34a" if running_switch else "#e2e8f0",
            fg="white" if running_switch else "#0f172a",
            text="Monitoring switch",
        )
        self.btn_mon_server.config(
            bg="#16a34a" if running_server else "#e2e8f0",
            fg="white" if running_server else "#0f172a",
            text="Monitoring Serveur",
        )

        running_global = running_switch and running_server
        self.btn_mon_global.config(
            bg="#7c3aed" if running_global else "#e2e8f0",
            fg="white" if running_global else "#0f172a",
            text="Arreter Global" if (running_switch or running_server) else "Demarrer Global",
        )

    def _open_notification_dialog(self) -> None:
        from monitoring.ui.dialogs.notification_settings import NotificationSettingsDialog

        dlg = NotificationSettingsDialog(self.root, self.notification_settings)
        if dlg.result:
            self.notification_settings = dlg.result
            save_settings(self.notification_settings)
            self.controller.set_offline_delay_seconds(self.notification_settings.offline_delay_seconds)
            self.controller.set_show_status_popup(self.notification_settings.show_status_popup)

    def _open_monitoring_dialog(self) -> None:
        from monitoring.ui.dialogs.monitoring_settings import MonitoringSettingsDialog

        dlg = MonitoringSettingsDialog(
            self.root,
            self.notification_settings.offline_delay_seconds,
        )
        if dlg.result is None:
            return
        self.notification_settings.offline_delay_seconds = max(1, int(dlg.result))
        save_settings(self.notification_settings)
        self.controller.set_offline_delay_seconds(self.notification_settings.offline_delay_seconds)

    def _on_switch_select(self, _evt) -> None:
        try:
            for iid in self.server_app.tree.selection():
                self.server_app.tree.selection_remove(iid)
        except Exception:
            pass

    def _on_server_select(self, _evt) -> None:
        try:
            for iid in self.switch_app.tree.selection():
                self.switch_app.tree.selection_remove(iid)
        except Exception:
            pass

    def _on_closing(self) -> None:
        try:
            self.controller.stop_all_monitoring()
        finally:
            self.root.destroy()
