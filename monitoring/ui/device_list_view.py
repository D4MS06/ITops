# src/monitoring/ui/device_list_view.py

from __future__ import annotations

import ipaddress
import logging
import queue
import threading
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
    TOP,
    X,
    ttk,
)
from tkinter import simpledialog
from tkinter.scrolledtext import ScrolledText
from typing import Any, Optional, Sequence

from monitoring.controllers.app_controller import AppController
from monitoring.config.settings import load_settings
from monitoring.controllers.network_tools_controller import NetworkToolsController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.base_window import resource_path
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import apply_control_button_style, bind_blue_hover
from monitoring.ui.view_mixins import ContextMenuMixin, ThemedViewMixin
from monitoring.ui.utils.sortable_tree import make_treeview_sortable

LOGGER = logging.getLogger(__name__)


class DeviceListView(Frame, ContextMenuMixin, ThemedViewMixin):
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

    def __init__(
        self,
        parent: Frame,
        *,
        model: DevicesModel | None = None,
        controller: AppController | None = None,
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

        self.sort_col = None
        self.sort_reverse = False
        self.refresh_paused = False
        self._rendered_iids: set[str] = set()
        self._row_state: dict[str, tuple[str, tuple[Any, ...]]] = {}
        self.search_var = tk.StringVar(value="")
        self.show_local_monitoring_button = True
        self.force_inventory_visible = False
        app_settings = load_settings()
        self.theme = resolve_theme(str(getattr(app_settings, "ui_theme", "light") or "light"))
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
        except Exception:
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
            font=("Arial", 10, "bold"),
            relief="raised",
            bd=2,
        )
        self.btn_toggle.pack(side=LEFT, padx=5)
        self.btn_logs = Button(
            btnf,
            text="Logs",
            command=self._open_logs,
            font=("Arial", 10, "bold"),
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
            font=("Segoe UI", 12, "bold"),
        )
        self.placeholder_title.pack()
        self.placeholder_subtitle = Label(
            self.placeholder,
            text="Demarrez la sonde pour afficher les equipements en temps reel.",
            bg=c["placeholder_bg"],
            fg=c["text_muted"],
            font=("Segoe UI", 10),
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

    def update_display(self) -> None:
        """
        Met a jour les lignes du Treeview selon model.device_data[self.device_type]
        et ajuste le texte/couleur du bouton toggle.
        """
        if self.refresh_paused or self.is_locked_view():
            return

        items = list(self.model.device_data.get(self.device_type, {}).items())
        query = self.search_var.get().strip().lower()
        if query:
            items = [(did, dev) for did, dev in items if self._device_matches_search(str(did), dev, query)]
        if self.device_type != "consolidated":
            self.tree.config(height=max(len(items), 5))

        if self.sort_col:
            try:
                items.sort(
                    key=lambda x: self._sort_value_for_column(x[1], str(self.sort_col)),
                    reverse=self.sort_reverse,
                )
            except Exception:
                LOGGER.exception("Tri impossible sur la colonne '%s'", self.sort_col)

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
            icon = {
                "online": self.img_online,
                "offline": self.img_offline,
                "idle": self.img_idle,
            }[dev.status]
            values = tuple(
                getattr(dev, c) if c != "desc" else dev.description
                for c in self.columns
            )
            state_sig = (dev.status, values)
            if not self.tree.exists(iid):
                self.tree.insert(
                    "", "end", iid=iid, image=icon, values=values, tags=(dev.status,)
                )
            elif self._row_state.get(iid) != state_sig:
                self.tree.item(iid, image=icon, values=values, tags=(dev.status,))
            self._row_state[iid] = state_sig

        # Repositionne les lignes sans les recreer.
        for idx, iid in enumerate(desired_iids):
            if self.tree.exists(iid):
                try:
                    self.tree.move(iid, "", idx)
                except Exception:
                    pass
        self._rendered_iids = {iid for iid in desired_iids if self.tree.exists(iid)}

        running = self.model.do_run.get(self.device_type, False)
        label_map = {
            "switch": "Monitoring switch",
            "server": "Monitoring Serveur",
        }
        button_label = label_map.get(self.device_type, "Monitoring")
        self.btn_toggle.config(
            text=button_label,
            bg=self.theme.colors["button_active_bg"] if running else self.theme.colors["button_inactive_bg"],
            activebackground=self.theme.colors["button_active_bg"] if running else self.theme.colors["button_inactive_bg"],
            fg=self.theme.colors["button_active_fg"] if running else self.theme.colors["button_inactive_fg"],
            activeforeground=self.theme.colors["button_active_fg"] if running else self.theme.colors["button_inactive_fg"],
        )
        self._set_placeholder_visible(
            (not running) and (not self.force_inventory_visible),
            title="Monitoring arrete",
            subtitle="Demarrez la sonde pour afficher les equipements en temps reel.",
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
                candidate = str(getattr(load_settings(), "watermark_image_path", "") or "").strip()
            except Exception:
                candidate = ""
        selected = candidate if candidate and Path(candidate).is_file() else ""

        if selected:
            try:
                self.img_monitoring_paused = PhotoImage(file=selected)
            except Exception:
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
        except Exception:
            pass

    def apply_theme(self, theme_key: str) -> None:
        self.theme = resolve_theme(theme_key)
        self.configure(bg=self.theme.colors["app_bg"])
        self._configure_view_ttk_styles()
        c = self.theme.colors

        for widget in (
            getattr(self, "_cont", None),
            getattr(self, "_btn_row", None),
            getattr(self, "_search_row", None),
            getattr(self, "_tree_wrap", None),
        ):
            if widget is not None:
                try:
                    widget.configure(bg=c["app_bg"])
                except Exception:
                    pass

        try:
            self.placeholder.configure(bg=c["placeholder_bg"])
            self.placeholder_image.configure(bg=c["placeholder_bg"])
            self.placeholder_title.configure(bg=c["placeholder_bg"], fg=c["text_primary"])
            self.placeholder_subtitle.configure(bg=c["placeholder_bg"], fg=c["text_muted"])
            self.lbl_search.configure(bg=c["app_bg"], fg=c["text_primary"])
            self.entry_search.configure(
                bg=c["panel_bg"],
                fg=c["text_primary"],
                insertbackground=c["text_primary"],
                highlightthickness=1,
                highlightbackground=c["placeholder_border"],
                highlightcolor=c["nav_active_bg"],
            )
            self.btn_clear_search.configure(
                relief="flat",
                bd=1,
            )
            self.btn_logs.configure(relief="flat", bd=1)
            apply_control_button_style(self.btn_clear_search, c, hovered=False)
            apply_control_button_style(self.btn_logs, c, hovered=False)
        except Exception:
            pass

        try:
            style = ttk.Style()
            # Force a style engine that honors custom heading/background colors.
            try:
                style.theme_use("clam")
            except Exception:
                pass
            style_name = "NM.Treeview"
            heading_style = "NM.Treeview.Heading"
            style.configure(
                style_name,
                background=c["tree_bg"],
                fieldbackground=c["tree_bg"],
                foreground=c["tree_fg"],
                borderwidth=0,
                relief="flat",
            )
            style.configure(
                heading_style,
                background=c["panel_bg"],
                foreground=c["tree_heading_fg"],
                borderwidth=1,
                relief="flat",
            )
            style.map(style_name, background=[("selected", c["tree_select_bg"])])
            style.map(
                heading_style,
                background=[("active", c["panel_hover_bg"]), ("!active", c["panel_bg"])],
                foreground=[("!disabled", c["tree_heading_fg"])],
            )
            self.tree.configure(style=style_name)
        except Exception:
            pass

        if self.theme.key == "dark":
            status_tags = {
                "online": {"background": "#163329", "foreground": "#86efac"},
                "offline": {"background": "#3a1d23", "foreground": "#fca5a5"},
                "idle": {"background": "#3b3419", "foreground": "#fde68a"},
            }
        else:
            status_tags = {
                "online": {"background": "#d4edda", "foreground": "#155724"},
                "offline": {"background": "#f8d7da", "foreground": "#721c24"},
                "idle": {"background": "#fff3cd", "foreground": "#856404"},
            }
        for tag, cfg in status_tags.items():
            try:
                self.tree.tag_configure(tag, **cfg)
            except Exception:
                continue

        try:
            self.update_display()
        except Exception:
            pass
        try:
            self._apply_theme_recursive(self)
        except Exception:
            pass

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

        # Checkbutton pour le flag notify
        sel = self.tree.selection()
        did = sel[0] if sel else None
        current = False
        if did:
            if self.device_type == "consolidated" and "::" in str(did):
                dtype, rid = str(did).split("::", 1)
                current = self.model.notify_flags.get(str(dtype), {}).get(str(rid), False)
            else:
                current = self.model.notify_flags.get(self.device_type, {}).get(did, False)
        var = tk.BooleanVar(value=current)
        menu.add_checkbutton(
            label="Alerte sur changement de statut",
            variable=var,
            command=lambda d=did, v=var: self._toggle_notify(d, v),
        )
        menu.add_command(label="Afficher logs", command=self._open_logs)

        return menu

    def _show_tool_output(self, title: str, output: str) -> None:
        """Affiche le resultat d'un outil reseau."""
        win = tk.Toplevel(self.parent)
        win.title(title)
        win.geometry("760x480")
        c = self.theme.colors
        win.configure(bg=c["app_bg"])
        txt = ScrolledText(win, wrap="word")
        txt.pack(fill=BOTH, expand=True, padx=8, pady=8)
        txt.configure(bg=c["tree_bg"], fg=c["tree_fg"], insertbackground=c["tree_fg"])
        txt.insert("1.0", output or "Aucune sortie.")
        txt.configure(state="disabled")

    def _open_tool_output_window(self, title: str):
        win = tk.Toplevel(self.parent)
        win.title(title)
        win.geometry("760x480")
        c = self.theme.colors
        win.configure(bg=c["app_bg"])
        txt = ScrolledText(win, wrap="word")
        txt.pack(fill=BOTH, expand=True, padx=8, pady=8)
        txt.configure(bg=c["tree_bg"], fg=c["tree_fg"], insertbackground=c["tree_fg"])
        txt.insert("1.0", "Execution en cours...\n")
        txt.configure(state="disabled")
        return win, txt

    @staticmethod
    def _append_tool_line(txt: ScrolledText, line: str) -> None:
        txt.configure(state="normal")
        txt.insert("end", line + "\n")
        txt.see("end")
        txt.configure(state="disabled")

    def _run_network_tool(self, title: str, runner) -> None:
        ok, output = runner()
        status = "OK" if ok else "ECHEC"
        self._show_tool_output(f"{title} - {status}", output)

    def _run_network_tool_stream(self, title: str, runner_stream) -> None:
        """Lance un outil reseau avec affichage progressif en temps reel."""
        win, txt = self._open_tool_output_window(title)
        events: queue.Queue = queue.Queue()

        def _push(line: str) -> None:
            events.put(("line", line))

        def _worker() -> None:
            ok = runner_stream(_push)
            events.put(("done", ok))

        def _poll() -> None:
            if not win.winfo_exists():
                return
            try:
                while True:
                    kind, payload = events.get_nowait()
                    if kind == "line":
                        self._append_tool_line(txt, str(payload))
                    elif kind == "done":
                        status = "OK" if payload else "ECHEC"
                        win.title(f"{title} - {status}")
            except queue.Empty:
                pass
            win.after(120, _poll)

        threading.Thread(target=_worker, daemon=True).start()
        _poll()

    def _run_ping_tool_stream(self, ip: str) -> None:
        """Lance un ping continu et permet de l'arreter proprement."""
        win = tk.Toplevel(self.parent)
        win.title("Ping (continu)")
        win.geometry("760x520")
        c = self.theme.colors
        win.configure(bg=c["app_bg"])

        txt = ScrolledText(win, wrap="word")
        txt.pack(fill=BOTH, expand=True, padx=8, pady=8)
        txt.configure(bg=c["tree_bg"], fg=c["tree_fg"], insertbackground=c["tree_fg"])
        txt.insert("1.0", f"Execution ping -t vers {ip}...\n")
        txt.configure(state="disabled")

        controls = Frame(win, bg=c["app_bg"])
        controls.pack(fill="x", padx=8, pady=(0, 8))

        events: queue.Queue = queue.Queue()
        stop_event = threading.Event()
        proc_holder: dict[str, subprocess.Popen] = {}

        def _on_start(proc) -> None:
            proc_holder["proc"] = proc

        def _push(line: str) -> None:
            events.put(("line", line))

        def _stop_and_close() -> None:
            stop_event.set()
            proc = proc_holder.get("proc")
            if proc is not None and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            if win.winfo_exists():
                win.destroy()

        controls.grid_columnconfigure(0, weight=1)
        btn_stop = Button(
            controls,
            text="Stop",
            command=_stop_and_close,
            relief="raised",
            bd=1,
        )
        btn_stop.grid(row=0, column=0)
        apply_control_button_style(btn_stop, c, hovered=False)
        bind_blue_hover(btn_stop, lambda: self.theme.colors)

        def _worker() -> None:
            ok = self.network_tools.stream_ping(
                ip,
                _push,
                continuous=True,
                stop_event=stop_event,
                on_start=_on_start,
            )
            events.put(("done", ok))

        def _poll() -> None:
            if not win.winfo_exists():
                return
            try:
                while True:
                    kind, payload = events.get_nowait()
                    if kind == "line":
                        self._append_tool_line(txt, str(payload))
                    elif kind == "done":
                        status = "OK" if payload else "Arrete"
                        win.title(f"Ping (continu) - {status}")
            except queue.Empty:
                pass
            win.after(120, _poll)

        win.protocol("WM_DELETE_WINDOW", _stop_and_close)
        threading.Thread(target=_worker, daemon=True).start()
        _poll()

    def _add_network_tools_submenu(self, menu: Menu, ip: str, *, at_index: int | None = None) -> None:
        """Ajoute le sous-menu Outils Reseau au menu contextuel."""
        tools = Menu(
            menu,
            tearoff=0,
            bg=self.theme.colors["menu_bg"],
            fg=self.theme.colors["menu_fg"],
        )

        tools.add_command(
            label="Ping",
            command=lambda: self._run_ping_tool_stream(ip),
        )

        def _port_check() -> None:
            port = simpledialog.askinteger(
                "Port check",
                f"Port TCP a tester pour {ip}:",
                parent=self.parent,
                minvalue=1,
                maxvalue=65535,
            )
            if port is None:
                return
            self._run_network_tool(
                "Port check",
                lambda: self.network_tools.port_check(ip, port),
            )

        tools.add_command(label="Port check", command=_port_check)
        tools.add_command(
            label="Traceroute",
            command=lambda: self._run_network_tool_stream(
                "Traceroute",
                lambda on_line: self.network_tools.stream_traceroute(ip, on_line),
            ),
        )

        def _dns_lookup() -> None:
            target = simpledialog.askstring(
                "DNS lookup",
                "Domaine ou IP a resoudre:",
                initialvalue=ip,
                parent=self.parent,
            )
            if not target:
                return
            self._run_network_tool_stream(
                "DNS lookup",
                lambda on_line: self.network_tools.stream_dns_lookup(target.strip(), on_line),
            )

        tools.add_command(label="DNS lookup", command=_dns_lookup)

        def _http_check() -> None:
            url = simpledialog.askstring(
                "HTTP(S) check",
                "URL a verifier (certificat si HTTPS):",
                initialvalue=f"http://{ip}",
                parent=self.parent,
            )
            if not url:
                return
            self._run_network_tool(
                "HTTP(S) check",
                lambda: self.network_tools.http_check(url.strip()),
            )

        tools.add_command(label="HTTP(S) check (avec certificat)", command=_http_check)

        def _snmp_check() -> None:
            community = simpledialog.askstring(
                "SNMP",
                "Community:",
                initialvalue="public",
                parent=self.parent,
            )
            if not community:
                return
            oid = simpledialog.askstring(
                "SNMP",
                "OID:",
                initialvalue="1.3.6.1.2.1.1.1.0",
                parent=self.parent,
            )
            if not oid:
                return
            self._run_network_tool(
                "SNMP",
                lambda: self.network_tools.snmp_check(ip, community.strip(), oid.strip()),
            )

        tools.add_command(label="SNMP", command=_snmp_check)

        if at_index is None:
            menu.add_cascade(label="Outils Réseau", menu=tools)
        else:
            menu.insert_cascade(at_index, label="Outils Réseau", menu=tools)

    def _toggle_notify(self, device_id: Optional[str], var: tk.BooleanVar) -> None:
        """
        Bascule le flag notify pour le device et notifie les vues.
        """
        if not device_id:
            return
        try:
            if self.device_type == "consolidated" and "::" in str(device_id):
                dtype, rid = str(device_id).split("::", 1)
                self.model.notify_flags.setdefault(str(dtype), {})[str(rid)] = var.get()
            else:
                self.model.notify_flags.setdefault(self.device_type, {})[str(device_id)] = var.get()
            self.model.update_json_file()
            self.model._notify_observers()
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
            StatusLogsViewer(self.parent, title="Journal global des changements de statut")
            return

        sel = self.tree.selection()
        if not sel:
            focused = str(self.tree.focus() or "").strip()
            if focused:
                sel = (focused,)
        if not sel:
            StatusLogsViewer(
                self.parent,
                title=f"Journal des changements - {self.device_type}",
                dtype=self.device_type,
            )
            return

        did = str(sel[0])
        dev = self.model.device_data.get(self.device_type, {}).get(did)
        if dev is None:
            StatusLogsViewer(
                self.parent,
                title=f"Journal des changements - {self.device_type}",
                dtype=self.device_type,
            )
            return
        StatusLogsViewer(
            self.parent,
            title=f'Logs {self.device_type} "{dev.name}"',
            dtype=self.device_type,
            device_id=did,
        )

    def _on_selection_mutual(self, _evt=None) -> None:
        """Stub pour selection mutuelle entre vues (a surcharger si besoin)."""
        pass

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
