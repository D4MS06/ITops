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
    BOTH,
    LEFT,
    TOP,
    ttk,
)
from typing import Any, Optional, Sequence

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.base_window import resource_path
from monitoring.ui.view_mixins import ContextMenuMixin
from monitoring.ui.utils.sortable_tree import make_treeview_sortable

LOGGER = logging.getLogger(__name__)


class DeviceListView(Frame, ContextMenuMixin):
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

        self.sort_col = None
        self.sort_reverse = False
        self.refresh_paused = False

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
            self.img_online = PhotoImage(file=p(base / "online.png"))
            self.img_offline = PhotoImage(file=p(base / "offline.png"))
            self.img_idle = PhotoImage(file=p(base / "idle.png"))
        except Exception:
            LOGGER.exception("Erreur chargement icones")

    def _build_ui(self) -> None:
        """Construit le Treeview, le scrollbar, le bouton toggle et les bindings."""
        is_global = (self.device_type == "consolidated")
        cont = Frame(self.parent, bg="gainsboro")
        cont.pack(fill=BOTH, expand=is_global, padx=5, pady=5)

        self.tree = ttk.Treeview(
            cont,
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

        vsb = ttk.Scrollbar(cont, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(side=LEFT, fill=BOTH if is_global else "x", expand=is_global)
        vsb.pack(side=LEFT, fill="y")

        btnf = Frame(self.parent, bg="gainsboro")
        btnf.pack(side=TOP, pady=5)
        self.btn_toggle = Button(
            btnf,
            command=self._toggle_monitoring,
            font=("Arial", 10, "bold"),
            relief="raised",
            bd=2,
        )
        self.btn_toggle.pack(side=LEFT, padx=5)

        # Bindings
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_mutual)
        self.bind_context_menu_with_pause(
            tree=self.tree, menu_builder=self._build_context_menu
        )
        self.tree.bind("<Double-1>", self._on_double_click)

    def update_display(self) -> None:
        """
        Met a jour les lignes du Treeview selon model.device_data[self.device_type]
        et ajuste le texte/couleur du bouton toggle.
        """
        if self.refresh_paused or self.is_locked_view():
            return

        items = list(self.model.device_data.get(self.device_type, {}).items())
        if self.device_type != "consolidated":
            self.tree.config(height=max(len(items), 5))
        self.tree.delete(*self.tree.get_children())

        if self.sort_col:
            items.sort(
                key=lambda x: (
                    ipaddress.ip_address(x[1].ip)
                    if self.sort_col == "ip"
                    else getattr(x[1], self.sort_col).lower()
                ),
                reverse=self.sort_reverse,
            )

        for did, dev in items:
            icon = {
                "online": self.img_online,
                "offline": self.img_offline,
                "idle": self.img_idle,
            }[dev.status]
            values = tuple(
                getattr(dev, c) if c != "desc" else dev.description
                for c in self.columns
            )
            self.tree.insert(
                "", "end", iid=did, image=icon, values=values, tags=(dev.status,)
            )

        running = self.model.do_run.get(self.device_type, False)
        self.btn_toggle.config(
            text="Arreter" if running else "Demarrer",
            bg="#c0392b" if running else "#27ae60",
            fg="white",
        )

    def _build_context_menu(self) -> Menu:
        """
        Construit le menu contextuel commun : Ajouter / Modifier / Supprimer /
        Alerte (sans gestion du monitoring).
        """
        menu = Menu(self.parent, tearoff=0, bg="gainsboro")
        menu.add_command(label="Ajouter", command=self._on_add)
        menu.add_command(label="Modifier", command=self._on_edit)
        menu.add_command(label="Supprimer", command=self._on_delete)
        menu.add_separator()

        # Checkbutton pour le flag notify
        sel = self.tree.selection()
        did = sel[0] if sel else None
        current = False
        if did:
            current = self.model.notify_flags[self.device_type].get(did, False)
        var = tk.BooleanVar(value=current)
        menu.add_checkbutton(
            label="Alerte sur changement de statut",
            variable=var,
            command=lambda d=did, v=var: self._toggle_notify(d, v),
        )

        return menu

    def _toggle_notify(self, device_id: Optional[str], var: tk.BooleanVar) -> None:
        """
        Bascule le flag notify pour le device et notifie les vues.
        """
        if not device_id:
            return
        try:
            self.model.notify_flags[self.device_type][device_id] = var.get()
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
