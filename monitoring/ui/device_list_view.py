# src/monitoring/ui/device_list_view.py

from __future__ import annotations

import ipaddress
import logging
import tkinter as tk
from pathlib import Path
from tkinter import (
    Frame,
    Menu,
    PhotoImage,
    Button,
    Label,
    BOTH,
    LEFT,
    RIGHT,
    X,
    simpledialog,
    ttk,
)
from typing import Any, Optional, Sequence

from monitoring.controllers.app_controller import AppController
from monitoring.controllers.network_tools_controller import NetworkToolsController
from monitoring.models.devices_model import DevicesModel
from monitoring.services.device_actions_service import DeviceActionService
from monitoring.services.settings_service import SettingsService
from monitoring.ui.base_window import resource_path
from monitoring.ui.network_tools_actions_mixin import NetworkToolsActionsMixin
from monitoring.ui.style_system import resolve_ui_style_tokens
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import apply_control_button_style, bind_blue_hover
from monitoring.ui.view_mixins import ContextMenuMixin, ThemedViewMixin
from monitoring.ui.utils.sortable_tree import make_treeview_sortable

LOGGER = logging.getLogger(__name__)


class DeviceListView(Frame, NetworkToolsActionsMixin, ContextMenuMixin, ThemedViewMixin):
    """
    Base class pour toutes les vues listant des devices avec flag notify.
    Fournit l'arbre, les icones, le bouton de toggle monitoring et
    le menu contextuel commun.
    """

    default_tag_configs: dict[str, dict[str, Any]] = {
        "online":  {"background": "#d4edda", "foreground": "#155724"},
        "offline": {"background": "#f8d7da", "foreground": "#721c24"},
        "idle":    {"background": "#fff3cd", "foreground": "#856404"},
    }
    tag_configs: dict[str, dict[str, Any]] = {}
    device_type: str = ""
    columns: Sequence[str] = ()
    headings: dict[str, str] = {}

    @staticmethod
    def _log_ui_debug(view: Any, message: str, exc: Exception) -> None:
        logger = getattr(view, "logger", LOGGER)
        logger.debug("%s: %s", message, exc)

    def __init__(
        self,
        parent: Frame,
        *,
        model: DevicesModel | None = None,
        controller: AppController | None = None,
        settings_service: SettingsService | None = None,
        device_actions_service: DeviceActionService | None = None,
    ) -> None:
        """
        Initialise la vue, charge les icones, construit l'UI
        et enregistre la vue aupres du controleur.
        """
        super().__init__(parent)
        ContextMenuMixin.__init__(self)

        self.parent = parent
        self.model = model or DevicesModel()
        self.controller = controller or AppController(self.model, self)
        self.controller.register_view(self)
        self.network_tools = NetworkToolsController()
        self.settings_service = settings_service
        self.device_actions_service = device_actions_service or DeviceActionService()

        self.sort_col = None
        self.sort_reverse = False
        self.refresh_paused = False
        self._rendered_iids: set[str] = set()
        self._row_state: dict[str, tuple[str, tuple[Any, ...]]] = {}
        self.search_var = tk.StringVar(value="")
        self.show_local_monitoring_button = True
        self.force_inventory_visible = False
        app_settings = self._current_settings()
        self.theme = resolve_theme(str(getattr(app_settings, "ui_theme", "light") or "light"))
        self.ui_tokens = resolve_ui_style_tokens(self.theme.key)
        self.configure(bg=self.theme.colors["app_bg"])
        self._init_theme_support(self.theme.key, style_scope=f"{self.__class__.__name__}.View")
        self.status_indicator_style = self._normalize_status_indicator_style(
            str(getattr(app_settings, "status_indicator_style", "badge") or "badge")
        )

        # Configuration des tags couleur
        self.tag_configs = {**self.default_tag_configs, **self.tag_configs}

        self._load_icons()
        self._build_ui()
        self.update_display()

    def _load_icons(self) -> None:
        """Charge les images online/offline/idle depuis les ressources."""
        base = Path("monitoring/ui/assets")
        p = resource_path
        try:
            self.img_monitoring_paused = PhotoImage(file=p(base / "monitoring_paused.png"))
        except Exception:
            LOGGER.exception("Erreur chargement icones")
            self.img_monitoring_paused = None
        self._load_status_icons(self.status_indicator_style)

    @staticmethod
    def _normalize_status_indicator_style(style_key: str) -> str:
        key = (style_key or "").strip().lower()
        if key in {"dot", "pastille"}:
            return "dot"
        return "badge"

    @staticmethod
    def _draw_circle(img: PhotoImage, size: int, *, fill: str, outline: str) -> None:
        cx = size / 2.0
        cy = size / 2.0
        radius = (size - 3) / 2.0
        inner = radius - 1.2
        for y in range(size):
            for x in range(size):
                dx = (x + 0.5) - cx
                dy = (y + 0.5) - cy
                dist2 = (dx * dx) + (dy * dy)
                if dist2 <= inner * inner:
                    img.put(fill, (x, y))
                elif dist2 <= radius * radius:
                    img.put(outline, (x, y))

    @staticmethod
    def _draw_diag_line(img: PhotoImage, x0: int, y0: int, x1: int, y1: int, color: str, thickness: int = 1) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            t = i / steps
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            for ox in range(-thickness + 1, thickness):
                for oy in range(-thickness + 1, thickness):
                    xx = x + ox
                    yy = y + oy
                    if 0 <= xx < int(img["width"]) and 0 <= yy < int(img["height"]):
                        img.put(color, (xx, yy))

    def _icon_badge(self, status: str) -> PhotoImage:
        size = 14
        img = PhotoImage(width=size, height=size)
        palette = {
            "online": ("#16a34a", "#0f7a36"),
            "offline": ("#dc2626", "#9f1f1f"),
            "idle": ("#0ea5e9", "#0369a1"),
        }
        fill, outline = palette.get(status, ("#64748b", "#475569"))
        self._draw_circle(img, size, fill=fill, outline=outline)
        if status == "online":
            self._draw_diag_line(img, 4, 8, 6, 10, "#ffffff", thickness=1)
            self._draw_diag_line(img, 6, 10, 10, 5, "#ffffff", thickness=1)
        elif status == "offline":
            self._draw_diag_line(img, 4, 4, 10, 10, "#ffffff", thickness=1)
            self._draw_diag_line(img, 10, 4, 4, 10, "#ffffff", thickness=1)
        else:  # idle
            for y in range(4, 11):
                img.put("#ffffff", (5, y))
                img.put("#ffffff", (8, y))
        return img

    def _icon_dot(self, status: str) -> PhotoImage:
        size = 12
        img = PhotoImage(width=size, height=size)
        palette = {
            "online": ("#22c55e", "#15803d"),
            "offline": ("#ef4444", "#991b1b"),
            "idle": ("#38bdf8", "#0369a1"),
        }
        fill, outline = palette.get(status, ("#94a3b8", "#475569"))
        self._draw_circle(img, size, fill=fill, outline=outline)
        if status == "idle":
            # Donne une pastille "anneau" pour idle: plus distincte de online/offline.
            center = size // 2
            for y in range(size):
                for x in range(size):
                    dx = x - center
                    dy = y - center
                    if (dx * dx) + (dy * dy) <= 4:
                        img.put("#0f172a", (x, y))
        return img

    def _load_status_icons(self, style_key: str) -> None:
        style = self._normalize_status_indicator_style(style_key)
        self.status_indicator_style = style
        try:
            if style == "dot":
                self.img_online = self._icon_dot("online")
                self.img_offline = self._icon_dot("offline")
                self.img_idle = self._icon_dot("idle")
            else:
                self.img_online = self._icon_badge("online")
                self.img_offline = self._icon_badge("offline")
                self.img_idle = self._icon_badge("idle")
        except Exception as exc:
            DeviceListView._log_ui_debug(self, "Fallback status icon loading engaged", exc)
            base = Path("monitoring/ui/assets")
            p = resource_path
            self.img_online = PhotoImage(file=p(base / "online.png"))
            self.img_offline = PhotoImage(file=p(base / "offline.png"))
            self.img_idle = PhotoImage(file=p(base / "idle.png"))

    def refresh_status_icons(self, style_key: str | None = None) -> None:
        target_style = style_key if style_key is not None else self.status_indicator_style
        self._load_status_icons(target_style)
        # Force row repaint so Treeview rows rebind to newly generated PhotoImage objects.
        self._row_state.clear()
        try:
            self.update_display()
        except Exception:
            LOGGER.exception("Erreur rafraichissement des icones de statut")

    def _build_ui(self) -> None:
        """Construit le Treeview, le scrollbar, le bouton toggle et les bindings."""
        c = self.theme.colors
        cont = Frame(self, bg=c["app_bg"])
        cont.pack(fill=BOTH, expand=True, padx=5, pady=5)
        self._cont = cont

        btnf = Frame(cont, bg=c["app_bg"])
        btnf.pack(fill=X, pady=(0, 5))
        self._btn_row = btnf
        self.btn_toggle = Button(
            btnf,
            command=self._toggle_monitoring,
            font=self.ui_tokens.fonts.button,
            relief="raised",
            bd=2,
        )
        self.btn_toggle.pack(side=LEFT, padx=5)
        self.btn_logs = Button(
            btnf,
            text="Logs",
            command=self._open_logs,
            font=self.ui_tokens.fonts.button,
            relief="raised",
            bd=2,
        )
        self.btn_logs.pack(side=RIGHT, padx=5)

        search_row = Frame(cont, bg=c["app_bg"])
        search_row.pack(fill=X, padx=2, pady=(2, 6))
        self._search_row = search_row
        self.lbl_search = Label(
            search_row,
            text="Recherche:",
            bg=c["app_bg"],
            fg=c["text_primary"],
        )
        self.lbl_search.pack(side=LEFT, padx=(2, 6))
        self.entry_search = tk.Entry(
            search_row,
            textvariable=self.search_var,
            relief="solid",
            bd=1,
        )
        self.entry_search.pack(side=LEFT, fill=X, expand=True)
        self.btn_clear_search = Button(
            search_row,
            text="Effacer",
            command=self._clear_search,
            relief="raised",
            bd=1,
        )
        self.btn_clear_search.pack(side=RIGHT, padx=(6, 0))
        bind_blue_hover(self.btn_toggle, lambda: self.theme.colors)
        bind_blue_hover(self.btn_logs, lambda: self.theme.colors)
        bind_blue_hover(self.btn_clear_search, lambda: self.theme.colors)
        self.search_var.trace_add("write", self._on_search_change)
        self._apply_monitoring_button_visibility()

        tree_wrap = Frame(cont, bg=c["app_bg"])
        tree_wrap.pack(fill=BOTH, expand=True)
        self._tree_wrap = tree_wrap

        self.tree = ttk.Treeview(
            tree_wrap,
            columns=self.columns,
            show=("tree", "headings"),
            selectmode="browse",
        )
        make_treeview_sortable(self.tree, self)
        self.tree.heading("#0", text="Statut", anchor="center")
        self.tree.column("#0", width=56, minwidth=56, stretch=False, anchor="center")
        for col in self.columns:
            self.tree.heading(col, text=self.headings.get(col, col.capitalize()))
            if col == "ip":
                self.tree.column(col, width=130, minwidth=120, stretch=False, anchor="w")
            elif col == "name":
                self.tree.column(col, width=220, minwidth=170, stretch=True, anchor="w")
            elif col == "desc":
                self.tree.column(col, width=260, minwidth=180, stretch=True, anchor="w")
            else:
                self.tree.column(col, anchor="w")
        for tag, cfg in self.tag_configs.items():
            self.tree.tag_configure(tag, **cfg)

        self.tree_scrollbar = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=self.tree_scrollbar.set)

        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree_scrollbar.pack(side=LEFT, fill="y")

        self.placeholder = Frame(tree_wrap, bg=c["placeholder_bg"])
        self.placeholder_image = Label(
            self.placeholder,
            image=self.img_monitoring_paused,
            bg=c["placeholder_bg"],
        )
        self.placeholder_image.pack(pady=(24, 10))
        self.placeholder_title = Label(
            self.placeholder,
            text="Monitoring arrete",
            bg=c["placeholder_bg"],
            fg=c["text_primary"],
            font=self.ui_tokens.fonts.card_state_value,
        )
        self.placeholder_title.pack()
        self.placeholder_subtitle = Label(
            self.placeholder,
            text="Demarrez la sonde pour afficher les equipements en temps reel.",
            bg=c["placeholder_bg"],
            fg=c["text_muted"],
            font=self.ui_tokens.fonts.body,
        )
        self.placeholder_subtitle.pack(pady=(6, 0))
        self._placeholder_visible = False
        self.refresh_watermark_image()
        self.apply_theme(self.theme.key)

        # Bindings
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_mutual)
        self.bind_context_menu_with_pause(
            tree=self.tree, menu_builder=self._build_context_menu
        )
        self.tree.bind("<Double-1>", self._on_double_click)

    def _clear_search(self) -> None:
        if self.search_var.get():
            self.search_var.set("")

    def set_local_monitoring_button_visible(self, visible: bool) -> None:
        self.show_local_monitoring_button = bool(visible)
        self._apply_monitoring_button_visibility()

    def set_force_inventory_visible(self, visible: bool) -> None:
        self.force_inventory_visible = bool(visible)

    def _apply_monitoring_button_visibility(self) -> None:
        if not hasattr(self, "_btn_row"):
            return
        if self.show_local_monitoring_button:
            if not self._btn_row.winfo_manager():
                before_widget = getattr(self, "_search_row", None)
                if before_widget is not None:
                    self._btn_row.pack(fill=X, pady=(0, 5), before=before_widget)
                else:
                    self._btn_row.pack(fill=X, pady=(0, 5))
        elif self._btn_row.winfo_manager():
            self._btn_row.pack_forget()

    def _on_search_change(self, *_args) -> None:
        try:
            # La recherche doit rester reactive meme si une pause UI est restee active
            # (ex: menu contextuel interrompu sous Windows packagé).
            self.refresh_paused = False
            self.unlock_view()
            self.update_display()
        except Exception:
            LOGGER.exception("Erreur rafraichissement recherche")

    def _device_matches_search(self, did: str, dev: Any, query: str) -> bool:
        if not query:
            return True
        haystack_parts = [
            str(did),
            str(getattr(dev, "name", "")),
            str(getattr(dev, "ip", "")),
            str(getattr(dev, "description", "")),
            str(getattr(dev, "status", "")),
        ]
        for col in self.columns:
            if col == "desc":
                continue
            haystack_parts.append(str(getattr(dev, col, "")))
        haystack = " ".join(haystack_parts).lower()
        return query in haystack

    @staticmethod
    def _sort_value_for_column(dev: Any, col: str):
        if col == "ip":
            return ipaddress.ip_address(str(getattr(dev, "ip", "")))
        if col == "desc":
            return str(getattr(dev, "description", "")).lower()
        return str(getattr(dev, col, "")).lower()

    @staticmethod
    def _row_values_for_device(dev: Any, columns: Sequence[str]) -> tuple[Any, ...]:
        return tuple(getattr(dev, column) if column != "desc" else dev.description for column in columns)

    @staticmethod
    def _status_icon_for_device(view: Any, status: str):
        return {
            "online": view.img_online,
            "offline": view.img_offline,
            "idle": view.img_idle,
        }[status]

    @staticmethod
    def _status_tag_palette(theme_key: str) -> dict[str, dict[str, str]]:
        if theme_key == "dark":
            return {
                "online": {"background": "#163329", "foreground": "#86efac"},
                "offline": {"background": "#3a1d23", "foreground": "#fca5a5"},
                "idle": {"background": "#3b3419", "foreground": "#fde68a"},
            }
        return {
            "online": {"background": "#d4edda", "foreground": "#155724"},
            "offline": {"background": "#f8d7da", "foreground": "#721c24"},
            "idle": {"background": "#fff3cd", "foreground": "#856404"},
        }

    @staticmethod
    def _monitoring_button_colors(colors: dict[str, str], running: bool) -> dict[str, str]:
        return {
            "bg": colors["button_active_bg"] if running else colors["button_inactive_bg"],
            "activebackground": colors["button_active_bg"] if running else colors["button_inactive_bg"],
            "fg": colors["button_active_fg"] if running else colors["button_inactive_fg"],
            "activeforeground": colors["button_active_fg"] if running else colors["button_inactive_fg"],
        }

    @staticmethod
    def _monitoring_button_label(view: Any) -> str:
        type_label = str(view.model.type_definitions.get(view.device_type, {}).get("label", view.device_type)).strip()
        return f"Monitoring {type_label}" if type_label else "Monitoring"

    @staticmethod
    def _filtered_items(view: Any) -> list[tuple[str, Any]]:
        items = list(view.model.device_data.get(view.device_type, {}).items())
        query = view.search_var.get().strip().lower()
        if query:
            items = [
                (did, dev)
                for did, dev in items
                if DeviceListView._device_matches_search(view, str(did), dev, query)
            ]
        if view.sort_col:
            try:
                items.sort(
                    key=lambda item: DeviceListView._sort_value_for_column(item[1], str(view.sort_col)),
                    reverse=view.sort_reverse,
                )
            except Exception:
                LOGGER.exception("Tri impossible sur la colonne '%s'", view.sort_col)
        return items

    @staticmethod
    def _placeholder_should_be_visible(view: Any, running: bool) -> bool:
        return (not running) and (not view.force_inventory_visible)

    @staticmethod
    def _placeholder_message() -> tuple[str, str]:
        return (
            "Monitoring arrete",
            "Demarrez la sonde pour afficher les equipements en temps reel.",
        )

    @staticmethod
    def _apply_background_to_widgets(widgets: Sequence[Any], bg: str) -> None:
        for widget in widgets:
            if widget is None:
                continue
            try:
                widget.configure(bg=bg)
            except Exception as exc:
                DeviceListView._log_ui_debug(widget, "Widget background update failed", exc)

    @staticmethod
    def _configure_treeview_style(view: Any, colors: dict[str, str]) -> None:
        style = ttk.Style()
        style_name = "NM.Treeview"
        heading_style = "NM.Treeview.Heading"
        style.configure(
            style_name,
            background=colors["tree_bg"],
            fieldbackground=colors["tree_bg"],
            foreground=colors["tree_fg"],
            borderwidth=0,
            relief="flat",
        )
        style.configure(
            heading_style,
            background=colors["panel_bg"],
            foreground=colors["tree_heading_fg"],
            borderwidth=1,
            relief="flat",
        )
        style.map(style_name, background=[("selected", colors["tree_select_bg"])])
        style.map(
            heading_style,
            background=[("active", colors["panel_hover_bg"]), ("!active", colors["panel_bg"])],
            foreground=[("!disabled", colors["tree_heading_fg"])],
        )
        view.tree.configure(style=style_name)

    @staticmethod
    def _configure_placeholder_section(view: Any, colors: dict[str, str]) -> None:
        view.placeholder.configure(bg=colors["placeholder_bg"])
        view.placeholder_image.configure(bg=colors["placeholder_bg"])
        view.placeholder_title.configure(bg=colors["placeholder_bg"], fg=colors["text_primary"])
        view.placeholder_subtitle.configure(bg=colors["placeholder_bg"], fg=colors["text_muted"])

    @staticmethod
    def _configure_search_controls(view: Any, colors: dict[str, str]) -> None:
        view.lbl_search.configure(bg=colors["app_bg"], fg=colors["text_primary"])
        view.entry_search.configure(
            bg=colors["panel_bg"],
            fg=colors["text_primary"],
            insertbackground=colors["text_primary"],
            highlightthickness=1,
            highlightbackground=colors["placeholder_border"],
            highlightcolor=colors["nav_active_bg"],
        )
        view.btn_clear_search.configure(relief="flat", bd=1)
        view.btn_logs.configure(relief="flat", bd=1)
        apply_control_button_style(view.btn_clear_search, colors, hovered=False)
        apply_control_button_style(view.btn_logs, colors, hovered=False)

    def update_display(self) -> None:
        """
        Met a jour les lignes du Treeview selon model.device_data[self.device_type]
        et ajuste le texte/couleur du bouton toggle.
        """
        if not hasattr(self, "tree"):
            return
        try:
            if not bool(self.winfo_exists()) or not bool(self.tree.winfo_exists()):
                self.controller.unregister_view(self)
                return
        except Exception as exc:
            DeviceListView._log_ui_debug(self, "View existence check failed", exc)
            return

        if self.refresh_paused or self.is_locked_view():
            return

        items = DeviceListView._filtered_items(self)
        if self.device_type != "consolidated":
            self.tree.config(height=max(len(items), 5))

        desired_iids = [str(did) for did, _ in items]
        desired_set = set(desired_iids)

        # Supprime les lignes qui ne sont plus dans le modele.
        stale_iids = [iid for iid in set(self._row_state).difference(desired_set) if self.tree.exists(iid)]
        if stale_iids:
            self.tree.delete(*stale_iids)
        for iid in stale_iids:
            self._row_state.pop(iid, None)

        for did, dev in items:
            iid = str(did)
            icon = DeviceListView._status_icon_for_device(self, dev.status)
            values = DeviceListView._row_values_for_device(dev, self.columns)
            state_sig = (dev.status, values)
            if not self.tree.exists(iid):
                self.tree.insert(
                    "", "end", iid=iid, image=icon, values=values, tags=(dev.status,)
                )
            else:
                self.tree.reattach(iid, "", "end")
                if self._row_state.get(iid) != state_sig:
                    self.tree.item(iid, image=icon, values=values, tags=(dev.status,))
            self._row_state[iid] = state_sig

        # Repositionne les lignes sans les recreer.
        for idx, iid in enumerate(desired_iids):
            if self.tree.exists(iid):
                try:
                    self.tree.move(iid, "", idx)
                except Exception as exc:
                    DeviceListView._log_ui_debug(self, f"Tree row move failed for iid={iid}", exc)
        self._rendered_iids = {iid for iid in desired_iids if self.tree.exists(iid)}

        running = self.model.do_run.get(self.device_type, False)
        self.btn_toggle.config(
            text=DeviceListView._monitoring_button_label(self),
            **DeviceListView._monitoring_button_colors(self.theme.colors, running),
        )
        title, subtitle = DeviceListView._placeholder_message()
        self._set_placeholder_visible(
            DeviceListView._placeholder_should_be_visible(self, running),
            title=title,
            subtitle=subtitle,
        )

    def _set_placeholder_visible(self, visible: bool, *, title: str, subtitle: str) -> None:
        """Basculer entre le treeview et le visuel d'arret monitoring."""
        self.placeholder_title.config(text=title)
        self.placeholder_subtitle.config(text=subtitle)

        if visible and not self._placeholder_visible:
            self.tree.pack_forget()
            self.tree_scrollbar.pack_forget()
            self.placeholder.pack(fill=BOTH, expand=True)
            self._placeholder_visible = True
            return

        if not visible and self._placeholder_visible:
            self.placeholder.pack_forget()
            self.tree.pack(side=LEFT, fill=BOTH, expand=True)
            self.tree_scrollbar.pack(side=LEFT, fill="y")
            self._placeholder_visible = False

    def refresh_watermark_image(self, custom_path: str | None = None) -> None:
        """Recharge l'image watermark depuis les settings (ou chemin fourni)."""
        candidate = (custom_path or "").strip()
        if not candidate:
            try:
                candidate = str(getattr(self._current_settings(), "watermark_image_path", "") or "").strip()
            except Exception as exc:
                DeviceListView._log_ui_debug(self, "Watermark settings lookup failed", exc)
                candidate = ""
        selected = candidate if candidate and Path(candidate).is_file() else ""

        if selected:
            try:
                self.img_monitoring_paused = PhotoImage(file=selected)
            except Exception as exc:
                DeviceListView._log_ui_debug(self, "Custom watermark image loading failed", exc)
                self.img_monitoring_paused = None
        else:
            self.img_monitoring_paused = None

        try:
            self.placeholder_image.configure(image=self.img_monitoring_paused)
            self.placeholder_image.image = self.img_monitoring_paused
            if self.img_monitoring_paused is None:
                self.placeholder_image.pack_forget()
            elif not self.placeholder_image.winfo_manager():
                self.placeholder_image.pack(pady=(24, 10))
        except Exception as exc:
            DeviceListView._log_ui_debug(self, "Watermark placeholder image update failed", exc)

    def apply_theme(self, theme_key: str) -> None:
        self.theme = resolve_theme(theme_key)
        self.configure(bg=self.theme.colors["app_bg"])
        self._configure_view_ttk_styles()
        c = self.theme.colors

        DeviceListView._apply_background_to_widgets((
            getattr(self, "_cont", None),
            getattr(self, "_btn_row", None),
            getattr(self, "_search_row", None),
            getattr(self, "_tree_wrap", None),
        ), c["app_bg"])

        try:
            DeviceListView._configure_placeholder_section(self, c)
            DeviceListView._configure_search_controls(self, c)
        except Exception as exc:
            DeviceListView._log_ui_debug(self, "Placeholder/search theme update failed", exc)

        try:
            DeviceListView._configure_treeview_style(self, c)
        except Exception as exc:
            DeviceListView._log_ui_debug(self, "Treeview theme style setup failed", exc)

        status_tags = DeviceListView._status_tag_palette(self.theme.key)
        for tag, cfg in status_tags.items():
            try:
                self.tree.tag_configure(tag, **cfg)
            except Exception as exc:
                DeviceListView._log_ui_debug(self, f"Tree tag theme update failed for tag={tag}", exc)
                continue

        try:
            self.update_display()
        except Exception as exc:
            DeviceListView._log_ui_debug(self, "Theme-triggered display refresh failed", exc)
        try:
            self._apply_theme_recursive(self)
        except Exception as exc:
            DeviceListView._log_ui_debug(self, "Recursive theme apply failed", exc)

    def _build_context_menu(self) -> Menu:
        """
        Construit le menu contextuel commun : Ajouter / Modifier / Supprimer /
        Alerte (sans gestion du monitoring).
        """
        menu = Menu(
            self,
            tearoff=0,
            bg=self.theme.colors["menu_bg"],
            fg=self.theme.colors["menu_fg"],
        )
        menu.add_command(label="Ajouter", command=self._on_add)
        menu.add_command(label="Modifier", command=self._on_edit)
        menu.add_command(label="Supprimer", command=self._on_delete)
        menu.add_separator()
        device_id = self._selected_device_id()
        var = tk.BooleanVar(value=self._notify_flag_for_device(device_id))
        menu.add_checkbutton(
            label="Alerte sur changement de statut",
            variable=var,
            command=lambda d=device_id, v=var: self._toggle_notify(d, v),
        )
        menu.add_command(label="Afficher logs", command=self._open_logs)

        return menu

    def _toggle_notify(self, device_id: Optional[str], var: tk.BooleanVar) -> None:
        """
        Bascule le flag notify pour le device et notifie les vues.
        """
        if not device_id:
            return
        try:
            dtype, rid = self._resolve_notify_target(device_id)
            self.model.set_notify_flag(dtype, rid, var.get())
        except Exception:
            LOGGER.exception("Erreur bascule notification")

    def _toggle_monitoring(self) -> None:
        """
        Demarre/arrete le monitoring pour ce device_type.
        """
        self.refresh_paused = False
        self.controller.view = self
        if self.model.do_run.get(self.device_type, False):
            self.controller.stop_monitoring(self.device_type)
        else:
            self.controller.start_monitoring(self.device_type)

    def _open_logs(self) -> None:
        from monitoring.ui.dialogs.status_logs_viewer import StatusLogsViewer

        if self.device_type == "consolidated":
            self._open_status_logs_viewer("Journal global des changements de statut")
            return

        device_id = self._selected_device_id()
        dev = self.model.device_data.get(self.device_type, {}).get(str(device_id or ""))
        if dev is None:
            self._open_status_logs_viewer(f"Journal des changements - {self.device_type}", dtype=self.device_type)
            return
        self._open_status_logs_viewer(
            f'Logs {self.device_type} "{dev.name}"',
            dtype=self.device_type,
            device_id=str(device_id),
        )

    def _selected_device_id(self) -> Optional[str]:
        selection = tuple(self.tree.selection())
        if selection:
            return str(selection[0])
        focused = str(self.tree.focus() or "").strip()
        return focused or None

    def _resolve_notify_target(self, device_id: Optional[str]) -> tuple[str, str]:
        raw_id = str(device_id or "").strip()
        if self.device_type == "consolidated" and "::" in raw_id:
            dtype, rid = raw_id.split("::", 1)
            return str(dtype), str(rid)
        return str(self.device_type), raw_id

    def _notify_flag_for_device(self, device_id: Optional[str]) -> bool:
        if not device_id:
            return False
        dtype, rid = self._resolve_notify_target(device_id)
        return bool(self.model.notify_flags.get(dtype, {}).get(rid, False))

    def _open_status_logs_viewer(self, title: str, *, dtype: str | None = None, device_id: str | None = None) -> None:
        from monitoring.ui.dialogs.status_logs_viewer import StatusLogsViewer

        StatusLogsViewer(
            self.parent,
            title=title,
            dtype=dtype,
            device_id=device_id,
            manager=self.model.manager,
        )

    def _safe_clear_view_selection(self, view: object) -> None:
        tree = getattr(view, "tree", None)
        if tree is None:
            return
        try:
            selection = tuple(tree.selection())
            if selection:
                tree.selection_remove(*selection)
        except Exception as exc:
            LOGGER.debug("Deselection ignoree pour vue %r: %s", view, exc)

    def _safe_clear_master_view_selection(self, view_attr: str) -> None:
        master = getattr(self.parent, "master", None)
        if master is None:
            return
        target_view = getattr(master, str(view_attr), None)
        if target_view is None:
            return
        self._safe_clear_view_selection(target_view)

    def _on_selection_mutual(self, _evt=None) -> None:
        """Stub pour selection mutuelle entre vues (a surcharger si besoin)."""
        pass

    def _current_settings(self):
        if self.settings_service is not None:
            return self.settings_service.current()
        from monitoring.config.settings import load_settings

        return load_settings()

    def _save_settings(self, settings) -> None:
        if self.settings_service is not None:
            self.settings_service.save(settings)
            return
        from monitoring.config.settings import save_settings

        save_settings(settings)

    def _type_label(self) -> str:
        return str(self.model.type_definitions.get(self.device_type, {}).get("label", self.device_type)).strip()

    def _selected_device_record(self) -> tuple[str | None, object | None]:
        device_id = self._selected_device_id()
        if not device_id:
            return None, None
        return device_id, self.model.device_data.get(self.device_type, {}).get(device_id)

    def _build_device_form_initial(self, device_id: str, device) -> dict[str, object]:
        return {
            "name": getattr(device, "name", ""),
            "ip": getattr(device, "ip", ""),
            "desc": getattr(device, "description", ""),
            "subtype": getattr(device, "type", ""),
            "tv_id": getattr(device, "id_Teamviewer", ""),
            "action_double_click": getattr(device, "action_double_click", ""),
            "web_url": getattr(device, "web_url", ""),
            "ssh_user": getattr(device, "ssh_user", ""),
            "notify": self.model.notify_flags.get(self.device_type, {}).get(device_id, True),
            "custom_data": self.model.extract_custom_data(device),
        }

    def _create_device_from_form(self, form_data: dict[str, object]) -> bool:
        success = self.model.add_device(
            self.device_type,
            str(form_data["name"]),
            str(form_data["ip"]),
            str(form_data["desc"]),
            id_Teamviewer=str(form_data.get("tv_id", "")),
            device_subtype=str(form_data.get("subtype", "")),
            action_double_click=str(form_data.get("action_double_click", "")),
            web_url=str(form_data.get("web_url", "")),
            ssh_user=str(form_data.get("ssh_user", "")),
            custom_data=dict(form_data.get("custom_data", {}) or {}),
            notify=bool(form_data.get("notify", True)),
        )
        return bool(success)

    def _update_device_from_form(self, device_id: str, form_data: dict[str, object]) -> bool:
        return self.model.update_device(
            self.device_type,
            device_id,
            new_name=str(form_data["name"]),
            new_ip=str(form_data["ip"]),
            new_description=str(form_data["desc"]),
            id_Teamviewer=str(form_data.get("tv_id", "")),
            device_subtype=str(form_data.get("subtype", "")),
            action_double_click=str(form_data.get("action_double_click", "")),
            web_url=str(form_data.get("web_url", "")),
            ssh_user=str(form_data.get("ssh_user", "")),
            custom_data=dict(form_data.get("custom_data", {}) or {}),
            notify=bool(form_data.get("notify", True)),
        )

    def _device_type_actions(self) -> list[dict]:
        return list(self.model.manager.list_type_actions(self.device_type))

    def _resolve_device_action(self, device) -> str:
        return self.device_actions_service.resolve_action(
            device_type=self.device_type,
            device=device,
            configured_action=str(getattr(device, "action_double_click", "")),
            action_rows=self._device_type_actions(),
        )

    def _available_action_rows_for_device(self, device) -> list[dict]:
        allowed = set(
            self.device_actions_service.available_actions(
                action_rows=self._device_type_actions(),
                subtype=str(getattr(device, "type", "")),
            )
        )
        return [
            action
            for action in self._device_type_actions()
            if str(action.get("action_key", "")).strip().lower() in allowed
        ]

    def _run_device_action(self, device, action_key: str | None = None) -> None:
        resolved_action = str(action_key or self._resolve_device_action(device)).strip().lower()
        self.device_actions_service.run_action(
            device=device,
            action_key=resolved_action,
            prompt_ssh_login=lambda ip: simpledialog.askstring("Connexion SSH", f"Login SSH pour {ip} :", parent=self.parent),
        )

    def _on_add(self) -> None:
        """A surcharger dans les sous-classes pour ajouter un device."""
        raise NotImplementedError

    def _on_edit(self) -> None:
        """A surcharger dans les sous-classes pour modifier un device."""
        raise NotImplementedError

    def _on_delete(self) -> None:
        """A surcharger dans les sous-classes pour supprimer un device."""
        raise NotImplementedError

    def _on_double_click(self, _evt=None) -> None:
        """A surcharger dans les sous-classes pour gerer le double-clic."""
        raise NotImplementedError
