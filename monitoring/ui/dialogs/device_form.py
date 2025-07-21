from __future__ import annotations

import ipaddress
import logging
import tkinter as tk
from typing import Any

from tkinter import Entry, Label, StringVar, ttk, Frame, messagebox
from tkinter.simpledialog import Dialog

LOGGER = logging.getLogger(__name__)


class DeviceForm(Dialog):
    """Formulaire modal pour Switch / Serveur avec flag notify."""

    LABELS = {"switch": "Switch", "server": "Serveur"}
    REVERSE = {v: k for k, v in LABELS.items()}

    def __init__(
        self,
        parent,
        *,
        title: str,
        default_type: str | None = None,
        initial: dict[str, Any] | None = None,
    ) -> None:
        self.initial = initial or {}
        self.result: dict[str, Any] | None = None
        self.device_type = default_type
        super().__init__(parent, title)

    def body(self, master) -> Frame:
        # variables
        self.var_kind = StringVar()
        self.var_name = StringVar(value=self.initial.get("name", ""))
        self.var_ip = StringVar(value=self.initial.get("ip", ""))
        self.var_desc = StringVar(value=self.initial.get("desc", ""))
        self.var_type = StringVar(value=self.initial.get("subtype", ""))
        self.var_tv = StringVar(value=self.initial.get("tv_id", ""))
        # <-- nouveau flag notify
        self.var_notify = tk.BooleanVar(value=self.initial.get("notify", True))

        # Type d'appareil
        if self.device_type in self.LABELS:
            kind_label = self.LABELS[self.device_type]
        elif self.initial.get("subtype") or self.initial.get("tv_id"):
            kind_label = self.LABELS["server"]
            self.device_type = "server"
        else:
            kind_label = self.LABELS["switch"]
            self.device_type = "switch"
        self.var_kind.set(kind_label)

        Label(master, text="Type d'appareil :").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        self.combo_kind = ttk.Combobox(
            master,
            textvariable=self.var_kind,
            values=list(self.LABELS.values()),
            width=27,
            state="disabled" if self.initial else "readonly",
        )
        self.combo_kind.grid(row=0, column=1, padx=5, sticky="w")
        if not self.initial:
            self.combo_kind.bind("<<ComboboxSelected>>", self._on_type_change)

        Label(master, text="Nom :").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_name, width=30).grid(row=1, column=1, padx=5)

        Label(master, text="IP :").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_ip, width=30).grid(row=2, column=1, padx=5)

        Label(master, text="Description :").grid(row=3, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_desc, width=30).grid(row=3, column=1, padx=5)

        # advanced server fields
        self.advanced_frame = Frame(master)
        self.advanced_frame.grid(row=4, column=0, columnspan=2, sticky="ew")
        self._render_advanced_fields()

        # checkbox notify
        self.chk_notify = ttk.Checkbutton(
            master,
            text="Recevoir une alerte sur changement de statut",
            variable=self.var_notify,
        )
        self.chk_notify.grid(row=5, column=0, columnspan=2, pady=(8, 4))

        return master

    def _render_advanced_fields(self) -> None:
        for w in self.advanced_frame.winfo_children():
            w.destroy()
        if self.var_kind.get() == self.LABELS["server"]:
            Label(self.advanced_frame, text="Type OS :").grid(row=0, column=0, sticky="e", padx=5, pady=4)
            ttk.Combobox(
                self.advanced_frame,
                textvariable=self.var_type,
                values=["Windows", "DSM", "Linux", "Autre"],
                width=27,
            ).grid(row=0, column=1, padx=5)
            Label(self.advanced_frame, text="ID TeamViewer :").grid(row=1, column=0, sticky="e", padx=5, pady=4)
            Entry(self.advanced_frame, textvariable=self.var_tv, width=30).grid(row=1, column=1, padx=5)

    def _on_type_change(self, _evt=None) -> None:
        self._render_advanced_fields()

    def validate(self) -> bool:
        kind = self.REVERSE.get(self.var_kind.get())
        if kind not in {"switch", "server"}:
            messagebox.showerror("Type requis", "Veuillez sélectionner le type d’appareil.")
            return False
        if not self.var_name.get().strip():
            messagebox.showerror("Champ manquant", "Le nom est obligatoire.")
            return False
        try:
            ipaddress.ip_address(self.var_ip.get().strip())
        except ValueError:
            messagebox.showerror("IP invalide", "Adresse IP non valide.")
            return False
        return True

    def apply(self) -> None:
        kind = self.REVERSE[self.var_kind.get()]
        self.result = {
            "kind": kind,
            "name": self.var_name.get().strip(),
            "ip": self.var_ip.get().strip(),
            "desc": self.var_desc.get().strip(),
            "notify": self.var_notify.get(),
        }
        if kind == "server":
            self.result["subtype"] = self.var_type.get().strip()
            self.result["tv_id"] = self.var_tv.get().strip()
