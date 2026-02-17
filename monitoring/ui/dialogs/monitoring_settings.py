from __future__ import annotations

from tkinter import ACTIVE, Button, Entry, Frame, Label, StringVar
from tkinter import messagebox as mb
from tkinter.simpledialog import Dialog


class MonitoringSettingsDialog(Dialog):
    """Dialog modal pour configurer le delai avant statut hors ligne."""

    def __init__(self, parent, offline_delay_seconds: int) -> None:
        self.offline_delay_seconds = max(1, int(offline_delay_seconds or 5))
        self.result: int | None = None
        super().__init__(parent, title="Parametres monitoring")

    def body(self, master: Frame) -> Frame:
        self.var_delay = StringVar(value=str(self.offline_delay_seconds))
        Label(master, text="Delai hors ligne (secondes):").grid(
            row=0, column=0, sticky="e", padx=5, pady=6
        )
        Entry(master, textvariable=self.var_delay, width=12).grid(
            row=0, column=1, sticky="w", padx=5, pady=6
        )
        return master

    def buttonbox(self) -> None:
        box = Frame(self)
        Button(box, text="OK", width=10, command=self.ok, default=ACTIVE).pack(
            side="left", padx=5, pady=5
        )
        Button(box, text="Annuler", width=10, command=self.cancel).pack(
            side="right", padx=5, pady=5
        )
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def validate(self) -> bool:
        raw = self.var_delay.get().strip()
        try:
            val = int(raw)
        except Exception:
            mb.showerror("Valeur invalide", "Entrez un nombre entier de secondes.")
            return False
        if val < 1:
            mb.showerror("Valeur invalide", "Le delai doit etre superieur ou egal a 1 seconde.")
            return False
        self.result = val
        return True

