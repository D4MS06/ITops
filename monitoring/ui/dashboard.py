# src/monitoring/ui/dashboard.py

from __future__ import annotations

import logging
from tkinter import (
    BOTH, LEFT, RIGHT, X,
    Frame, Button, Label, LabelFrame, Tk
)

from monitoring.ui.base_window import BaseWindow
from monitoring.ui.switch_view import SwitchIHM
from monitoring.ui.server_view import ServerIHM
from monitoring.ui.consolidated_view import ConsolidatedView
from monitoring.models.devices_model import DevicesModel
from monitoring.controllers.app_controller import AppController


class DashboardIHM(BaseWindow):
    """Fenêtre principale avec bascule Vue Séparée / Vue Globale."""

    def __init__(self, root: Tk, *, model: DevicesModel, controller: AppController) -> None:
        super().__init__(root, title="Dashboard Monitoring - Multi-vues")
        self.logger = logging.getLogger(__name__)

        # Modèle & contrôleur
        self.model = model
        self.controller = controller
        self.controller.register_view(self)

        # Statut courant
        self.current_view = "separated"

        # Construction de l'interface
        self._build_ui()
        self.center_window()

    def _build_ui(self) -> None:
        """Compose l’UI : header → bannière stat → main_container."""
        self.root.geometry("1200x900")
        self.root.configure(bg="gainsboro")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._create_header()    # titre + boutons
        self._create_banner()    # nom de la vue + compteurs

        # Conteneur unique pour le contenu (Séparée ou Globale)
        self.main_container = Frame(self.root, bg="gainsboro")
        self.main_container.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # Initialisation des vues
        self._create_separated_view()
        self._create_consolidated_view()

        # Affiche par défaut la vue séparée
        self._show_separated_view()

    def _create_header(self) -> None:
        header = Frame(self.root, bg="#34495e", height=70)
        header.pack(fill=X, padx=10, pady=(10, 5))
        header.pack_propagate(False)

        Label(
            header,
            text="🌐 Dashboard Monitoring Réseau",
            font=("Arial", 16, "bold"),
            fg="white", bg="#34495e"
        ).pack(side=LEFT, padx=20)

        # Boutons Vue Séparée / Globale
        btn_frame = Frame(header, bg="#34495e")
        btn_frame.pack(side=RIGHT, padx=20)
        self.btn_separated = Button(
            btn_frame, text="Vue Séparée",
            command=self._show_separated_view,
            bg="#2980b9", fg="white", font=("Arial", 10, "bold")
        )
        self.btn_separated.pack(side=LEFT, padx=5)
        self.btn_consolidated = Button(
            btn_frame, text="Vue Globale",
            command=self._show_consolidated_view,
            bg="#3498db", fg="white", font=("Arial", 10, "bold")
        )
        self.btn_consolidated.pack(side=LEFT, padx=5)

        # Bouton Démarrer / Arrêter Tout
        self.btn_all = Button(
            header, command=self._toggle_all_monitoring,
            font=("Arial", 10, "bold"), relief="raised", bd=2
        )
        self.btn_all.pack(side=RIGHT, padx=5)
        self.update_display()

    def _create_banner(self) -> None:
        """Bannière juste sous le header avec nom de la vue et compteurs."""
        self.banner = Frame(self.root, bg="#2c3e50", height=40)
        self.banner.pack(fill=X, padx=10)
        self.banner.pack_propagate(False)

        # Titre de la vue
        self.lbl_view = Label(
            self.banner, text="", font=("Arial", 14, "bold"),
            fg="white", bg="#2c3e50"
        )
        self.lbl_view.pack(side=LEFT, padx=20)

        # Compteurs (Total / On / Off)
        stats = Frame(self.banner, bg="#2c3e50")
        stats.pack(side=RIGHT, padx=20)
        self.lbl_total = Label(stats, bg="#2c3e50", fg="white")
        self.lbl_total.pack(side=LEFT, padx=5)
        self.lbl_on = Label(stats, bg="#2c3e50", fg="white")
        self.lbl_on.pack(side=LEFT, padx=5)
        self.lbl_off = Label(stats, bg="#2c3e50", fg="white")
        self.lbl_off.pack(side=LEFT, padx=5)

    def _create_separated_view(self) -> None:
        """Crée la vue Switch + Server sans expansion verticale superflue."""
        self.sep_frame = Frame(self.main_container, bg="gainsboro")
        self.sep_frame.pack(fill="x", expand=False, padx=10, pady=5)
        self.sep_frame.columnconfigure(0, weight=1)
        self.sep_frame.columnconfigure(1, weight=1)

        # Panel Switch
        sw_lab = LabelFrame(
            self.sep_frame,
            text="🔀 Switch Monitoring",
            bg="gainsboro",
            font=("Arial", 12, "bold"),
        )
        sw_lab.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Panel Server
        srv_lab = LabelFrame(
            self.sep_frame,
            text="🖥️ Server Monitoring",
            bg="gainsboro",
            font=("Arial", 12, "bold"),
        )
        srv_lab.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Sous-app Switch
        self.switch_app = SwitchIHM(sw_lab, model=self.model, controller=self.controller)
        self.switch_app.pack(fill="x", padx=5, pady=(0, 5))

        # Sous-app Server
        self.server_app = ServerIHM(srv_lab, model=self.model, controller=self.controller)
        self.server_app.pack(fill="x", padx=5, pady=(0, 5))

        # **Bindings de sélection mutuelle**
        self.switch_app.tree.bind("<<TreeviewSelect>>", self._on_switch_select)
        self.server_app.tree.bind("<<TreeviewSelect>>", self._on_server_select)

    def _create_consolidated_view(self) -> None:
        """Crée la vue globale mais ne la packe pas tout de suite."""
        self.cons_frame = Frame(self.main_container, bg="gainsboro")
        # pas de pack ici → invisible initialement

        self.consolidated_app = ConsolidatedView(
            self.cons_frame, model=self.model, controller=self.controller
        )
        self.consolidated_app.pack(fill=BOTH, expand=True)

        # Lier les compteurs de Vue Globale à la bannière
        for var, lbl, fmt in (
            (self.consolidated_app.total_devices, self.lbl_total, "Total : {}"),
            (self.consolidated_app.online_devices, self.lbl_on,    "🟢 On : {}"),
            (self.consolidated_app.offline_devices, self.lbl_off, "🔴 Off : {}"),
        ):
            var.trace_add(
                "write",
                lambda *_,
                       v=var, l=lbl, f=fmt: l.config(text=f.format(v.get()))
            )

    def _show_separated_view(self) -> None:
        """Affiche uniquement la vue séparée et met à jour la bannière."""
        self.cons_frame.pack_forget()
        self.sep_frame.pack(fill=BOTH, expand=True)

        self.btn_separated.config(bg="#2980b9", relief="sunken")
        self.btn_consolidated.config(bg="#3498db", relief="raised")

        self.lbl_view.config(text="📑 Vue Séparée")
        self.current_view = "separated"

    def _show_consolidated_view(self) -> None:
        """Affiche uniquement la vue globale et met à jour la bannière."""
        self.sep_frame.pack_forget()
        self.cons_frame.pack(fill=BOTH, expand=True)

        self.btn_consolidated.config(bg="#2980b9", relief="sunken")
        self.btn_separated.config(bg="#3498db", relief="raised")

        self.lbl_view.config(text="📊 Vue Globale")
        self.current_view = "consolidated"

        self.consolidated_app.start_monitoring()

    def _toggle_all_monitoring(self) -> None:
        """Démarre ou arrête tout selon l’état courant."""
        self.controller.view = self
        if any(self.model.do_run.values()):
            self.controller.stop_all_monitoring()
        else:
            self.controller.start_monitoring("switch")
            self.controller.start_monitoring("server")

    def update_display(self) -> None:
        """Met à jour le libellé du bouton ▶️/⏹."""
        running = any(self.model.do_run.values())
        if running:
            self.btn_all.config(text="⏹ Arrêter Tout", bg="#c0392b", fg="white")
        else:
            self.btn_all.config(text="▶️ Démarrer Tout", bg="#27ae60", fg="white")

    def _on_switch_select(self, _evt) -> None:
        """Lorsque l'on sélectionne un switch, on désélectionne le serveur."""
        try:
            for iid in self.server_app.tree.selection():
                self.server_app.tree.selection_remove(iid)
        except Exception:
            pass

    def _on_server_select(self, _evt) -> None:
        """Lorsque l'on sélectionne un serveur, on désélectionne le switch."""
        try:
            for iid in self.switch_app.tree.selection():
                self.switch_app.tree.selection_remove(iid)
        except Exception:
            pass

    def _on_closing(self) -> None:
        """Arrêt propre puis fermeture de l'application."""
        try:
            self.controller.stop_all_monitoring()
        finally:
            self.root.destroy()
