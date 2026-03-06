# src/monitoring/ui/dashboard.py

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, TOP, X, Button, Canvas, Frame, Label, Menu, PhotoImage, StringVar, Tk, Toplevel, filedialog, messagebox
from tkinter import ttk

from monitoring.config.settings import NotificationSettings, load_settings, save_settings
from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.base_window import BaseWindow
from monitoring.ui.consolidated_view import ConsolidatedView
from monitoring.ui.dialogs.device_types_settings import DeviceTypesSettingsDialog
from monitoring.ui.dialogs.watermark_settings import WatermarkSettingsDialog
from monitoring.ui.type_devices_view import TypeDevicesView
from monitoring.ui.theme_manager import list_themes, resolve_theme
from monitoring.ui.theme_utils import bind_blue_hover
from monitoring.utils.config_files import (
    find_switch_config_files,
    open_path_with_default_app,
    resolve_switch_configs_dir,
)
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

    def _ordered_type_codes(self) -> list[str]:
        items = list(self.model.type_definitions.items())
        items.sort(key=lambda kv: (int(kv[1].get("sort_order", 0) or 0), str(kv[1].get("label", kv[0])).lower()))
        return [str(code) for code, _meta in items]

    def _monitored_type_codes(self) -> list[str]:
        return [code for code in self._ordered_type_codes() if bool(self.model.type_definitions.get(code, {}).get("monitoring_enabled", True))]

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
        btn_configs = Button(
            menu_frame,
            text="Configurations",
            bg=c["menu_bg"],
            fg=c["menu_fg"],
            activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
            activeforeground=c.get("control_hover_fg", c["text_primary"]),
            relief="flat",
            bd=0,
            padx=10,
            pady=3,
            command=lambda: self._popup_custom_menu(btn_configs, self._configs_menu_items()),
        )
        btn_configs.pack(side=LEFT, padx=(2, 0))
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
        self.menu_buttons = [btn_settings, btn_logs, btn_configs, btn_help]
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
        items: list[tuple[str, object]] = [("Journal global des changements...", self._open_global_status_logs)]
        for dtype in self._ordered_type_codes():
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            items.append((f"Journal {label}...", lambda dt=dtype: self._open_status_logs_by_type(dt)))
        return items

    def _configs_menu_items(self) -> list[tuple[str, object]]:
        return [
            (
                "Equipements",
                [
                    ("Types de devices...", self._open_device_types_settings),
                    ("Telecharger la conf du device selectionne", self._download_selected_device_config),
                ],
            ),
            (
                "Dossier des configs",
                [
                    ("Ouvrir dossier global des configs", self._open_switch_configs_root),
                    ("Choisir dossier des configs...", self._choose_switch_configs_dir),
                ],
            ),
        ]

    def _help_menu_items(self) -> list[tuple[str, object]]:
        return [("A propos...", self._open_about_dialog)]

    def _switch_configs_root_dir(self) -> Path:
        configured = str(getattr(self.notification_settings, "switch_configs_dir", "") or "").strip()
        return resolve_switch_configs_dir(configured)

    def _choose_switch_configs_dir(self) -> None:
        current = self._switch_configs_root_dir()
        chosen = filedialog.askdirectory(
            parent=self.root,
            title="Selectionner le dossier des configurations switch",
            initialdir=str(current),
            mustexist=False,
        )
        if not chosen:
            return
        self.notification_settings.switch_configs_dir = str(Path(chosen))
        save_settings(self.notification_settings)

    def _open_switch_configs_root(self) -> None:
        root_dir = self._switch_configs_root_dir()
        root_dir.mkdir(parents=True, exist_ok=True)
        try:
            open_path_with_default_app(root_dir)
        except Exception as exc:
            messagebox.showerror("Configurations", f"Impossible d'ouvrir le dossier: {exc}")

    def _open_device_types_settings(self) -> None:
        DeviceTypesSettingsDialog(self.root, on_changed=self._on_device_types_changed)

    def _on_device_types_changed(self) -> None:
        try:
            self.model.refresh_type_definitions()
            self._rebuild_dynamic_sections()
            self.controller._refresh_all_views()
        except Exception:
            self.logger.exception("Erreur rafraichissement types de devices")

    def _rebuild_dynamic_sections(self) -> None:
        for view in [*getattr(self, "type_views", {}).values(), getattr(self, "consolidated_app", None)]:
            if view is None:
                continue
            try:
                self.controller.unregister_view(view)
            except Exception:
                continue
        for widget in (
            getattr(self, "topbar", None),
            getattr(self, "cards_grid", None),
            getattr(self, "mon_wrap", None),
            getattr(self, "detail_container", None),
        ):
            try:
                if widget is not None:
                    widget.destroy()
            except Exception:
                continue
        self._create_topbar()
        self._create_kpi_cards()
        self._create_monitoring_bar()
        self._create_detail_area()
        self._show_dashboard()
        self.update_display()
        self._apply_theme()

    def _get_selected_config_device_record(self):
        if bool(getattr(self.global_detail_frame, "winfo_manager", lambda: "")()):
            sel = tuple(self.consolidated_app.tree.selection())
            if sel:
                iid = str(sel[0])
                if "::" in iid:
                    dtype, did = iid.split("::", 1)
                    dev = self.model.device_data.get(dtype, {}).get(did)
                    if dev is not None and self.model.is_config_download_type(dtype):
                        return dtype, did, dev

        for dtype in self._ordered_type_codes():
            frame = self.type_detail_frames.get(dtype)
            view = self.type_views.get(dtype)
            if frame is None or view is None:
                continue
            if not bool(getattr(frame, "winfo_manager", lambda: "")()):
                continue
            sel = tuple(view.tree.selection())
            if not sel:
                continue
            did = str(sel[0])
            dev = self.model.device_data.get(dtype, {}).get(did)
            if dev is not None and self.model.is_config_download_type(dtype):
                return dtype, did, dev
        return None, None, None

    def _download_selected_device_config(self) -> None:
        _dtype, _did, dev = self._get_selected_config_device_record()
        if dev is None:
            messagebox.showinfo(
                "Configurations",
                "Selectionnez un equipement compatible configuration dans une vue de type ou en vue globale.",
            )
            return
        root_dir = self._switch_configs_root_dir()
        matches = find_switch_config_files(root_dir, str(getattr(dev, "name", "")), str(getattr(dev, "ip", "")))
        if not matches:
            messagebox.showinfo(
                "Configurations",
                f"Aucun fichier trouve pour {dev.name} ({dev.ip}).\nDossier scanne: {root_dir}",
            )
            return
        source = matches[0]
        target = filedialog.asksaveasfilename(
            parent=self.root,
            title="Telecharger la conf",
            initialfile=source.name,
            defaultextension=source.suffix or ".cfg",
            filetypes=[("Config", "*.cfg *.conf *.txt"), ("Tous les fichiers", "*.*")],
        )
        if not target:
            return
        try:
            shutil.copy2(source, target)
            messagebox.showinfo("Configurations", f"Configuration telechargee vers:\n{target}")
        except Exception as exc:
            messagebox.showerror("Configurations", f"Impossible de telecharger la configuration: {exc}")

    def _set_theme_from_menu(self, theme_key: str) -> None:
        self.var_theme.set(theme_key)
        self._on_theme_changed()

    def _set_status_indicator_style_from_menu(self, style_key: str) -> None:
        self.notification_settings.status_indicator_style = str(style_key or "badge").strip().lower()
        save_settings(self.notification_settings)
        self._refresh_status_indicators()

    def _refresh_status_indicators(self) -> None:
        style_key = str(getattr(self.notification_settings, "status_indicator_style", "badge") or "badge")
        for view in [*getattr(self, "type_views", {}).values(), getattr(self, "consolidated_app", None)]:
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
                # Avoid opening submenus immediately at menu spawn when cursor
                # already rests on an item; require actual pointer movement.
                btn.bind("<Motion>", _open_submenu, add="+")
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

        self.btn_dashboard = Button(nav, text="Tableau de bord", command=self._show_dashboard, width=14)
        self.btn_dashboard.pack(side=LEFT, padx=3)
        self.type_nav_buttons: dict[str, Button] = {}
        for dtype in self._ordered_type_codes():
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            btn = Button(nav, text=label, command=lambda dt=dtype: self._show_type_detail(dt), width=10)
            btn.pack(side=LEFT, padx=3)
            self.type_nav_buttons[dtype] = btn
        self.btn_global = Button(nav, text="Globale", command=self._show_global_detail, width=10)
        self.btn_global.pack(side=LEFT, padx=3)
        self.btn_cards_edit = Button(
            nav,
            text="\u270E",
            command=self._toggle_cards_edit_mode,
            width=3,
            relief="solid",
            bd=1,
            font=("Segoe UI Symbol", 10, "bold"),
        )
        self.btn_cards_edit.pack(side=LEFT, padx=(8, 3))
        self.btn_cards_add = self._create_round_action_pill(
            nav,
            symbol="+",
            size=34,
            command=self._on_add_card_click,
            fill="#2563EB",
            hover_fill="#1D4ED8",
            text_color="#FFFFFF",
            disabled_fill="#CBD5E1",
            disabled_text="#64748B",
            container_bg=self.theme.colors["surface_bg"],
        )
        self.btn_cards_add.pack(side=LEFT, padx=(2, 3))
        for btn in [self.btn_dashboard, *self.type_nav_buttons.values(), self.btn_global]:
            bind_blue_hover(btn, lambda: self.theme.colors)
        bind_blue_hover(self.btn_cards_edit, lambda: self.theme.colors)

    @staticmethod
    def _pill_meta(widget: Canvas) -> dict:
        return getattr(widget, "_pill_meta", {})

    def _create_round_action_pill(
        self,
        parent: Frame,
        *,
        symbol: str,
        size: int,
        command,
        fill: str,
        hover_fill: str,
        text_color: str,
        disabled_fill: str,
        disabled_text: str,
        container_bg: str,
    ) -> Canvas:
        pad = 2
        pill = Canvas(
            parent,
            width=size,
            height=size,
            bd=0,
            highlightthickness=0,
            bg=container_bg,
            cursor="hand2",
        )
        oval = pill.create_oval(pad, pad, size - pad, size - pad, fill=fill, outline=fill, width=1)
        cx = size / 2.0
        cy = size / 2.0
        half = max(5, int(size * 0.2))
        stroke = max(2, int(size * 0.12))
        icon_items: list[int] = []
        # Draw vector icons instead of text glyphs for consistent centering.
        icon_items.append(
            pill.create_line(
                cx - half,
                cy,
                cx + half,
                cy,
                fill=text_color,
                width=stroke,
                capstyle="round",
            )
        )
        if symbol == "+":
            icon_items.append(
                pill.create_line(
                    cx,
                    cy - half,
                    cx,
                    cy + half,
                    fill=text_color,
                    width=stroke,
                    capstyle="round",
                )
            )
        pill._pill_meta = {
            "command": command,
            "oval": oval,
            "icon_items": icon_items,
            "fill": fill,
            "hover_fill": hover_fill,
            "text_color": text_color,
            "disabled_fill": disabled_fill,
            "disabled_text": disabled_text,
            "enabled": True,
            "hovered": False,
        }

        def _on_click(_evt=None) -> None:
            meta = self._pill_meta(pill)
            if bool(meta.get("enabled", True)):
                try:
                    cmd = meta.get("command")
                    if callable(cmd):
                        cmd()
                except Exception:
                    pass

        def _on_enter(_evt=None) -> None:
            meta = self._pill_meta(pill)
            meta["hovered"] = True
            self._set_round_action_pill_state(pill, enabled=bool(meta.get("enabled", True)))

        def _on_leave(_evt=None) -> None:
            meta = self._pill_meta(pill)
            meta["hovered"] = False
            self._set_round_action_pill_state(pill, enabled=bool(meta.get("enabled", True)))

        pill.bind("<Button-1>", _on_click)
        pill.bind("<Enter>", _on_enter)
        pill.bind("<Leave>", _on_leave)
        return pill

    def _set_round_action_pill_state(
        self,
        pill: Canvas,
        *,
        enabled: bool,
        border_color: str | None = None,
    ) -> None:
        meta = self._pill_meta(pill)
        if not meta:
            return
        meta["enabled"] = bool(enabled)
        hovered = bool(meta.get("hovered", False))
        if enabled:
            fill = str(meta.get("hover_fill")) if hovered else str(meta.get("fill"))
            text_color = str(meta.get("text_color"))
            outline = str(border_color or fill)
            width = 2 if border_color else 1
            cursor = "hand2"
        else:
            fill = str(meta.get("disabled_fill"))
            text_color = str(meta.get("disabled_text"))
            outline = fill
            width = 1
            cursor = "arrow"
        try:
            pill.itemconfigure(meta.get("oval"), fill=fill, outline=outline, width=width)
            for item_id in meta.get("icon_items", []):
                pill.itemconfigure(item_id, fill=text_color)
            pill.configure(cursor=cursor)
        except Exception:
            pass

    @staticmethod
    def _set_round_action_pill_container_bg(pill: Canvas, bg: str) -> None:
        try:
            pill.configure(bg=bg)
        except Exception:
            pass

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

    def _create_kpi_cards(self) -> None:
        self.cards_grid = Frame(self.root, bg=self.theme.colors["app_bg"])
        self.cards_grid.pack(fill=X, padx=10, pady=(2, 8))
        self.cards_edit_mode = False
        self._drag_card_key: str | None = None
        self._card_order: list[str] = []
        self._hidden_cards: set[str] = set()

        self.card_values: dict[str, Label] = {}
        self.card_subs: dict[str, Label] = {}
        self.card_defs: dict[str, dict] = {}
        self.card_click_actions = {"all_total": self._show_global_filtered}
        rows = []
        for dtype in self._ordered_type_codes():
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            self.card_click_actions[f"{dtype}_status"] = lambda dt=dtype: self._show_type_filtered(dt, None)
            rows.extend(
                [
                    (f"{dtype}_status", f"Etat {label}", self.theme.colors.get("kpi_total_accent", self.theme.colors["text_secondary"])),
                ]
            )
        rows.extend([("all_total", "Equipements", "#1d4ed8"), ("monitoring_state", "Monitoring", "#7c3aed")])
        default_order = [key for key, _title, _accent in rows]
        self._card_order, self._hidden_cards = self._load_saved_cards_layout(default_order)

        for col in range(4):
            self.cards_grid.grid_columnconfigure(col, weight=1, uniform="kpi")

        row_by_key = {key: (title, color) for key, title, color in rows}
        for key in default_order:
            title, color = row_by_key[key]
            self._create_card(self.cards_grid, key, title, color, row=0, col=0)
        self._layout_cards()
        self._apply_cards_edit_ui_state()

    def _load_saved_cards_layout(self, default_order: list[str]) -> tuple[list[str], set[str]]:
        raw = str(getattr(self.notification_settings, "dashboard_cards_order_json", "") or "").strip()
        hidden_raw = str(getattr(self.notification_settings, "dashboard_hidden_cards_json", "") or "").strip()
        ordered: list[str] = []
        hidden: set[str] = set()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    ordered = [str(v) for v in parsed if isinstance(v, str) and str(v) in default_order]
            except Exception:
                ordered = []
        if hidden_raw:
            try:
                hidden_parsed = json.loads(hidden_raw)
                if isinstance(hidden_parsed, list):
                    hidden = {str(v) for v in hidden_parsed if isinstance(v, str) and str(v) in default_order}
            except Exception:
                hidden = set()
        if not ordered:
            ordered = list(default_order)
        ordered = [k for k in ordered if k not in hidden]
        known = set(ordered) | hidden
        for key in default_order:
            if key not in known:
                ordered.append(key)
        return ordered, hidden

    def _save_cards_layout(self) -> None:
        try:
            self.notification_settings.dashboard_cards_order_json = json.dumps(self._card_order, ensure_ascii=False)
            self.notification_settings.dashboard_hidden_cards_json = json.dumps(sorted(self._hidden_cards), ensure_ascii=False)
            save_settings(self.notification_settings)
        except Exception:
            self.logger.exception("Erreur sauvegarde disposition des tuiles")

    def _toggle_cards_edit_mode(self) -> None:
        self.cards_edit_mode = not bool(getattr(self, "cards_edit_mode", False))
        if not self.cards_edit_mode:
            self._save_cards_layout()
        self._apply_cards_edit_ui_state()

    def _apply_cards_edit_ui_state(self) -> None:
        active = bool(getattr(self, "cards_edit_mode", False))
        border_color = "#25A244" if active else self.theme.colors["placeholder_border"]
        try:
            self.btn_cards_edit.configure(highlightthickness=2, highlightbackground=border_color)
        except Exception:
            pass
        try:
            self._set_round_action_pill_state(
                self.btn_cards_add,
                enabled=active and bool(self._hidden_cards),
                border_color=border_color if active else None,
            )
            if active and not self.btn_cards_add.winfo_manager():
                self.btn_cards_add.pack(side=LEFT, padx=(2, 3))
            if (not active) and self.btn_cards_add.winfo_manager():
                self.btn_cards_add.pack_forget()
        except Exception:
            pass
        for key, card_def in self.card_defs.items():
            frame = card_def["frame"]
            clickable = bool(card_def.get("clickable", False))
            remove_btn = card_def.get("remove_btn")
            try:
                frame.configure(
                    cursor="fleur" if active else "",
                    highlightbackground=border_color if active else self.theme.colors["placeholder_border"],
                    highlightthickness=2 if active else 1,
                )
            except Exception:
                continue
            if remove_btn is not None:
                if active and key in self._card_order:
                    try:
                        self._set_round_action_pill_state(
                            remove_btn,
                            enabled=(len(self._card_order) > 1),
                        )
                        remove_btn.place(relx=1.0, x=-5, y=5, anchor="ne")
                    except Exception:
                        pass
                else:
                    try:
                        remove_btn.place_forget()
                    except Exception:
                        pass
            widgets = (frame, *card_def["labels"])
            for widget in widgets:
                widget.unbind("<Enter>")
                widget.unbind("<Leave>")
                widget.unbind("<ButtonPress-1>")
                widget.unbind("<B1-Motion>")
                widget.unbind("<ButtonRelease-1>")
                if active:
                    widget.bind("<ButtonPress-1>", lambda evt, k=key: self._on_card_drag_start(evt, k))
                    widget.bind("<B1-Motion>", self._on_card_drag_motion)
                    widget.bind("<ButtonRelease-1>", self._on_card_drag_end)
                elif clickable:
                    widget.bind("<Enter>", lambda _evt, k=key: self._set_card_hover(k, True))
                    widget.bind("<Leave>", lambda _evt, k=key: self._set_card_hover(k, False))
                    widget.bind("<ButtonPress-1>", lambda _evt, k=key: self._on_card_click(k))
            status_widgets = card_def.get("status_widgets") or {}
            status_bind_items = tuple(status_widgets.items()) if isinstance(status_widgets, dict) else ()
            for wname, st_lbl in status_bind_items:
                st_lbl.unbind("<Enter>")
                st_lbl.unbind("<Leave>")
                st_lbl.unbind("<ButtonPress-1>")
                st_lbl.unbind("<B1-Motion>")
                st_lbl.unbind("<ButtonRelease-1>")
                if active:
                    st_lbl.bind("<ButtonPress-1>", lambda evt, k=key: self._on_card_drag_start(evt, k))
                    st_lbl.bind("<B1-Motion>", self._on_card_drag_motion)
                    st_lbl.bind("<ButtonRelease-1>", self._on_card_drag_end)
                elif clickable:
                    st_lbl.bind("<Enter>", lambda _evt, k=key: self._set_card_hover(k, True))
                    st_lbl.bind("<Leave>", lambda _evt, k=key: self._set_card_hover(k, False))
                    if wname == "val_up":
                        st_lbl.bind("<ButtonPress-1>", lambda _evt, k=key: self._on_status_metric_click(k, "online"))
                    elif wname == "val_down":
                        st_lbl.bind("<ButtonPress-1>", lambda _evt, k=key: self._on_status_metric_click(k, "offline"))
                    else:
                        st_lbl.bind("<ButtonPress-1>", lambda _evt, k=key: self._on_card_click(k))

    def _layout_cards(self) -> None:
        for card_def in self.card_defs.values():
            try:
                card_def["frame"].grid_remove()
            except Exception:
                pass
        for idx, key in enumerate(self._card_order):
            card_def = self.card_defs.get(key)
            if not card_def:
                continue
            row = idx // 4
            col = idx % 4
            card_def["frame"].grid_configure(row=row, column=col)

    def _on_card_drag_start(self, _evt, key: str) -> None:
        if not self.cards_edit_mode:
            return
        self._drag_card_key = str(key)

    def _on_card_drag_motion(self, _evt) -> None:
        return

    def _on_card_drag_end(self, evt) -> None:
        if not self.cards_edit_mode:
            return
        dragged = str(self._drag_card_key or "")
        self._drag_card_key = None
        if not dragged or dragged not in self._card_order:
            return
        target_key = self._card_key_under_pointer(int(evt.x_root), int(evt.y_root))
        if not target_key or target_key == dragged or target_key not in self._card_order:
            return
        old_idx = self._card_order.index(dragged)
        new_idx = self._card_order.index(target_key)
        if old_idx == new_idx:
            return
        self._card_order.pop(old_idx)
        self._card_order.insert(new_idx, dragged)
        self._layout_cards()

    def _remove_card(self, key: str) -> None:
        key = str(key)
        if key not in self._card_order:
            return
        if len(self._card_order) <= 1:
            return
        self._card_order = [k for k in self._card_order if k != key]
        self._hidden_cards.add(key)
        self._layout_cards()
        self._apply_cards_edit_ui_state()

    def _add_card(self, key: str) -> None:
        key = str(key)
        if key not in self.card_defs or key in self._card_order:
            return
        self._hidden_cards.discard(key)
        self._card_order.append(key)
        self._layout_cards()
        self._apply_cards_edit_ui_state()

    def _on_add_card_click(self) -> None:
        if not bool(getattr(self, "cards_edit_mode", False)):
            return
        hidden = [k for k in self.card_defs.keys() if k in self._hidden_cards]
        if not hidden:
            return
        menu = Menu(self.root, tearoff=0)
        for key in hidden:
            title = str(self.card_defs.get(key, {}).get("title", key))
            menu.add_command(label=f"+ {title}", command=lambda k=key: self._add_card(k))
        try:
            x = self.btn_cards_add.winfo_rootx()
            y = self.btn_cards_add.winfo_rooty() + self.btn_cards_add.winfo_height()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _card_key_under_pointer(self, x_root: int, y_root: int) -> str | None:
        target = self.root.winfo_containing(x_root, y_root)
        while target is not None:
            for key, card_def in self.card_defs.items():
                if target == card_def["frame"]:
                    return key
            target = target.master
        return None

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
        has_status_row = key.endswith("_status") or key == "all_total"
        card_height = 92 if has_status_row else 72

        card = Frame(
            parent,
            bg=base_bg,
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.theme.colors["placeholder_border"],
            padx=8,
            pady=3,
            height=card_height,
        )
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=3)
        # Les widgets internes utilisent pack; il faut donc figer via pack_propagate
        # pour eviter les variations de hauteur et les sauts de layout.
        card.pack_propagate(False)

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
        status_widgets: dict | None = None
        if key.endswith("_status") or key == "all_total":
            status_row = Frame(card, bg=base_bg)
            status_row.pack(anchor="w", pady=(1, 0))
            lbl_up = Label(
                status_row,
                text="En ligne:",
                bg=base_bg,
                fg=self.theme.colors["text_muted"],
                font=("Segoe UI", 8),
                cursor="hand2" if clickable else "arrow",
            )
            lbl_up.pack(side=LEFT, padx=(0, 3))
            status_up = Label(
                status_row,
                text="-",
                bg=base_bg,
                fg="#16a34a",
                font=("Segoe UI", 8, "bold"),
                cursor="hand2" if clickable else "arrow",
            )
            status_up.pack(side=LEFT, padx=(0, 8))
            lbl_down = Label(
                status_row,
                text="Hors ligne:",
                bg=base_bg,
                fg=self.theme.colors["text_muted"],
                font=("Segoe UI", 8),
                cursor="hand2" if clickable else "arrow",
            )
            lbl_down.pack(side=LEFT, padx=(0, 3))
            status_down = Label(
                status_row,
                text="-",
                bg=base_bg,
                fg="#dc2626",
                font=("Segoe UI", 8, "bold"),
                cursor="hand2" if clickable else "arrow",
            )
            status_down.pack(side=LEFT)
            status_widgets = {
                "row": status_row,
                "lbl_up": lbl_up,
                "val_up": status_up,
                "lbl_down": lbl_down,
                "val_down": status_down,
            }

        btn_remove = self._create_round_action_pill(
            card,
            symbol="\u2212",
            size=20,
            command=lambda k=key: self._remove_card(k),
            fill="#E2E8F0",
            hover_fill="#CBD5E1",
            text_color="#334155",
            disabled_fill="#F1F5F9",
            disabled_text="#94A3B8",
            container_bg=base_bg,
        )
        btn_remove.place_forget()

        self.card_values[key] = val
        self.card_subs[key] = sub
        self.card_defs[key] = {
            "frame": card,
            "labels": (title_lbl, val, sub),
            "status_widgets": status_widgets,
            "base_bg": base_bg,
            "hover_bg": hover_bg,
            "clickable": clickable,
            "title": title,
            "remove_btn": btn_remove,
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
        status_widgets = card_def.get("status_widgets") or {}
        if isinstance(status_widgets, dict):
            for wname, st_lbl in status_widgets.items():
                st_lbl.bind("<Enter>", lambda _evt, k=key: self._set_card_hover(k, True))
                st_lbl.bind("<Leave>", lambda _evt, k=key: self._set_card_hover(k, False))
                if wname == "val_up":
                    st_lbl.bind("<Button-1>", lambda _evt, k=key: self._on_status_metric_click(k, "online"))
                elif wname == "val_down":
                    st_lbl.bind("<Button-1>", lambda _evt, k=key: self._on_status_metric_click(k, "offline"))
                else:
                    st_lbl.bind("<Button-1>", lambda _evt, k=key: self._on_card_click(k))

    def _set_card_hover(self, key: str, hovered: bool) -> None:
        card_def = self.card_defs.get(key)
        if not card_def:
            return
        if not hovered and self._is_pointer_inside_card(key):
            return
        bg = card_def["hover_bg"] if hovered else card_def["base_bg"]
        border = self.theme.colors["nav_active_bg"] if hovered else self.theme.colors["placeholder_border"]
        card_def["frame"].config(bg=bg, relief="flat", bd=0, highlightbackground=border)
        for lbl in card_def["labels"]:
            lbl.config(bg=bg)
        status_widgets = card_def.get("status_widgets") or {}
        if isinstance(status_widgets, dict):
            for st_lbl in status_widgets.values():
                st_lbl.config(bg=bg)
        remove_btn = card_def.get("remove_btn")
        if remove_btn is not None:
            self._set_round_action_pill_container_bg(remove_btn, bg)

    def _is_pointer_inside_card(self, key: str) -> bool:
        card_def = self.card_defs.get(key)
        if not card_def:
            return False
        frame = card_def.get("frame")
        if frame is None:
            return False
        try:
            x_root, y_root = self.root.winfo_pointerxy()
            target = self.root.winfo_containing(x_root, y_root)
            while target is not None:
                if target == frame:
                    return True
                target = getattr(target, "master", None)
        except Exception:
            return False
        return False

    def _on_card_click(self, key: str) -> None:
        if bool(getattr(self, "cards_edit_mode", False)):
            return
        action = self.card_click_actions.get(key)
        if action:
            action()

    def _on_status_metric_click(self, key: str, status: str) -> None:
        if bool(getattr(self, "cards_edit_mode", False)):
            return
        if key == "all_total":
            self._show_global_filtered(status)
            return
        if key.endswith("_status"):
            dtype = key[: -len("_status")]
            if dtype in self.type_views:
                self._show_type_filtered(dtype, status)

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
            text="Cliquez sur un monitoring de type ou sur Demarrer Global.",
            bg=self.theme.colors["placeholder_bg"],
            fg=self.theme.colors["text_muted"],
            font=("Segoe UI", 10),
        )
        self.dashboard_placeholder_subtitle.pack()
        self._refresh_dashboard_watermark()

        self.global_detail_frame = Frame(self.detail_container, bg=self.theme.colors["app_bg"])
        self.type_detail_frames: dict[str, Frame] = {}
        self.type_views: dict[str, TypeDevicesView] = {}
        for dtype in self._ordered_type_codes():
            frame = Frame(self.detail_container, bg=self.theme.colors["app_bg"])
            view = TypeDevicesView(
                frame,
                device_type_code=dtype,
                type_label=str(self.model.type_definitions.get(dtype, {}).get("label", dtype)),
                model=self.model,
                controller=self.controller,
            )
            view.pack(fill=BOTH, expand=True)
            self.type_detail_frames[dtype] = frame
            self.type_views[dtype] = view

        self.consolidated_app = ConsolidatedView(
            self.global_detail_frame,
            model=self.model,
            controller=self.controller,
        )
        self.consolidated_app.pack(fill=BOTH, expand=True)

    def _hide_details(self) -> None:
        self.placeholder.pack_forget()
        for frame in self.type_detail_frames.values():
            frame.pack_forget()
        self.global_detail_frame.pack_forget()

    def _show_dashboard(self) -> None:
        running_types = [dtype for dtype in self._monitored_type_codes() if bool(self.model.do_run.get(dtype, False))]
        if len(running_types) > 1:
            self._show_global_embedded()
            return
        if len(running_types) == 1:
            self._show_type_embedded(running_types[0])
            return

        self._show_summary_panels()
        self._hide_details()
        self.placeholder.pack(fill=BOTH, expand=True, pady=20)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()

    def _show_type_detail(self, dtype: str) -> None:
        view = self.type_views.get(dtype)
        frame = self.type_detail_frames.get(dtype)
        if view is None or frame is None:
            return
        self._hide_summary_panels()
        self._hide_details()
        view.set_local_monitoring_button_visible(True)
        view.set_force_inventory_visible(True)
        frame.pack(fill=BOTH, expand=True)
        self.current_detail = dtype
        self.active_tree_filter = None
        self._update_nav_buttons()
        view.update_display()

    def _show_global_detail(self) -> None:
        self._hide_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(True)
        self.consolidated_app.set_force_inventory_visible(True)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "global"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.consolidated_app.update_display()

    def _show_type_filtered(self, dtype: str, status: str | None) -> None:
        view = self.type_views.get(dtype)
        frame = self.type_detail_frames.get(dtype)
        if view is None or frame is None:
            return
        self._show_summary_panels()
        self._hide_details()
        view.set_local_monitoring_button_visible(False)
        view.set_force_inventory_visible(status is None)
        frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = (dtype, status)
        self._update_nav_buttons()
        view.update_display()
        self._apply_active_tree_filter()

    def _show_global_filtered(self, status: str | None = None) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(False)
        self.consolidated_app.set_force_inventory_visible(status is None)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = ("global", status)
        self._update_nav_buttons()
        self.consolidated_app.update_display()
        self._apply_active_tree_filter()

    def _show_type_embedded(self, dtype: str) -> None:
        view = self.type_views.get(dtype)
        frame = self.type_detail_frames.get(dtype)
        if view is None or frame is None:
            return
        self._show_summary_panels()
        self._hide_details()
        view.set_local_monitoring_button_visible(False)
        view.set_force_inventory_visible(False)
        frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()
        view.update_display()

    def _show_global_embedded(self) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(False)
        self.consolidated_app.set_force_inventory_visible(False)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.consolidated_app.update_display()

    def _apply_active_tree_filter(self) -> None:
        if not self.active_tree_filter:
            return

        target, status_filter = self.active_tree_filter
        if target in self.type_views:
            self._filter_tree(self.type_views[target].tree, self.model.device_data.get(target, {}), status_filter)
            return
        if target == "global":
            self._filter_consolidated_tree(self.consolidated_app.tree, self.model.device_data, status_filter)

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

    @staticmethod
    def _filter_consolidated_tree(tree, devices_by_type: dict, status_filter: str | None) -> None:
        for dtype, devices in devices_by_type.items():
            for did, dev in devices.items():
                iid = f"{dtype}::{did}"
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
            *[(dtype, btn) for dtype, btn in self.type_nav_buttons.items()],
            ("global", self.btn_global),
        ):
            btn.config(
                bg=active if self.current_detail == name else base,
                fg=fg,
                relief="sunken" if self.current_detail == name else "raised",
            )

    def _toggle_monitoring_target(self, target: str) -> None:
        self.controller.view = self
        if target in self.type_views:
            self._show_type_embedded(target)
        if target == "global":
            self._show_global_embedded()

        if target == "global":
            if any(self.model.do_run.values()):
                self.controller.stop_all_monitoring()
            else:
                for dtype in self._monitored_type_codes():
                    self.controller.start_monitoring(dtype)
            self.update_display()
            return

        if target in self.type_views:
            if self.model.do_run.get(target, False):
                self.controller.stop_monitoring(target)
            else:
                self.controller.start_monitoring(target)
        self.update_display()

    def update_display(self) -> None:
        totals: dict[str, int] = {}
        ups: dict[str, int] = {}
        downs: dict[str, int] = {}
        for dtype in self._ordered_type_codes():
            devices = list(self.model.device_data.get(dtype, {}).values())
            total = len(devices)
            up = sum(1 for d in devices if getattr(d, "status", "") == "online")
            down = max(total - up, 0)
            totals[dtype] = total
            ups[dtype] = up
            downs[dtype] = down
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            self.card_values[f"{dtype}_status"].config(text=str(total), fg=self.theme.colors.get("kpi_total_accent", self.theme.colors["text_secondary"]))
            self.card_subs[f"{dtype}_status"].config(text=f"Inventaire {label.lower()}")
            running = bool(self.model.do_run.get(dtype, False))
            status_widgets = self.card_defs.get(f"{dtype}_status", {}).get("status_widgets") or {}
            if isinstance(status_widgets, dict):
                lbl_up = status_widgets.get("lbl_up")
                val_up = status_widgets.get("val_up")
                lbl_down = status_widgets.get("lbl_down")
                val_down = status_widgets.get("val_down")
                if running:
                    if lbl_up is not None:
                        lbl_up.config(text="En ligne:", fg=self.theme.colors["text_muted"])
                    if lbl_down is not None:
                        lbl_down.config(text="Hors ligne:", fg=self.theme.colors["text_muted"])
                    if val_up is not None:
                        val_up.config(text=str(up), fg="#16a34a")
                    if val_down is not None:
                        val_down.config(text=str(down), fg="#dc2626")
                else:
                    if lbl_up is not None:
                        lbl_up.config(text="", fg=self.theme.colors["text_muted"])
                    if lbl_down is not None:
                        lbl_down.config(text="", fg=self.theme.colors["text_muted"])
                    if val_up is not None:
                        val_up.config(text="", fg=self.theme.colors["text_muted"])
                    if val_down is not None:
                        val_down.config(text="", fg=self.theme.colors["text_muted"])

        all_total = sum(totals.values())
        monitored = self._monitored_type_codes()
        running_any = any(bool(self.model.do_run.get(dtype, False)) for dtype in monitored)
        running_all = bool(monitored) and all(bool(self.model.do_run.get(dtype, False)) for dtype in monitored)
        visible_up = sum(ups.values())
        visible_down = sum(downs[dtype] for dtype in monitored if bool(self.model.do_run.get(dtype, False)))
        self.card_values["all_total"].config(text=str(all_total))
        self.card_subs["all_total"].config(text="Inventaire global")
        all_status_widgets = self.card_defs.get("all_total", {}).get("status_widgets") or {}
        if isinstance(all_status_widgets, dict):
            all_lbl_up = all_status_widgets.get("lbl_up")
            all_val_up = all_status_widgets.get("val_up")
            all_lbl_down = all_status_widgets.get("lbl_down")
            all_val_down = all_status_widgets.get("val_down")
            if running_any:
                if all_lbl_up is not None:
                    all_lbl_up.config(text="En ligne:", fg=self.theme.colors["text_muted"])
                if all_lbl_down is not None:
                    all_lbl_down.config(text="Hors ligne:", fg=self.theme.colors["text_muted"])
                if all_val_up is not None:
                    all_val_up.config(text=str(visible_up), fg="#16a34a")
                if all_val_down is not None:
                    all_val_down.config(text=str(visible_down), fg="#dc2626")
            else:
                if all_lbl_up is not None:
                    all_lbl_up.config(text="", fg=self.theme.colors["text_muted"])
                if all_lbl_down is not None:
                    all_lbl_down.config(text="", fg=self.theme.colors["text_muted"])
                if all_val_up is not None:
                    all_val_up.config(text="", fg=self.theme.colors["text_muted"])
                if all_val_down is not None:
                    all_val_down.config(text="", fg=self.theme.colors["text_muted"])
        state = "Global" if running_all else ("Partiel" if running_any else "Arrete")
        self.card_values["monitoring_state"].config(text=state)
        self.card_subs["monitoring_state"].config(text="Etat des sondes")

        self._update_monitoring_buttons()
        self._apply_active_tree_filter()

    def _update_monitoring_buttons(self) -> None:
        monitored = self._monitored_type_codes()
        for dtype, btn in self.type_monitor_buttons.items():
            running = bool(self.model.do_run.get(dtype, False))
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            btn.config(
                bg=self.theme.colors["button_active_bg"] if running else self.theme.colors["button_inactive_bg"],
                fg=self.theme.colors["button_active_fg"] if running else self.theme.colors["button_inactive_fg"],
                text=f"Monitoring {label}",
            )
        running_any = any(bool(self.model.do_run.get(dtype, False)) for dtype in monitored)
        running_global = bool(monitored) and all(bool(self.model.do_run.get(dtype, False)) for dtype in monitored)
        self.btn_mon_global.config(
            bg=self.theme.colors["button_global_bg"] if running_global else self.theme.colors["button_inactive_bg"],
            fg=self.theme.colors["button_active_fg"] if running_global else self.theme.colors["button_inactive_fg"],
            text="Monitoring Globale",
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
            getattr(self, "global_detail_frame", None),
        ):
            if widget is not None:
                try:
                    widget.configure(bg=c["app_bg"])
                except Exception:
                    pass
        for frame in getattr(self, "type_detail_frames", {}).values():
            try:
                frame.configure(bg=c["app_bg"])
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
            status_widgets = card_def.get("status_widgets") or {}
            try:
                frame.configure(bg=c["panel_bg"])
                labels[0].configure(bg=c["panel_bg"], fg=c["text_secondary"])
                labels[2].configure(bg=c["panel_bg"], fg=c["text_muted"])
                if isinstance(status_widgets, dict):
                    for st_lbl in status_widgets.values():
                        st_lbl.configure(bg=c["panel_bg"])
                if key.endswith("_status"):
                    labels[1].configure(fg=c.get("kpi_total_accent", c["text_secondary"]))
                    if isinstance(status_widgets, dict):
                        if status_widgets.get("lbl_up") is not None:
                            status_widgets["lbl_up"].configure(fg=c["text_muted"])
                        if status_widgets.get("lbl_down") is not None:
                            status_widgets["lbl_down"].configure(fg=c["text_muted"])
                        if status_widgets.get("val_up") is not None:
                            status_widgets["val_up"].configure(fg="#16a34a")
                        if status_widgets.get("val_down") is not None:
                            status_widgets["val_down"].configure(fg="#dc2626")
                elif key.endswith("_total") and key != "all_total":
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

        self._update_nav_buttons()
        self._update_monitoring_buttons()
        self._refresh_dashboard_watermark()

        for view in [*getattr(self, "type_views", {}).values(), getattr(self, "consolidated_app", None)]:
            if view is None:
                continue
            try:
                if hasattr(view, "apply_theme"):
                    view.apply_theme(self.theme.key)
                elif hasattr(view, "update_display"):
                    view.update_display()
            except Exception:
                continue
        try:
            self.btn_cards_edit.configure(
                bg=c["surface_bg"],
                fg=c["text_primary"],
                activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                activeforeground=c.get("control_hover_fg", c["text_primary"]),
            )
            self._set_round_action_pill_container_bg(self.btn_cards_add, c["surface_bg"])
        except Exception:
            pass
        self._apply_cards_edit_ui_state()

    def _open_update_settings_dialog(self) -> None:
        from monitoring.ui.dialogs.update_settings import UpdateSettingsDialog

        dlg = UpdateSettingsDialog(self.root, self.notification_settings)
        if dlg.result:
            self.notification_settings = dlg.result
            save_settings(self.notification_settings)
            # UX attendu: apres validation des parametres MAJ, proposer une verification immediate.
            if bool(getattr(self.notification_settings, "updates_enabled", False)):
                self._check_updates_now_interactive()

    def _check_updates_now_interactive(self) -> None:
        def worker() -> None:
            try:
                info = find_available_update(self.app_version, self.notification_settings)
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Mise a jour", f"Verification impossible: {exc}"))
                return
            if info is None:
                self.root.after(0, lambda: messagebox.showinfo("Mise a jour", "Aucune mise a jour disponible."))
                return
            self.root.after(0, lambda: self._prompt_install_update(info))

        threading.Thread(target=worker, daemon=True, name="UpdateCheckManual").start()

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
        for view in [*getattr(self, "type_views", {}).values(), getattr(self, "consolidated_app", None)]:
            if view is None:
                continue
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
        self._show_update_progress("Telechargement de la mise a jour en cours...")

        def worker() -> None:
            try:
                setup_path = download_update_asset(info, self.notification_settings)
            except Exception as exc:
                self.root.after(
                    0,
                    lambda: (
                        self._close_update_progress(),
                        messagebox.showerror("Mise a jour", f"Telechargement impossible: {exc}"),
                    ),
                )
                return
            self.root.after(
                0,
                lambda: (
                    self._close_update_progress(),
                    self._run_installer_and_exit(setup_path),
                ),
            )

        threading.Thread(target=worker, daemon=True, name="UpdateDownload").start()

    def _show_update_progress(self, message: str) -> None:
        try:
            if getattr(self, "_update_progress_win", None) is not None:
                self._close_update_progress()
            progress_win = Toplevel(self.root)
            progress_win.title("Mise a jour")
            progress_win.transient(self.root)
            progress_win.grab_set()
            progress_win.resizable(False, False)
            progress_win.configure(bg=self.theme.colors["app_bg"])
            Label(
                progress_win,
                text=message,
                bg=self.theme.colors["app_bg"],
                fg=self.theme.colors["text_primary"],
            ).pack(padx=16, pady=(14, 8))
            bar = ttk.Progressbar(progress_win, mode="indeterminate", length=280)
            bar.pack(padx=16, pady=(0, 14))
            bar.start(12)
            self._update_progress_win = progress_win
            self._update_progress_bar = bar
            try:
                progress_win.update_idletasks()
                w = progress_win.winfo_width()
                h = progress_win.winfo_height()
                x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (w // 2)
                y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (h // 2)
                progress_win.geometry(f"+{max(0, x)}+{max(0, y)}")
            except Exception:
                pass
        except Exception:
            self._update_progress_win = None
            self._update_progress_bar = None

    def _close_update_progress(self) -> None:
        bar = getattr(self, "_update_progress_bar", None)
        win = getattr(self, "_update_progress_win", None)
        try:
            if bar is not None:
                bar.stop()
        except Exception:
            pass
        try:
            if win is not None and win.winfo_exists():
                win.grab_release()
                win.destroy()
        except Exception:
            pass
        self._update_progress_bar = None
        self._update_progress_win = None

    def _run_installer_and_exit(self, setup_path: str) -> None:
        # Lance un helper externe qui attend la fin du process courant avant
        # de demarrer l'installateur: evite toute collision fichiers/verrous.
        try:
            pid = int(os.getpid())
            exe_path = str(setup_path).replace("'", "''")
            ps_script = (
                f"$pidToWait={pid}; "
                "while (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) "
                "{ Start-Sleep -Milliseconds 300 }; "
                f"Start-Process -FilePath '{exe_path}'"
            )
            creation_flags = 0
            creation_flags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
            creation_flags |= int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps_script,
                ],
                shell=False,
                creationflags=creation_flags,
            )
        except Exception as exc:
            messagebox.showerror("Mise a jour", f"Impossible de preparer l'installation: {exc}")
            return
        self._on_closing()

    def _open_about_dialog(self) -> None:
        messagebox.showinfo(
            "A propos",
            f"NetworkMonitoringProject\nVersion: {self.app_version}",
        )

    def _on_switch_select(self, _evt) -> None:
        return

    def _on_server_select(self, _evt) -> None:
        return

    def _on_closing(self) -> None:
        try:
            self.controller.stop_all_monitoring()
        finally:
            self.root.destroy()

