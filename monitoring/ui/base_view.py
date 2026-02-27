# monitoring/ui/base_view.py

from __future__ import annotations

import ipaddress
import logging
import webbrowser
from pathlib import Path
from tkinter import (
    Frame,
    Menu,
    PhotoImage,
    Button,
    Label,
    messagebox,
    BOTH,
    LEFT,
    TOP,
)
from tkinter import ttk
from typing import Sequence, Optional, Any

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.base_window import resource_path
from monitoring.ui.view_mixins import ContextMenuMixin
from monitoring.ui.utils.sortable_tree import make_treeview_sortable

LOGGER = logging.getLogger(__name__)


class DeviceListView(ContextMenuMixin):
    """BaseView pour toutes les vues listant des devices (switch, server, global).

    • Définit le Treeview, le bouton ▶️/⏹ et le menu contextuel générique.
    • Implémente update_display(), tri, pause/reprise via ContextMenuMixin.
    • Les sous-classes doivent spécifier :
      – device_type: str = "switch" ou "server"
      – columns: Sequence[str]
      – headings: dict[str,str]
      – tag_configs (optionnel) pour coloration des lignes
      – _on_add(), _on_edit(), _on_delete(), _on_double_click()
      – (optionnel) _on_selection_mutual() pour désélection mutuelle
    """

    device_type: str = ""
    columns: Sequence[str] = ()
    headings: dict[str, str] = {}
    tag_configs: dict[str, dict[str, Any]] = {}

    def __init__(
        self,
        parent: Frame,
        *,
        model: DevicesModel | None = None,
        controller: AppController | None = None,
    ) -> None:
        super().__init__()
        self.parent = parent
        self.model = model or DevicesModel()
        self.controller = controller or AppController(self.model, self)
        self.controller.view = self
        self.controller.register_view(self)

        # Tri
        self.sort_col: Optional[str] = None
        self.sort_reverse = False

        # Pause d'actualisation
        self.refresh_paused = False
        self._last_iid: Optional[str] = None

        # Icônes de statut
        self._load_icons()

        # Construction de l'UI
        self._build_ui()

        # Affichage initial
        self.update_display()

    def _load_icons(self) -> None:
        """Charge les icônes online/offline/idle depuis assets."""
        base = Path("monitoring/ui/assets")
        p = resource_path
        self.img_online = PhotoImage(file=p(base / "online.png"))
        self.img_offline = PhotoImage(file=p(base / "offline.png"))
        self.img_idle = PhotoImage(file=p(base / "idle.png"))
        self.img_monitoring_paused = None
        try:
            self.img_monitoring_paused = PhotoImage(file=p(base / "monitoring_paused.png"))
        except Exception:
            self.img_monitoring_paused = None

    def _build_ui(self) -> None:
        """Construit le Treeview, le bouton toggle et les bindings."""
        cont = Frame(self.parent, bg="gainsboro")
        cont.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # Treeview
        self.tree = ttk.Treeview(
            cont,
            columns=self.columns,
            show=("tree", "headings"),
            height=15,
            selectmode="browse",
        )
        make_treeview_sortable(self.tree, self)

        # Colonne d'icône
        self.tree.heading("#0", text="Statut")
        self.tree.column("#0", width=40, anchor="center")

        # Colonnes métier
        for col in self.columns:
            self.tree.heading(col, text=self.headings.get(col, col.capitalize()))
            self.tree.column(col, anchor="w")

        # Tags pour coloration
        for tag, cfg in self.tag_configs.items():
            self.tree.tag_configure(tag, **cfg)

        # Scrollbar
        self.tree_scrollbar = ttk.Scrollbar(cont, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=self.tree_scrollbar.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree_scrollbar.pack(side=LEFT, fill="y")

        self.placeholder = Frame(cont, bg="#e9edf2")
        self.placeholder_image = Label(
            self.placeholder,
            image=self.img_monitoring_paused,
            bg="#e9edf2",
        )
        self.placeholder_image.pack(pady=(24, 10))
        self.placeholder_title = Label(
            self.placeholder,
            text="Monitoring arrete",
            bg="#e9edf2",
            fg="#0f172a",
            font=("Segoe UI", 12, "bold"),
        )
        self.placeholder_title.pack()
        self.placeholder_subtitle = Label(
            self.placeholder,
            text="Demarrez la sonde pour afficher les equipements en temps reel.",
            bg="#e9edf2",
            fg="#475569",
            font=("Segoe UI", 10),
        )
        self.placeholder_subtitle.pack(pady=(6, 0))
        self._placeholder_visible = False

        # Bouton ▶️/⏹
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

        # Sélection mutuelle
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_mutual)

        # Menu contextuel avec pause/reprise
        self.bind_context_menu_with_pause(
            tree=self.tree,
            menu_builder=self._build_context_menu,
        )

        # Double-clic
        self.tree.bind("<Double-1>", self._on_double_click)

    def _build_context_menu(self) -> Menu:
        """Menu commun : CRUD + toggle monitoring."""
        menu = Menu(self.parent, tearoff=0, bg="gainsboro")
        menu.add_command(label="Ajouter", command=self._on_add)
        menu.add_command(label="Modifier", command=self._on_edit)
        menu.add_command(label="Supprimer", command=self._on_delete)
        menu.add_separator()
        running = self.model.do_run.get(self.device_type, False)
        menu.add_command(
            label="⏹ Arrêter" if running else "▶️ Démarrer",
            command=self._toggle_monitoring,
        )
        return menu

    def update_display(self) -> None:
        """Vide et remplit le Treeview depuis le modèle, puis met à jour le bouton."""
        if self.refresh_paused or self.is_locked_view():
            return

        try:
            self.tree.delete(*self.tree.get_children())

            items = list(self.model.device_data.get(self.device_type, {}).items())
            if self.sort_col:
                key = (
                    lambda x: ipaddress.ip_address(x[1].ip)
                    if self.sort_col == "ip"
                    else getattr(x[1], self.sort_col).lower()
                )
                items.sort(key=key, reverse=self.sort_reverse)

            for did, dev in items:
                icon = {
                    "online": self.img_online,
                    "offline": self.img_offline,
                    "idle": self.img_idle,
                }[dev.status]

                values = tuple(
                    getattr(dev, col) if col != "desc" else dev.description
                    for col in self.columns
                )

                self.tree.insert(
                    "",
                    "end",
                    iid=did,
                    image=icon,
                    values=values,
                    tags=(dev.status,),
                )

            running = self.model.do_run.get(self.device_type, False)
            self.btn_toggle.config(
                text="⏹ Arrêter" if running else "▶️ Démarrer",
                bg="#c0392b" if running else "#27ae60",
                fg="white",
            )
            self._set_placeholder_visible(
                not running,
                title="Monitoring arrete",
                subtitle="Demarrez la sonde pour afficher les equipements en temps reel.",
            )

        except Exception as exc:
            LOGGER.exception("update_display %s : %s", self.device_type, exc)


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

    def _toggle_monitoring(self) -> None:
        """Démarre ou arrête le monitoring via l’AppController."""
        self.controller.view = self
        if self.model.do_run.get(self.device_type, False):
            self.controller.stop_monitoring(self.device_type)
        else:
            self.controller.start_monitoring(self.device_type)

    def _on_selection_mutual(self, _evt=None) -> None:
        """À surcharger : désélection mutuelle entre vues."""
        pass

    # ——— À implémenter en sous-classe ———

    def _on_add(self) -> None:
        raise NotImplementedError

    def _on_edit(self) -> None:
        raise NotImplementedError

    def _on_delete(self) -> None:
        raise NotImplementedError

    def _on_double_click(self, _evt=None) -> None:
        raise NotImplementedError
