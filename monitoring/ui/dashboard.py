# src/monitoring/ui/dashboard.py

from __future__ import annotations

import logging
import shutil
import threading
import webbrowser
from pathlib import Path
from tkinter import LEFT, RIGHT, TOP, X, Button, Canvas, Frame, Label, StringVar, Tk, messagebox
from tkinter import ttk

from monitoring.config.settings import NotificationSettings, load_settings, save_settings
from monitoring.api.app import create_app
from monitoring.backend.app_backend import ApplicationBackend
from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.services.caddy_manager import CaddyManager
from monitoring.services.web_server_manager import WebServerManager
from monitoring.ui.base_window import BaseWindow
from monitoring.ui.dialogs.config_storage_settings import ConfigStorageSettingsDialog
from monitoring.ui.dialogs.device_types_settings import DeviceTypesSettingsDialog
from monitoring.ui.dashboard_menu_mixin import DashboardMenuMixin
from monitoring.ui.dashboard_cards_mixin import DashboardCardsMixin
from monitoring.ui.dashboard_detail_mixin import DashboardDetailMixin
from monitoring.ui.dashboard_theme_mixin import DashboardThemeMixin
from monitoring.ui.dashboard_update_mixin import DashboardUpdateMixin
from monitoring.ui.dashboard_watermark_mixin import DashboardWatermarkMixin
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import bind_blue_hover
from monitoring.utils.config_files import find_switch_config_files, open_path_with_default_app

try:
    from monitoring import __version__ as APP_VERSION
except Exception:
    try:
        from __init__ import __version__ as APP_VERSION
    except Exception:
        APP_VERSION = "unknown"


