from __future__ import annotations

from tkinter import ACTIVE, BooleanVar, Button, Checkbutton, Entry, Frame, Label, StringVar
from tkinter import messagebox as mb

from monitoring.services.web_server_manager import WebServerState
from monitoring.ui.dialogs.themed_dialog import ThemedDialog


class WebServerSettingsDialog(ThemedDialog):
    def __init__(
        self,
        parent,
        *,
        host: str,
        port: int,
        autostart: bool,
        state_provider,
        on_save,
        on_toggle,
        on_restart,
        on_open_browser,
    ) -> None:
        self._state_provider = state_provider
        self._on_save = on_save
        self._on_toggle = on_toggle
        self._on_restart = on_restart
        self._on_open_browser = on_open_browser
        self._initial_host = str(host or "127.0.0.1").strip() or "127.0.0.1"
        self._initial_port = max(1, int(port or 8000))
        self._initial_autostart = bool(autostart)
        self.result: dict[str, object] | None = None
        super().__init__(parent, title="Gestion du serveur web")

    def body(self, master: Frame) -> Frame:
        self.var_host = StringVar(value=self._initial_host)
        self.var_port = StringVar(value=str(self._initial_port))
        self.var_autostart = BooleanVar(value=self._initial_autostart)
        self.var_state = StringVar(value="")
        self.var_url = StringVar(value="")

        Label(master, text="Etat", anchor="w").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        Label(master, textvariable=self.var_state, anchor="w").grid(row=0, column=1, sticky="w", padx=8, pady=(8, 4))

        Label(master, text="URL", anchor="w").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        Label(master, textvariable=self.var_url, anchor="w").grid(row=1, column=1, sticky="w", padx=8, pady=4)

        Label(master, text="Host", anchor="w").grid(row=2, column=0, sticky="w", padx=8, pady=(10, 4))
        Entry(master, textvariable=self.var_host, width=20).grid(row=2, column=1, sticky="ew", padx=8, pady=(10, 4))

        Label(master, text="Port", anchor="w").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        Entry(master, textvariable=self.var_port, width=10, justify="right").grid(row=3, column=1, sticky="w", padx=8, pady=4)

        Checkbutton(
            master,
            text="Demarrer automatiquement avec le desktop",
            variable=self.var_autostart,
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 8))

        actions = Frame(master, bg=self.theme.colors["app_bg"])
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 8))
        self.btn_toggle = Button(actions, text="", width=14, command=self._handle_toggle)
        self.btn_toggle.pack(side="left", padx=(0, 6))
        self.btn_restart = Button(actions, text="Redemarrer", width=12, command=self._handle_restart)
        self.btn_restart.pack(side="left", padx=6)
        self.btn_open = Button(actions, text="Ouvrir", width=10, command=self._handle_open)
        self.btn_open.pack(side="left", padx=6)
        for btn in (self.btn_toggle, self.btn_restart, self.btn_open):
            self.style_button(btn)

        master.grid_columnconfigure(1, weight=1)
        self._refresh_state_widgets()
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        btn_ok = Button(box, text="Enregistrer", width=12, command=self.ok, default=ACTIVE)
        btn_ok.pack(side="left", padx=5, pady=5)
        btn_cancel = Button(box, text="Fermer", width=10, command=self.cancel)
        btn_cancel.pack(side="right", padx=5, pady=5)
        for btn in (btn_ok, btn_cancel):
            self.style_button(btn)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()
        self.apply_theme(self)

    def validate(self) -> bool:
        payload = self._collect_payload()
        if payload is None:
            return False
        try:
            self._on_save(payload["host"], payload["port"], payload["autostart"])
        except Exception as exc:
            mb.showerror("Serveur web", f"Impossible d'enregistrer les parametres: {exc}")
            return False
        self.result = payload
        return True

    def _collect_payload(self) -> dict[str, object] | None:
        host = self.var_host.get().strip() or "127.0.0.1"
        raw_port = self.var_port.get().strip()
        try:
            port = int(raw_port)
        except Exception:
            mb.showerror("Valeur invalide", "Le port du serveur web doit etre un entier valide.")
            return None
        if port < 1 or port > 65535:
            mb.showerror("Valeur invalide", "Le port du serveur web doit etre compris entre 1 et 65535.")
            return None
        return {
            "host": host,
            "port": port,
            "autostart": bool(self.var_autostart.get()),
        }

    def _refresh_state_widgets(self) -> None:
        state: WebServerState = self._state_provider()
        self.var_state.set("Actif" if state.running else "Arrete")
        self.var_url.set(state.url)
        self.btn_toggle.configure(text="Arreter" if state.running else "Demarrer")

    def _handle_toggle(self) -> None:
        payload = self._collect_payload()
        if payload is None:
            return
        try:
            self._on_save(payload["host"], payload["port"], payload["autostart"])
            self._on_toggle(payload["host"], payload["port"])
            self.after(500, self._refresh_state_widgets)
        except Exception as exc:
            mb.showerror("Serveur web", f"Operation impossible: {exc}")

    def _handle_restart(self) -> None:
        payload = self._collect_payload()
        if payload is None:
            return
        try:
            self._on_save(payload["host"], payload["port"], payload["autostart"])
            self._on_restart(payload["host"], payload["port"])
            self.after(500, self._refresh_state_widgets)
        except Exception as exc:
            mb.showerror("Serveur web", f"Redemarrage impossible: {exc}")

    def _handle_open(self) -> None:
        payload = self._collect_payload()
        if payload is None:
            return
        try:
            self._on_save(payload["host"], payload["port"], payload["autostart"])
            self._on_open_browser(payload["host"], payload["port"])
            self.after(500, self._refresh_state_widgets)
        except Exception as exc:
            mb.showerror("Serveur web", f"Ouverture impossible: {exc}")
