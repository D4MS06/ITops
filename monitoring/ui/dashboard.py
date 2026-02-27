# src/monitoring/ui/dashboard.py

from __future__ import annotations

import logging
import os
import subprocess
import threading
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, TOP, X, Button, Frame, Label, Menu, PhotoImage, StringVar, Tk, messagebox

from monitoring.config.settings import NotificationSettings, load_settings, save_settings
from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.base_window import BaseWindow
from monitoring.ui.consolidated_view import ConsolidatedView
from monitoring.ui.dialogs.watermark_settings import WatermarkSettingsDialog
from monitoring.ui.server_view import ServerIHM
from monitoring.ui.switch_view import SwitchIHM
from monitoring.ui.theme_manager import list_themes, resolve_theme
from monitoring.ui.theme_utils import bind_blue_hover
from monitoring.utils.updater import download_update_asset, find_available_update

try:
    from __init__ import __version__ as APP_VERSION
except Exception:
    APP_VERSION = "unknown"


class DashboardIHM(BaseWindow):
    """Fenetre principale: dashboard tuiles + vues detaillees a la demande."""

    def __init__(self, root: Tk, *, model: DevicesModel, controller: AppController) -> None:
        self.app_version = APP_VERSION
        super().__init__(root, title=f"Tableau de bord Monitoring v{self.app_version}")
        self.logger = logging.getLogger(__name__)

        self.model = model
        self.controller = controller
        self.controller.register_view(self)

        self.current_detail = "dashboard"
        self.active_tree_filter: tuple[str, str | None] | None = None
        self.notification_settings: NotificationSettings = load_settings()
        self.theme = resolve_theme(getattr(self.notification_settings, "ui_theme", "light"))
        self.controller.set_offline_delay_seconds(self.notification_settings.offline_delay_seconds)
        self.controller.set_online_recovery_delay_seconds(
            self.notification_settings.online_recovery_delay_seconds
        )
        self.controller.set_notification_cooldown_seconds(
            self.notification_settings.notification_cooldown_seconds
        )
        self.controller.set_failures_for_offline(self.notification_settings.failures_for_offline)
        self.controller.set_successes_for_online(self.notification_settings.successes_for_online)
        self.controller.set_ping_timeout_ms(self.notification_settings.ping_timeout_ms)
        self.controller.set_probe_interval_ms(self.notification_settings.probe_interval_ms)
        self.controller.set_log_diagnostic_events(self.notification_settings.log_diagnostic_events)
        self.controller.set_show_status_popup(self.notification_settings.show_status_popup)

        self._build_ui()
        self.center_window()

    def _build_ui(self) -> None:
        self.root.geometry("1300x900")
        self.root.configure(bg=self.theme.colors["app_bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._create_menu()
        self._create_topbar()
        self._create_kpi_cards()
        self._create_monitoring_bar()
        self._create_detail_area()

        self._show_dashboard()
        self.update_display()
        self._apply_theme()
        self.root.after(150, lambda: self._apply_window_chrome_theme(self.theme.key == "dark"))
        self.root.after(1800, self._check_updates_on_startup)

    def _create_menu(self) -> None:
        c = self.theme.colors
        self.root.config(menu="")
        menu_frame = Frame(self.root, bg=c["menu_bg"], height=28)
        menu_frame.pack(fill=X, padx=0, pady=0)
        menu_frame.pack_propagate(False)
        self.var_theme = StringVar(value=self.theme.key)

        btn_settings = Button(
            menu_frame,
            text="Parametres",
            bg=c["menu_bg"],
            fg=c["menu_fg"],
            activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
            activeforeground=c.get("control_hover_fg", c["text_primary"]),
            relief="flat",
            bd=0,
            padx=10,
            pady=3,
            command=lambda: self._popup_custom_menu(btn_settings, self._settings_menu_items()),
        )
        btn_settings.pack(side=LEFT, padx=(4, 0))
        btn_logs = Button(
            menu_frame,
            text="Journaux",
            bg=c["menu_bg"],
            fg=c["menu_fg"],
            activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
            activeforeground=c.get("control_hover_fg", c["text_primary"]),
            relief="flat",
            bd=0,
            padx=10,
            pady=3,
            command=lambda: self._popup_custom_menu(btn_logs, self._logs_menu_items()),
        )
        btn_logs.pack(side=LEFT, padx=(2, 0))
        btn_help = Button(
            menu_frame,
            text="Aide",
            bg=c["menu_bg"],
            fg=c["menu_fg"],
            activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
            activeforeground=c.get("control_hover_fg", c["text_primary"]),
            relief="flat",
            bd=0,
            padx=10,
            pady=3,
            command=lambda: self._popup_custom_menu(btn_help, self._help_menu_items()),
        )
        btn_help.pack(side=LEFT, padx=(2, 0))

        self.menu_bar_frame = menu_frame
        self.menu_buttons = [btn_settings, btn_logs, btn_help]
        self._menu_popups: list[Frame] = []
        self._submenu_anchor_by_level: dict[int, str] = {}
        self._menu_outside_click_bind = None

    def _settings_menu_items(self) -> list[tuple[str, object]]:
        return [
            ("Notifications (email + popup)...", self._open_notification_dialog),
            (
                "Monitoring",
                [("Seuils monitoring + logs diagnostics...", self._open_monitoring_dialog)],
            ),
            (
                "Personnalisation",
                [
                    (
                        "Theme",
                        [
                            ("Light", lambda: self._set_theme_from_menu("light")),
                            ("Dark", lambda: self._set_theme_from_menu("dark")),
                        ],
                    ),
                    (
                        "Indicateurs de statut",
                        [
                            ("Badge coche / croix", lambda: self._set_status_indicator_style_from_menu("badge")),
                            ("Pastille moderne", lambda: self._set_status_indicator_style_from_menu("dot")),
                        ],
                    ),
                    ("Image de fond...", self._open_watermark_dialog),
                ],
            ),
            ("Mises a jour...", self._open_update_settings_dialog),
        ]

    def _logs_menu_items(self) -> list[tuple[str, object]]:
        return [
            ("Journal global des changements...", self._open_global_status_logs),
            ("Journal switches...", lambda: self._open_status_logs_by_type("switch")),
            ("Journal serveurs...", lambda: self._open_status_logs_by_type("server")),
        ]

    def _help_menu_items(self) -> list[tuple[str, object]]:
        return [("A propos...", self._open_about_dialog)]

    def _set_theme_from_menu(self, theme_key: str) -> None:
        self.var_theme.set(theme_key)
        self._on_theme_changed()

    def _set_status_indicator_style_from_menu(self, style_key: str) -> None:
        self.notification_settings.status_indicator_style = str(style_key or "badge").strip().lower()
        save_settings(self.notification_settings)
        self._refresh_status_indicators()

    def _refresh_status_indicators(self) -> None:
        style_key = str(getattr(self.notification_settings, "status_indicator_style", "badge") or "badge")
        for view in (
            getattr(self, "switch_app", None),
            getattr(self, "server_app", None),
            getattr(self, "consolidated_app", None),
        ):
            if view is None:
                continue
            try:
                view.refresh_status_icons(style_key)
            except Exception:
                continue

    def _close_custom_menu(self) -> None:
        if self._menu_outside_click_bind is not None:
            try:
                self.root.unbind("<Button-1>", self._menu_outside_click_bind)
            except Exception:
                pass
            self._menu_outside_click_bind = None
        for popup in list(getattr(self, "_menu_popups", [])):
            try:
                popup.place_forget()
                popup.destroy()
            except Exception:
                pass
        self._menu_popups = []
        self._submenu_anchor_by_level = {}

    def _close_submenus_from(self, index: int) -> None:
        popups = getattr(self, "_menu_popups", [])
        for popup in popups[index:]:
            try:
                popup.place_forget()
                popup.destroy()
            except Exception:
                pass
        self._menu_popups = popups[:index]
        for lvl in list(getattr(self, "_submenu_anchor_by_level", {}).keys()):
            if lvl >= index:
                self._submenu_anchor_by_level.pop(lvl, None)

    def _build_dropdown_frame(
        self,
        x: int,
        y: int,
        items: list[tuple[str, object]],
        *,
        level: int,
        animate: bool = False,
        animate_from: tuple[int, int, int] | None = None,
    ) -> Frame:
        c = self.theme.colors
        popup = Frame(
            self.root,
            bg=c["menu_bg"],
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=c.get("menu_border", c["placeholder_border"]),
        )
        popup.lift()
        if animate:
            self._animate_menu_open(
                popup,
                x,
                y,
                level=level,
                animate_from=animate_from,
            )
        else:
            popup.place(x=x, y=y)

        for label, action in items:
            if isinstance(action, list):
                btn = Button(
                    popup,
                    text=label,
                    anchor="w",
                    justify="left",
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                    activeforeground=c.get("control_hover_fg", c["text_primary"]),
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    padx=10,
                    pady=4,
                )
                btn.pack(fill=X)
                btn.bind("<Enter>", lambda _e=None, b=btn: self._menu_item_hover(b, True))
                btn.bind("<Leave>", lambda _e=None, b=btn: self._menu_item_hover(b, False))

                def _open_submenu(_evt=None, *, b=btn, submenu_items=action, lvl=level):
                    anchor_key = f"{lvl+1}:{b.winfo_id()}"
                    if self._submenu_anchor_by_level.get(lvl + 1) == anchor_key:
                        return
                    self._close_submenus_from(lvl + 1)
                    bx = b.winfo_rootx() - self.root.winfo_rootx() + b.winfo_width()
                    by = b.winfo_rooty() - self.root.winfo_rooty()
                    source_x = b.winfo_rootx() - self.root.winfo_rootx()
                    source_y = b.winfo_rooty() - self.root.winfo_rooty()
                    source_w = b.winfo_width()
                    sub = self._build_dropdown_frame(
                        bx,
                        by,
                        submenu_items,
                        level=lvl + 1,
                        animate=True,
                        animate_from=(source_x, source_y, source_w),
                    )
                    self._menu_popups.append(sub)
                    self._submenu_anchor_by_level[lvl + 1] = anchor_key

                btn.configure(command=_open_submenu)
                btn.bind("<Enter>", _open_submenu, add="+")
            else:
                btn = Button(
                    popup,
                    text=label,
                    anchor="w",
                    justify="left",
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                    activeforeground=c.get("control_hover_fg", c["text_primary"]),
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    padx=10,
                    pady=4,
                    command=lambda a=action: self._on_custom_menu_action(a),
                )
                btn.pack(fill=X)
                btn.bind(
                    "<Enter>",
                    lambda _e=None, b=btn, lvl=level: (
                        self._close_submenus_from(lvl + 1),
                        self._menu_item_hover(b, True),
                    ),
                )
                btn.bind("<Leave>", lambda _e=None, b=btn: self._menu_item_hover(b, False))
        return popup

    def _menu_item_hover(self, button: Button, hovered: bool) -> None:
        c = self.theme.colors
        hover_bg = c.get("control_hover_bg", c["panel_hover_bg"])
        hover_fg = c.get("control_hover_fg", c["text_primary"])
        hover_border = c.get("control_hover_border", c["nav_active_bg"])
        try:
            if hovered:
                button.configure(
                    bg=hover_bg,
                    fg=hover_fg,
                    relief="flat",
                    bd=0,
                    highlightthickness=1,
                    highlightbackground=hover_border,
                )
            else:
                button.configure(
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                )
        except Exception:
            pass

    def _popup_custom_menu(self, anchor_button: Button, items: list[tuple[str, object]]) -> None:
        self._close_custom_menu()
        x = anchor_button.winfo_x()
        y = self.menu_bar_frame.winfo_y() + self.menu_bar_frame.winfo_height()
        popup = self._build_dropdown_frame(x, y, items, level=0, animate=True)
        self._menu_popups = [popup]
        self._menu_outside_click_bind = self.root.bind("<Button-1>", self._on_root_click_close_menu, add="+")

    def _animate_menu_open(
        self,
        popup: Frame,
        target_x: int,
        target_y: int,
        *,
        level: int,
        animate_from: tuple[int, int, int] | None = None,
    ) -> None:
        if level == 0:
            start_x = target_x - 8
            start_y = target_y - 4
        elif animate_from is not None:
            src_x, src_y, src_w = animate_from
            # Sous-menu: depart a l'interieur de l'item parent pour un effet "sortie".
            start_x = src_x + max(6, int(src_w * 0.35))
            start_y = src_y + 1
        else:
            start_x = target_x - 10
            start_y = target_y
        steps = 10 if level > 0 else 6
        popup.place(x=start_x, y=start_y)

        def _step(i: int) -> None:
            if not popup.winfo_exists():
                return
            if i >= steps:
                popup.place_configure(x=target_x, y=target_y)
                return
            t = (i + 1) / steps
            t = 1 - (1 - t) * (1 - t)
            x = int(start_x + (target_x - start_x) * t)
            y = int(start_y + (target_y - start_y) * t)
            popup.place_configure(x=x, y=y)
            popup.after(16 if level > 0 else 14, lambda: _step(i + 1))

        _step(0)

    def _on_root_click_close_menu(self, event) -> None:
        popups = getattr(self, "_menu_popups", [])
        if not popups:
            return
        widget = event.widget
        while widget is not None:
            if widget in popups:
                return
            widget = getattr(widget, "master", None)
        for btn in getattr(self, "menu_buttons", []):
            if event.widget is btn:
                return
        self._close_custom_menu()

    def _on_custom_menu_action(self, action) -> None:
        self._close_custom_menu()
        try:
            action()
        except Exception:
            pass

    @staticmethod
    def _popup_menu(menu: Menu, anchor_button: Button) -> None:
        try:
            x = anchor_button.winfo_rootx()
            y = anchor_button.winfo_rooty() + anchor_button.winfo_height()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _create_topbar(self) -> None:
        bar = Frame(self.root, bg=self.theme.colors["surface_bg"], height=86)
        bar.pack(fill=X, padx=10, pady=(10, 6))
        bar.pack_propagate(False)
        self.topbar = bar

        Label(
            bar,
            text="Tableau de bord Monitoring Reseau",
            font=("Segoe UI", 16, "bold"),
            fg=self.theme.colors["text_primary"],
            bg=self.theme.colors["surface_bg"],
        ).pack(side=LEFT, padx=16)

        right_block = Frame(bar, bg=self.theme.colors["surface_bg"])
        right_block.pack(side=RIGHT, padx=14)
        self.topbar_right = right_block

        nav = Frame(right_block, bg=self.theme.colors["surface_bg"])
        nav.pack(side=TOP, anchor="e", pady=(4, 2))
        self.navbar = nav

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
        for btn in (self.btn_dashboard, self.btn_switch, self.btn_server, self.btn_global):
            bind_blue_hover(btn, lambda: self.theme.colors)

    def _create_monitoring_bar(self) -> None:
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

        self.btn_mon_switch = Button(
            mon,
            text="Monitoring switch",
            width=16,
            command=lambda: self._toggle_monitoring_target("switch"),
            bd=1,
            relief="flat",
        )
        self.btn_mon_switch.pack(side=LEFT, padx=6, pady=6)

        self.btn_mon_server = Button(
            mon,
            text="Monitoring Serveur",
            width=16,
            command=lambda: self._toggle_monitoring_target("server"),
            bd=1,
            relief="flat",
        )
        self.btn_mon_server.pack(side=LEFT, padx=6, pady=6)

        self.btn_mon_global = Button(
            mon,
            text="Monitoring Global",
            width=16,
            command=lambda: self._toggle_monitoring_target("global"),
            bd=1,
            relief="flat",
        )
        self.btn_mon_global.pack(side=LEFT, padx=6, pady=6)
        for btn in (self.btn_mon_switch, self.btn_mon_server, self.btn_mon_global):
            bind_blue_hover(btn, lambda: self.theme.colors)

    def _create_kpi_cards(self) -> None:
        self.cards_grid = Frame(self.root, bg=self.theme.colors["app_bg"])
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
            ("switch_total", "Total Switchs", self.theme.colors.get("kpi_total_accent", self.theme.colors["text_secondary"])),
            ("switch_up", "Switchs en ligne", "#16a34a"),
            ("switch_down", "Switchs hors ligne", "#dc2626"),
            ("server_total", "Total Serveurs", self.theme.colors.get("kpi_total_accent", self.theme.colors["text_secondary"])),
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
        base_bg = self.theme.colors["panel_bg"]
        hover_bg = self.theme.colors["panel_hover_bg"]

        card = Frame(
            parent,
            bg=base_bg,
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.theme.colors["placeholder_border"],
            padx=8,
            pady=3,
            height=72,
        )
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=3)
        card.grid_propagate(False)

        title_lbl = Label(
            card,
            text=title,
            bg=base_bg,
            fg=self.theme.colors["text_secondary"],
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
            fg=self.theme.colors["text_muted"],
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
        border = self.theme.colors["nav_active_bg"] if hovered else self.theme.colors["placeholder_border"]
        card_def["frame"].config(bg=bg, relief="flat", bd=0, highlightbackground=border)
        for lbl in card_def["labels"]:
            lbl.config(bg=bg)

    def _on_card_click(self, key: str) -> None:
        action = self.card_click_actions.get(key)
        if action:
            action()

    def _create_detail_area(self) -> None:
        self.detail_container = Frame(self.root, bg=self.theme.colors["app_bg"])
        self.detail_container.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        self.placeholder = Frame(self.detail_container, bg=self.theme.colors["placeholder_bg"])
        self._dashboard_watermark = None
        self.placeholder_image = Label(self.placeholder, bg=self.theme.colors["placeholder_bg"])
        self.placeholder_image.pack(pady=(24, 8))
        self.dashboard_placeholder_title = Label(
            self.placeholder,
            text="Aucune sonde active",
            bg=self.theme.colors["placeholder_bg"],
            fg=self.theme.colors["text_primary"],
            font=("Segoe UI", 13, "bold"),
        )
        self.dashboard_placeholder_title.pack(pady=(8, 4))
        self.dashboard_placeholder_subtitle = Label(
            self.placeholder,
            text="Cliquez sur Monitoring switch, Monitoring Serveur ou Demarrer Global.",
            bg=self.theme.colors["placeholder_bg"],
            fg=self.theme.colors["text_muted"],
            font=("Segoe UI", 10),
        )
        self.dashboard_placeholder_subtitle.pack()
        self._refresh_dashboard_watermark()

        self.switch_detail_frame = Frame(self.detail_container, bg=self.theme.colors["app_bg"])
        self.server_detail_frame = Frame(self.detail_container, bg=self.theme.colors["app_bg"])
        self.global_detail_frame = Frame(self.detail_container, bg=self.theme.colors["app_bg"])

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
        self.switch_app.set_force_inventory_visible(False)
        self.switch_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "switch"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.switch_app.update_display()

    def _show_server_detail(self) -> None:
        self._hide_summary_panels()
        self._hide_details()
        self.server_app.set_local_monitoring_button_visible(True)
        self.server_app.set_force_inventory_visible(False)
        self.server_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "server"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.server_app.update_display()

    def _show_global_detail(self) -> None:
        self._hide_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(True)
        self.consolidated_app.set_force_inventory_visible(False)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "global"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.consolidated_app.start_monitoring()

    def _show_switch_filtered(self, status: str | None) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.switch_app.set_local_monitoring_button_visible(False)
        self.switch_app.set_force_inventory_visible(status is None)
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
        self.server_app.set_force_inventory_visible(status is None)
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
        self.consolidated_app.set_force_inventory_visible(True)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = ("global", None)
        self._update_nav_buttons()
        self.consolidated_app.update_display()

    def _show_switch_embedded(self) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.switch_app.set_local_monitoring_button_visible(False)
        self.switch_app.set_force_inventory_visible(False)
        self.switch_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.switch_app.update_display()

    def _show_server_embedded(self) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.server_app.set_local_monitoring_button_visible(False)
        self.server_app.set_force_inventory_visible(False)
        self.server_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.server_app.update_display()

    def _show_global_embedded(self) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(False)
        self.consolidated_app.set_force_inventory_visible(False)
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
        base = self.theme.colors["nav_inactive_bg"]
        active = self.theme.colors["nav_active_bg"]
        fg = self.theme.colors["text_primary"]
        for name, btn in (
            ("dashboard", self.btn_dashboard),
            ("switch", self.btn_switch),
            ("server", self.btn_server),
            ("global", self.btn_global),
        ):
            btn.config(
                bg=active if self.current_detail == name else base,
                fg=fg,
                relief="sunken" if self.current_detail == name else "raised",
            )

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
            self.card_values["switch_down"].config(text="-", fg=self.theme.colors["text_muted"])
            self.card_subs["switch_down"].config(text="Monitoring arrete")

        self.card_values["server_total"].config(text=str(srv_total))
        self.card_subs["server_total"].config(text="Inventaire serveurs")

        if running_server:
            self.card_values["server_up"].config(text=str(srv_up), fg="#16a34a")
            self.card_subs["server_up"].config(text=f"{srv_total} total")
        else:
            self.card_values["server_up"].config(text="-", fg=self.theme.colors["text_muted"])
            self.card_subs["server_up"].config(text="Monitoring arrete")

        if running_server:
            self.card_values["server_down"].config(text=str(srv_down), fg="#dc2626")
            self.card_subs["server_down"].config(text=f"{srv_total} total")
        else:
            self.card_values["server_down"].config(text="-", fg=self.theme.colors["text_muted"])
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
            bg=self.theme.colors["button_active_bg"] if running_switch else self.theme.colors["button_inactive_bg"],
            fg=self.theme.colors["button_active_fg"] if running_switch else self.theme.colors["button_inactive_fg"],
            text="Monitoring switch",
        )
        self.btn_mon_server.config(
            bg=self.theme.colors["button_active_bg"] if running_server else self.theme.colors["button_inactive_bg"],
            fg=self.theme.colors["button_active_fg"] if running_server else self.theme.colors["button_inactive_fg"],
            text="Monitoring Serveur",
        )

        running_global = running_switch and running_server
        self.btn_mon_global.config(
            bg=self.theme.colors["button_global_bg"] if running_global else self.theme.colors["button_inactive_bg"],
            fg=self.theme.colors["button_active_fg"] if running_global else self.theme.colors["button_inactive_fg"],
            text="Arreter Global" if (running_switch or running_server) else "Demarrer Global",
        )

    def _open_notification_dialog(self) -> None:
        from monitoring.ui.dialogs.notification_settings import NotificationSettingsDialog

        dlg = NotificationSettingsDialog(self.root, self.notification_settings)
        if dlg.result:
            self.notification_settings = dlg.result
            save_settings(self.notification_settings)
            self.controller.set_offline_delay_seconds(self.notification_settings.offline_delay_seconds)
            self.controller.set_online_recovery_delay_seconds(
                self.notification_settings.online_recovery_delay_seconds
            )
            self.controller.set_notification_cooldown_seconds(
                self.notification_settings.notification_cooldown_seconds
            )
            self.controller.set_failures_for_offline(self.notification_settings.failures_for_offline)
            self.controller.set_successes_for_online(self.notification_settings.successes_for_online)
            self.controller.set_ping_timeout_ms(self.notification_settings.ping_timeout_ms)
            self.controller.set_probe_interval_ms(self.notification_settings.probe_interval_ms)
            self.controller.set_log_diagnostic_events(self.notification_settings.log_diagnostic_events)
            self.controller.set_show_status_popup(self.notification_settings.show_status_popup)

    def _open_monitoring_dialog(self) -> None:
        from monitoring.ui.dialogs.monitoring_settings import MonitoringSettingsDialog

        dlg = MonitoringSettingsDialog(
            self.root,
            self.notification_settings.offline_delay_seconds,
            self.notification_settings.online_recovery_delay_seconds,
            self.notification_settings.notification_cooldown_seconds,
            self.notification_settings.failures_for_offline,
            self.notification_settings.successes_for_online,
            self.notification_settings.ping_timeout_ms,
            self.notification_settings.probe_interval_ms,
            self.notification_settings.log_diagnostic_events,
        )
        if dlg.result is None:
            return
        self.notification_settings.offline_delay_seconds = max(
            1, int(dlg.result["offline_delay_seconds"])
        )
        self.notification_settings.online_recovery_delay_seconds = max(
            1, int(dlg.result["online_recovery_delay_seconds"])
        )
        self.notification_settings.notification_cooldown_seconds = max(
            0, int(dlg.result["notification_cooldown_seconds"])
        )
        self.notification_settings.failures_for_offline = max(
            1, int(dlg.result["failures_for_offline"])
        )
        self.notification_settings.successes_for_online = max(
            1, int(dlg.result["successes_for_online"])
        )
        self.notification_settings.ping_timeout_ms = max(250, int(dlg.result["ping_timeout_ms"]))
        self.notification_settings.probe_interval_ms = max(250, int(dlg.result["probe_interval_ms"]))
        self.notification_settings.log_diagnostic_events = bool(dlg.result["log_diagnostic_events"])
        save_settings(self.notification_settings)
        self.controller.set_offline_delay_seconds(self.notification_settings.offline_delay_seconds)
        self.controller.set_online_recovery_delay_seconds(
            self.notification_settings.online_recovery_delay_seconds
        )
        self.controller.set_notification_cooldown_seconds(
            self.notification_settings.notification_cooldown_seconds
        )
        self.controller.set_failures_for_offline(self.notification_settings.failures_for_offline)
        self.controller.set_successes_for_online(self.notification_settings.successes_for_online)
        self.controller.set_ping_timeout_ms(self.notification_settings.ping_timeout_ms)
        self.controller.set_probe_interval_ms(self.notification_settings.probe_interval_ms)
        self.controller.set_log_diagnostic_events(self.notification_settings.log_diagnostic_events)

    def _on_theme_changed(self) -> None:
        requested = self.var_theme.get().strip().lower() if hasattr(self, "var_theme") else "light"
        self.theme = resolve_theme(requested)
        self.notification_settings.ui_theme = self.theme.key
        save_settings(self.notification_settings)
        self._apply_theme()
        self.root.after(50, lambda: self._apply_window_chrome_theme(self.theme.key == "dark"))

    def _apply_theme(self) -> None:
        c = self.theme.colors
        self.root.configure(bg=c["app_bg"])
        self._apply_window_chrome_theme(self.theme.key == "dark")
        for menu_obj in (
            getattr(self, "settings_menu", None),
            getattr(self, "monitoring_submenu", None),
            getattr(self, "personalization_submenu", None),
            getattr(self, "theme_submenu", None),
            getattr(self, "logs_menu", None),
            getattr(self, "help_menu", None),
        ):
            if menu_obj is None:
                continue
            try:
                menu_obj.configure(
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    activebackground=c["panel_hover_bg"],
                    activeforeground=c["text_primary"],
                )
            except Exception:
                pass
        try:
            self.menu_bar_frame.configure(bg=c["menu_bg"])
        except Exception:
            pass
        for btn in getattr(self, "menu_buttons", []):
            try:
                btn.configure(
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                    activeforeground=c.get("control_hover_fg", c["text_primary"]),
                    relief="flat",
                    bd=0,
                )
            except Exception:
                continue

        for widget in (
            getattr(self, "cards_grid", None),
            getattr(self, "mon_wrap", None),
            getattr(self, "detail_container", None),
            getattr(self, "switch_detail_frame", None),
            getattr(self, "server_detail_frame", None),
            getattr(self, "global_detail_frame", None),
        ):
            if widget is not None:
                try:
                    widget.configure(bg=c["app_bg"])
                except Exception:
                    pass

        for widget in (
            getattr(self, "topbar", None),
            getattr(self, "topbar_right", None),
            getattr(self, "navbar", None),
            getattr(self, "mon_panel", None),
        ):
            if widget is not None:
                try:
                    widget.configure(bg=c["surface_bg"])
                except Exception:
                    pass
        try:
            self.mon_panel.configure(highlightbackground=c["placeholder_border"])
        except Exception:
            pass

        for widget in (getattr(self, "placeholder", None), getattr(self, "placeholder_image", None)):
            if widget is not None:
                try:
                    widget.configure(bg=c["placeholder_bg"])
                except Exception:
                    pass

        # Update top bar labels.
        for child in self.topbar.winfo_children() if hasattr(self, "topbar") else []:
            if isinstance(child, Label):
                try:
                    # Keep version text slightly muted.
                    fg = c["text_secondary"] if str(child.cget("text")).startswith("v") else c["text_primary"]
                    child.configure(bg=c["surface_bg"], fg=fg)
                except Exception:
                    continue

        # Update KPI card palette.
        for key, card_def in self.card_defs.items():
            card_def["base_bg"] = c["panel_bg"]
            card_def["hover_bg"] = c["panel_hover_bg"]
            frame = card_def["frame"]
            labels = card_def["labels"]
            try:
                frame.configure(bg=c["panel_bg"])
                labels[0].configure(bg=c["panel_bg"], fg=c["text_secondary"])
                labels[2].configure(bg=c["panel_bg"], fg=c["text_muted"])
                if key in ("switch_total", "server_total"):
                    labels[1].configure(fg=c.get("kpi_total_accent", c["text_secondary"]))
            except Exception:
                pass
            self._set_card_hover(key, False)

        try:
            self.dashboard_placeholder_title.configure(bg=c["placeholder_bg"], fg=c["text_primary"])
            self.dashboard_placeholder_subtitle.configure(bg=c["placeholder_bg"], fg=c["text_muted"])
            self.placeholder.configure(bg=c["placeholder_bg"])
            self.placeholder_image.configure(bg=c["placeholder_bg"])
        except Exception:
            pass

        running_switch = self.model.do_run.get("switch", False)
        running_server = self.model.do_run.get("server", False)
        self._update_nav_buttons()
        self._update_monitoring_buttons(running_switch, running_server)
        self._refresh_dashboard_watermark()

        for view in (getattr(self, "switch_app", None), getattr(self, "server_app", None), getattr(self, "consolidated_app", None)):
            if view is None:
                continue
            try:
                if hasattr(view, "apply_theme"):
                    view.apply_theme(self.theme.key)
                elif hasattr(view, "update_display"):
                    view.update_display()
            except Exception:
                continue

    def _open_update_settings_dialog(self) -> None:
        from monitoring.ui.dialogs.update_settings import UpdateSettingsDialog

        dlg = UpdateSettingsDialog(self.root, self.notification_settings)
        if dlg.result:
            self.notification_settings = dlg.result
            save_settings(self.notification_settings)

    def _custom_watermark_target_path(self) -> Path:
        app_data_root = os.environ.get("LOCALAPPDATA") or str(Path.home())
        target_dir = Path(app_data_root) / "NetworkMonitoringProject" / "assets"
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / "custom_watermark.png"

    def _materialize_watermark(self, source_path: str, opacity: float, *, source_baseline_opacity: float = 1.0) -> str:
        src = Path(source_path)
        if not source_path or not src.is_file():
            return ""
        target = self._custom_watermark_target_path()
        try:
            from PIL import Image, ImageEnhance  # type: ignore
        except Exception:
            raise RuntimeError("Pillow est requis pour appliquer l'opacite du watermark.")

        img = Image.open(src).convert("RGBA")
        img.thumbnail((360, 220), Image.Resampling.LANCZOS)
        alpha = img.split()[-1]
        target_opacity = min(1.0, max(0.05, float(opacity or 0.16)))
        baseline_opacity = min(1.0, max(0.05, float(source_baseline_opacity or 1.0)))
        factor = target_opacity / baseline_opacity
        alpha = ImageEnhance.Brightness(alpha).enhance(factor)
        img.putalpha(alpha)
        img.save(target, format="PNG")
        return str(target)

    def _open_watermark_dialog(self) -> None:
        dlg = WatermarkSettingsDialog(
            self.root,
            current_source_path=str(getattr(self.notification_settings, "watermark_source_path", "") or ""),
            current_rendered_path=str(getattr(self.notification_settings, "watermark_image_path", "") or ""),
            current_opacity=float(getattr(self.notification_settings, "watermark_opacity", 0.16) or 0.16),
        )
        if dlg.result is None:
            return

        source_path = str(dlg.result.get("source_path", "") or "").strip()
        opacity = min(1.0, max(0.05, float(dlg.result.get("opacity", 0.16) or 0.16)))
        cleared = bool(dlg.result.get("cleared", False))
        current_rendered = str(getattr(self.notification_settings, "watermark_image_path", "") or "").strip()
        current_saved_opacity = float(getattr(self.notification_settings, "watermark_opacity", 0.16) or 0.16)
        if cleared:
            self.notification_settings.watermark_source_path = ""
            self.notification_settings.watermark_image_path = ""
            self.notification_settings.watermark_opacity = opacity
            save_settings(self.notification_settings)
            self._refresh_watermarks()
            return

        if not source_path:
            source_path = str(getattr(self.notification_settings, "watermark_source_path", "") or "").strip()
        if not source_path:
            source_path = str(getattr(self.notification_settings, "watermark_image_path", "") or "").strip()

        try:
            baseline = 1.0
            try:
                if source_path and current_rendered and Path(source_path).resolve() == Path(current_rendered).resolve():
                    baseline = min(1.0, max(0.05, current_saved_opacity))
            except Exception:
                baseline = 1.0

            processed_path = self._materialize_watermark(source_path, opacity, source_baseline_opacity=baseline)
            _img_check = PhotoImage(file=processed_path)
            del _img_check
        except Exception as exc:
            messagebox.showerror(
                "Personnalisation",
                f"Impossible d'appliquer l'image de fond: {exc}",
            )
            return

        # If source equals the generated file, keep source empty to avoid cumulative reprocessing.
        try:
            same_as_generated = bool(current_rendered) and Path(source_path).resolve() == Path(current_rendered).resolve()
        except Exception:
            same_as_generated = False
        self.notification_settings.watermark_source_path = "" if same_as_generated else source_path
        self.notification_settings.watermark_image_path = processed_path
        self.notification_settings.watermark_opacity = opacity
        save_settings(self.notification_settings)
        self._refresh_watermarks()

    def _refresh_dashboard_watermark(self) -> None:
        custom_path = str(getattr(self.notification_settings, "watermark_image_path", "") or "").strip()
        selected = custom_path if custom_path and Path(custom_path).is_file() else ""

        if selected:
            try:
                self._dashboard_watermark = PhotoImage(file=selected)
            except Exception:
                self._dashboard_watermark = None
        else:
            self._dashboard_watermark = None
        self.placeholder_image.configure(image=self._dashboard_watermark)
        self.placeholder_image.image = self._dashboard_watermark
        if self._dashboard_watermark is None:
            self.placeholder_image.pack_forget()
        elif not self.placeholder_image.winfo_manager():
            self.placeholder_image.pack(pady=(24, 8))

    def _refresh_watermarks(self) -> None:
        self._refresh_dashboard_watermark()
        custom_path = str(getattr(self.notification_settings, "watermark_image_path", "") or "").strip()
        for view in (self.switch_app, self.server_app, self.consolidated_app):
            try:
                view.refresh_watermark_image(custom_path)
            except Exception:
                continue

    def _open_global_status_logs(self) -> None:
        from monitoring.ui.dialogs.status_logs_viewer import StatusLogsViewer

        StatusLogsViewer(self.root, title="Journal global des changements de statut")

    def _open_status_logs_by_type(self, dtype: str) -> None:
        from monitoring.ui.dialogs.status_logs_viewer import StatusLogsViewer

        StatusLogsViewer(
            self.root,
            title=f"Journal des changements - {dtype}",
            dtype=dtype,
        )

    def _check_updates_on_startup(self) -> None:
        if not bool(getattr(self.notification_settings, "updates_enabled", False)):
            return

        def worker() -> None:
            try:
                info = find_available_update(self.app_version, self.notification_settings)
            except Exception as exc:
                self.logger.warning("Verification MAJ impossible: %s", exc)
                return
            if info is None:
                return
            self.root.after(0, lambda: self._prompt_install_update(info))

        threading.Thread(target=worker, daemon=True, name="UpdateCheck").start()

    def _prompt_install_update(self, info) -> None:
        msg = (
            f"Une nouvelle version est disponible: v{info.version}\n\n"
            f"Release: {info.release_name}\n\n"
            "Voulez-vous telecharger et installer la mise a jour maintenant ?"
        )
        if not messagebox.askyesno("Mise a jour disponible", msg):
            return

        def worker() -> None:
            try:
                setup_path = download_update_asset(info, self.notification_settings)
            except Exception as exc:
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Mise a jour", f"Telechargement impossible: {exc}"),
                )
                return
            self.root.after(0, lambda: self._run_installer_and_exit(setup_path))

        threading.Thread(target=worker, daemon=True, name="UpdateDownload").start()

    def _run_installer_and_exit(self, setup_path: str) -> None:
        try:
            subprocess.Popen([setup_path], shell=False)
        except Exception as exc:
            messagebox.showerror("Mise a jour", f"Impossible de lancer l'installateur: {exc}")
            return
        self._on_closing()

    def _open_about_dialog(self) -> None:
        messagebox.showinfo(
            "A propos",
            f"NetworkMonitoringProject\nVersion: {self.app_version}",
        )

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