class DashboardIHM(
    DashboardMenuMixin,
    DashboardCardsMixin,
    DashboardDetailMixin,
    DashboardThemeMixin,
    DashboardUpdateMixin,
    DashboardWatermarkMixin,
    BaseWindow,
):
    """Fenetre principale: dashboard tuiles + vues detaillees a la demande."""

    def __init__(
        self,
        root: Tk,
        *,
        model: DevicesModel,
        controller: AppController,
        backend: ApplicationBackend | None = None,
    ) -> None:
        self.app_version = APP_VERSION
        super().__init__(root, title=f"Tableau de bord Monitoring v{self.app_version}")
        self.logger = logging.getLogger(__name__)

        self.model = model
        self.controller = controller
        self.backend = backend

        self.current_detail = "dashboard"
        self.active_tree_filter: tuple[str, str | None] | None = None
        self.notification_settings: NotificationSettings = load_settings()
        self.config_storage = ConfigStorageService(settings_provider=lambda: self.notification_settings)
        self.caddy_manager = CaddyManager()
        self.web_server_manager = WebServerManager(
            app_factory=(
                lambda: create_app(backend=self.backend, stop_runtime_on_shutdown=False)
            ) if self.backend is not None else None
        )
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
        self.controller.register_view(self)
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
        self._maybe_sync_public_web_proxy()
        self._maybe_autostart_web_server()
        self.root.after(150, lambda: self._apply_window_chrome_theme(self.theme.key == "dark"))
        self.root.after(1800, self._check_updates_on_startup)
        self.root.after(2800, self._schedule_config_auto_sync)

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

        btn_supervision = Button(
            menu_frame,
            text="Supervision",
            bg=c["menu_bg"],
            fg=c["menu_fg"],
            activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
            activeforeground=c.get("control_hover_fg", c["text_primary"]),
            relief="flat",
            bd=0,
            padx=10,
            pady=3,
            command=lambda: self._popup_custom_menu(btn_supervision, self._supervision_menu_items()),
        )
        btn_supervision.pack(side=LEFT, padx=(4, 0))
        btn_inventory = Button(
            menu_frame,
            text="Equipements",
            bg=c["menu_bg"],
            fg=c["menu_fg"],
            activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
            activeforeground=c.get("control_hover_fg", c["text_primary"]),
            relief="flat",
            bd=0,
            padx=10,
            pady=3,
            command=lambda: self._popup_custom_menu(btn_inventory, self._inventory_menu_items()),
        )
        btn_inventory.pack(side=LEFT, padx=(2, 0))
        btn_display = Button(
            menu_frame,
            text="Affichage",
            bg=c["menu_bg"],
            fg=c["menu_fg"],
            activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
            activeforeground=c.get("control_hover_fg", c["text_primary"]),
            relief="flat",
            bd=0,
            padx=10,
            pady=3,
            command=lambda: self._popup_custom_menu(btn_display, self._display_menu_items()),
        )
        btn_display.pack(side=LEFT, padx=(2, 0))
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
        self.menu_buttons = [btn_supervision, btn_inventory, btn_display, btn_help]
        self._menu_popups: list[Frame] = []
        self._submenu_anchor_by_level: dict[int, str] = {}
        self._menu_outside_click_bind = None

    def _supervision_menu_items(self) -> list[tuple[str, object]]:
        return [
            ("Notifications (email + popup)...", self._open_notification_dialog),
            ("Parametres de monitoring...", self._open_monitoring_dialog),
            ("Serveur web...", self._open_web_server_dialog),
            ("Journaux", self._logs_menu_items()),
            ("Mises a jour...", self._open_update_settings_dialog),
        ]

    def _inventory_menu_items(self) -> list[tuple[str, object]]:
        return [
            ("Types d'equipements...", self._open_device_types_settings),
            (
                "Fichiers de configuration",
                [
                    ("Configurer sauvegarde...", self._open_config_storage_settings_dialog),
                    ("Ouvrir le dossier de sauvegarde", self._open_switch_configs_root),
                    ("Sauvegarder maintenant", self._run_config_sync_now_interactive),
                ],
            ),
        ]

    def _display_menu_items(self) -> list[tuple[str, object]]:
        return [
            (
                "Theme",
                [
                    ("Clair", lambda: self._set_theme_from_menu("light")),
                    ("Sombre", lambda: self._set_theme_from_menu("dark")),
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
        ]

    def _logs_menu_items(self) -> list[tuple[str, object]]:
        items: list[tuple[str, object]] = [("Journal global des changements...", self._open_global_status_logs)]
        for dtype in self._ordered_type_codes():
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            items.append((f"Journal {label}...", lambda dt=dtype: self._open_status_logs_by_type(dt)))
        return items

    def _help_menu_items(self) -> list[tuple[str, object]]:
        return [("A propos...", self._open_about_dialog)]

    def _switch_configs_root_dir(self) -> Path:
        return self.config_storage.backup_root_dir()

    def _open_switch_configs_root(self) -> None:
        root_dir = self._switch_configs_root_dir()
        if str(getattr(self.notification_settings, "config_storage_mode", "local") or "local").strip().lower() != "smb3":
            root_dir.mkdir(parents=True, exist_ok=True)
        try:
            open_path_with_default_app(root_dir)
        except Exception as exc:
            messagebox.showerror("Fichiers de configuration", f"Impossible d'ouvrir le dossier de sauvegarde: {exc}")

    def _open_config_storage_settings_dialog(self) -> None:
        dlg = ConfigStorageSettingsDialog(self.root, self.notification_settings)
        if not dlg.result:
            return
        self.notification_settings = dlg.result
        save_settings(self.notification_settings)

    def _open_device_types_settings(self) -> None:
        DeviceTypesSettingsDialog(self.root, on_changed=self._on_device_types_changed)

    def _on_device_types_changed(self) -> None:
        try:
            self.model.refresh_type_definitions()
            self._rebuild_dynamic_sections()
            self.controller.refresh_views()
        except Exception:
            self.logger.exception("Erreur rafraichissement types de devices")

    def _run_config_sync_now_interactive(self) -> None:
        self._run_config_sync_now(manual_feedback=True)

    def _run_config_sync_now(self, *, manual_feedback: bool) -> None:
        def worker() -> None:
            ok, info = self.config_storage.ensure_backup_connection()
            if not ok:
                if manual_feedback:
                    self.root.after(0, lambda: messagebox.showerror("Sauvegarde", f"Connexion dossier de sauvegarde impossible: {info}"))
                return
            stats = self.config_storage.sync_local_versions_to_backup()
            total_scanned = int(stats.scanned)
            total_copied = int(stats.copied)
            if manual_feedback:
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Sauvegarde",
                        f"Termine.\nVersions locales analysees: {total_scanned}\nFichiers sauvegardes: {total_copied}",
                    ),
                )

        threading.Thread(target=worker, daemon=True, name="ConfigSyncNow").start()

    def _schedule_config_auto_sync(self) -> None:
        enabled = bool(getattr(self.notification_settings, "config_auto_sync_enabled", False))
        interval = max(
            5,
            int(getattr(self.notification_settings, "config_auto_sync_interval_seconds", 3600) or 3600),
        )
        if enabled:
            self._run_config_sync_now(manual_feedback=False)
        self.root.after(interval * 1000, self._schedule_config_auto_sync)

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
                f"Aucune sauvegarde trouvee pour {dev.name} ({dev.ip}).\nDossier scanne: {root_dir}",
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
    def update_display(self) -> None:
        if not all(
            hasattr(self, attr)
            for attr in ("card_values", "card_subs", "card_defs", "btn_mon_global", "type_monitor_buttons")
        ):
            return
        totals: dict[str, int] = {}
        ups: dict[str, int] = {}
        downs: dict[str, int] = {}
        for dtype in self._ordered_type_codes():
            devices = list(self.model.device_data.get(dtype, {}).values())
            total = len(devices)
            up = sum(1 for d in devices if str(getattr(d, "status", "")).strip().lower() == "online")
            down = sum(1 for d in devices if str(getattr(d, "status", "")).strip().lower() == "offline")
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
        visible_up = sum(ups[dtype] for dtype in monitored if bool(self.model.do_run.get(dtype, False)))
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
        if hasattr(self, "web_server_manager") and "web_server_state" in self.card_values:
            web_state = self.web_server_manager.state()
            self.card_values["web_server_state"].config(
                text="Actif" if web_state.running else "Arrete",
                fg="#16a34a" if web_state.running else "#dc2626",
            )
            self.card_subs["web_server_state"].config(text=f"{web_state.host}:{web_state.port}")
            web_action_btn = self.card_defs.get("web_server_state", {}).get("action_button")
            if web_action_btn is not None:
                web_action_btn.config(
                    text="Arreter" if web_state.running else "Demarrer",
                    bg=self.theme.colors["button_active_bg"] if web_state.running else self.theme.colors["button_inactive_bg"],
                    fg=self.theme.colors["button_active_fg"] if web_state.running else self.theme.colors["button_inactive_fg"],
                )

        self._update_monitoring_buttons()
        if (
            getattr(self, "current_detail", "dashboard") == "dashboard"
            and not getattr(self, "active_tree_filter", None)
            and hasattr(self, "_show_dashboard")
        ):
            self._show_dashboard()
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

    def _open_global_status_logs(self) -> None:
        from monitoring.ui.dialogs.status_logs_viewer import StatusLogsViewer

        StatusLogsViewer(
            self.root,
            title="Journal global des changements de statut",
            manager=self.model.manager,
        )

    def _open_status_logs_by_type(self, dtype: str) -> None:
        from monitoring.ui.dialogs.status_logs_viewer import StatusLogsViewer

        StatusLogsViewer(
            self.root,
            title=f"Journal des changements - {dtype}",
            dtype=dtype,
            manager=self.model.manager,
        )

    def _open_about_dialog(self) -> None:
        messagebox.showinfo(
            "A propos",
            f"NetworkMonitoringProject\nVersion: {self.app_version}",
        )

    def _web_server_url(self) -> str:
        host = str(getattr(self.notification_settings, "web_server_host", "127.0.0.1") or "127.0.0.1").strip()
        port = max(1, int(getattr(self.notification_settings, "web_server_port", 8000) or 8000))
        return f"http://{host}:{port}/"

    def _web_server_public_url(self) -> str:
        return str(getattr(self.notification_settings, "web_server_public_url", "") or "").strip().rstrip("/")

    def _preferred_web_server_url(self) -> str:
        public_url = self._web_server_public_url()
        if bool(getattr(self.notification_settings, "web_server_use_public_url", False)) and public_url:
            return f"{public_url}/"
        return self._web_server_url()

    def _maybe_autostart_web_server(self) -> None:
        if bool(getattr(self.notification_settings, "web_server_autostart", False)):
            self.root.after(300, self._start_web_server_silent)

    def _maybe_sync_public_web_proxy(self) -> None:
        if not bool(getattr(self.notification_settings, "web_server_use_public_url", False)):
            return
        if not self._web_server_public_url():
            return

        def worker() -> None:
            try:
                self.caddy_manager.sync_from_settings(self.notification_settings)
            except Exception as exc:
                self.root.after(
                    0,
                    lambda e=exc: messagebox.showerror(
                        "Proxy HTTPS",
                        f"Impossible de synchroniser le proxy public: {e}",
                    ),
                )

        threading.Thread(target=worker, daemon=True, name="CaddySync").start()

    def _open_web_server_dialog(self) -> None:
        from monitoring.ui.dialogs.web_server_settings import WebServerSettingsDialog

        WebServerSettingsDialog(
            self.root,
            host=str(getattr(self.notification_settings, "web_server_host", "127.0.0.1")),
            port=int(getattr(self.notification_settings, "web_server_port", 8000)),
            autostart=bool(getattr(self.notification_settings, "web_server_autostart", False)),
            public_url=self._web_server_public_url(),
            use_public_url=bool(getattr(self.notification_settings, "web_server_use_public_url", False)),
            state_provider=self.web_server_manager.state,
            on_save=self._save_web_server_settings,
            on_toggle=self._toggle_web_server_dialog_action,
            on_restart=self._restart_web_server_dialog_action,
            on_open_browser=self._open_web_ui_for_host_port,
        )

    def _save_web_server_settings(
        self,
        host: str,
        port: int,
        autostart: bool,
        public_url: str = "",
        use_public_url: bool = False,
    ) -> None:
        self.notification_settings.web_server_host = str(host)
        self.notification_settings.web_server_port = int(port)
        self.notification_settings.web_server_autostart = bool(autostart)
        self.notification_settings.web_server_public_url = str(public_url or "").strip().rstrip("/")
        self.notification_settings.web_server_use_public_url = bool(use_public_url)
        save_settings(self.notification_settings)
        self.caddy_manager.sync_from_settings(self.notification_settings)
        self.update_display()

    def _start_web_server(self, *, show_feedback: bool, open_browser: bool = False) -> None:
        self._run_web_server_operation(
            lambda: self.web_server_manager.start(
                host=str(getattr(self.notification_settings, "web_server_host", "127.0.0.1")),
                port=int(getattr(self.notification_settings, "web_server_port", 8000)),
                open_browser=open_browser,
            ),
            success_message="Serveur web actif sur:",
            show_feedback=show_feedback,
        )

    def _start_web_server_silent(self) -> None:
        self._start_web_server(show_feedback=False)

    def _start_web_server_interactive(self) -> None:
        self._start_web_server(show_feedback=True)

    def _stop_web_server_interactive(self) -> None:
        self._run_web_server_operation(
            self.web_server_manager.stop,
            success_message="Serveur web arrete.\nURL:",
            show_feedback=True,
        )

    def _restart_web_server_interactive(self) -> None:
        self._run_web_server_operation(
            lambda: self.web_server_manager.restart(
                host=str(getattr(self.notification_settings, "web_server_host", "127.0.0.1")),
                port=int(getattr(self.notification_settings, "web_server_port", 8000)),
            ),
            success_message="Serveur web redemarre sur:",
            show_feedback=True,
        )

    def _open_web_ui_in_browser(self) -> None:
        if not self.web_server_manager.state().running:
            self._start_web_server(show_feedback=False)
        try:
            webbrowser.open(self._preferred_web_server_url())
        except Exception as exc:
            messagebox.showerror("Serveur web", f"Impossible d'ouvrir le navigateur: {exc}")

    def _open_web_ui_for_host_port(self, host: str, port: int) -> None:
        self._save_web_server_settings(
            host,
            port,
            bool(getattr(self.notification_settings, "web_server_autostart", False)),
            self._web_server_public_url(),
            bool(getattr(self.notification_settings, "web_server_use_public_url", False)),
        )
        if not self.web_server_manager.state().running:
            self._run_web_server_operation(
                lambda: self.web_server_manager.start(host=str(host), port=int(port), open_browser=True),
                show_feedback=False,
            )
            return
        webbrowser.open(self._preferred_web_server_url())

    def _toggle_web_server_dialog_action(self, host: str, port: int) -> None:
        state = self.web_server_manager.state()
        if state.running and (state.host != str(host) or state.port != int(port)):
            self._run_web_server_operation(
                lambda: self.web_server_manager.restart(host=str(host), port=int(port), open_browser=False),
                show_feedback=False,
            )
            return
        if state.running:
            self._run_web_server_operation(self.web_server_manager.stop, show_feedback=False)
            return
        self._run_web_server_operation(
            lambda: self.web_server_manager.start(host=str(host), port=int(port), open_browser=False),
            show_feedback=False,
        )

    def _restart_web_server_dialog_action(self, host: str, port: int) -> None:
        self._run_web_server_operation(
            lambda: self.web_server_manager.restart(host=str(host), port=int(port), open_browser=False),
            show_feedback=False,
        )

    def _toggle_web_server_from_dashboard(self) -> None:
        state = self.web_server_manager.state()
        if state.running:
            self._run_web_server_operation(self.web_server_manager.stop, show_feedback=False)
        else:
            self._run_web_server_operation(
                lambda: self.web_server_manager.start(
                host=str(getattr(self.notification_settings, "web_server_host", "127.0.0.1")),
                port=int(getattr(self.notification_settings, "web_server_port", 8000)),
                open_browser=False,
                ),
                show_feedback=False,
            )

    def _run_web_server_operation(self, operation, *, success_message: str | None = None, show_feedback: bool) -> None:
        def worker() -> None:
            try:
                state = operation()
                self.root.after(0, lambda: self._on_web_server_operation_success(state, success_message, show_feedback))
            except Exception as exc:
                self.root.after(0, lambda e=exc: self._on_web_server_operation_error(e, show_feedback))

        threading.Thread(target=worker, daemon=True, name="WebServerAction").start()

    def _on_web_server_operation_success(self, state, success_message: str | None, show_feedback: bool) -> None:
        self.update_display()
        if show_feedback and success_message:
            public_url = self._web_server_public_url()
            if bool(getattr(self.notification_settings, "web_server_use_public_url", False)) and public_url:
                messagebox.showinfo(
                    "Serveur web",
                    f"{success_message}\nURL publique: {public_url}/\nBackend local: {state.url}",
                )
            else:
                messagebox.showinfo("Serveur web", f"{success_message}\n{state.url}")

    @staticmethod
    def _on_web_server_operation_error(exc: Exception, show_feedback: bool) -> None:
        messagebox.showerror("Serveur web", f"Operation impossible: {exc}")

    def _on_switch_select(self, _evt) -> None:
        return

    def _on_server_select(self, _evt) -> None:
        return

    def _on_closing(self) -> None:
        try:
            self.controller.stop_all_monitoring()
            self.web_server_manager.stop()
        finally:
            self.root.destroy()








