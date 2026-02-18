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
from monitoring.controllers.network_tools_controller import NetworkToolsController
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
        self.network_tools = NetworkToolsController()

        self.sort_col = None
        self.sort_reverse = False
        self.refresh_paused = False
        self._rendered_iids: set[str] = set()
        self._row_state: dict[str, tuple[str, tuple[Any, ...]]] = {}
        self.search_var = tk.StringVar(value="")
        self.show_local_monitoring_button = True

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
        cont = Frame(self.parent, bg="gainsboro")
        cont.pack(fill=BOTH, expand=True, padx=5, pady=5)

        btnf = Frame(cont, bg="gainsboro")
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

        search_row = Frame(cont, bg="gainsboro")
        search_row.pack(fill=X, padx=2, pady=(2, 6))
        self._search_row = search_row
        ttk.Label(search_row, text="Recherche:").pack(side=LEFT, padx=(2, 6))
        self.entry_search = ttk.Entry(search_row, textvariable=self.search_var)
        self.entry_search.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(search_row, text="Effacer", command=self._clear_search).pack(side=RIGHT, padx=(6, 0))
        self.search_var.trace_add("write", self._on_search_change)
        self._apply_monitoring_button_visibility()

        tree_wrap = Frame(cont, bg="gainsboro")
        tree_wrap.pack(fill=BOTH, expand=True)

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

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=LEFT, fill="y")

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
            bg="#27ae60" if running else "#9e9e9e",
            activebackground="#27ae60" if running else "#9e9e9e",
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

    def _show_tool_output(self, title: str, output: str) -> None:
        """Affiche le resultat d'un outil reseau."""
        win = tk.Toplevel(self.parent)
        win.title(title)
        win.geometry("760x480")
        txt = ScrolledText(win, wrap="word")
        txt.pack(fill=BOTH, expand=True, padx=8, pady=8)
        txt.insert("1.0", output or "Aucune sortie.")
        txt.configure(state="disabled")

    def _open_tool_output_window(self, title: str):
        win = tk.Toplevel(self.parent)
        win.title(title)
        win.geometry("760x480")
        txt = ScrolledText(win, wrap="word")
        txt.pack(fill=BOTH, expand=True, padx=8, pady=8)
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

        txt = ScrolledText(win, wrap="word")
        txt.pack(fill=BOTH, expand=True, padx=8, pady=8)
        txt.insert("1.0", f"Execution ping -t vers {ip}...\n")
        txt.configure(state="disabled")

        controls = Frame(win, bg="gainsboro")
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
        ttk.Button(controls, text="Stop", command=_stop_and_close).grid(
            row=0, column=0
        )

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
        tools = Menu(menu, tearoff=0, bg="gainsboro")

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
