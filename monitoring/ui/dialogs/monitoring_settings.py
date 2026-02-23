from __future__ import annotations

from tkinter import ACTIVE, Button, Entry, Frame, Label, StringVar
from tkinter import messagebox as mb
from tkinter.simpledialog import Dialog


class MonitoringSettingsDialog(Dialog):
    """Dialog modal pour configurer les delais de monitoring et le cooldown d'alertes."""

    def __init__(
        self,
        parent,
        offline_delay_seconds: int,
        online_recovery_delay_seconds: int,
        notification_cooldown_seconds: int,
    ) -> None:
        self.offline_delay_seconds = max(1, int(offline_delay_seconds or 5))
        self.online_recovery_delay_seconds = max(
            1, int(online_recovery_delay_seconds or self.offline_delay_seconds)
        )
        self.notification_cooldown_seconds = max(0, int(notification_cooldown_seconds or 0))
        self.result: dict[str, int] | None = None
        super().__init__(parent, title="Parametres monitoring")

    def body(self, master: Frame) -> Frame:
        self.var_offline_delay = StringVar(value=str(self.offline_delay_seconds))
        self.var_online_delay = StringVar(value=str(self.online_recovery_delay_seconds))
        self.var_cooldown = StringVar(value=str(self.notification_cooldown_seconds))

        Label(master, text="Delai hors ligne (secondes):").grid(
            row=0, column=0, sticky="e", padx=5, pady=6
        )
        Entry(master, textvariable=self.var_offline_delay, width=12).grid(
            row=0, column=1, sticky="w", padx=5, pady=6
        )
        Label(master, text="Delai retour en ligne stable (secondes):").grid(
            row=1, column=0, sticky="e", padx=5, pady=6
        )
        Entry(master, textvariable=self.var_online_delay, width=12).grid(
            row=1, column=1, sticky="w", padx=5, pady=6
        )
        Label(master, text="Frequence max des alertes par equipement (secondes, 0 = illimite):").grid(
            row=2, column=0, sticky="e", padx=5, pady=6
        )
        Entry(master, textvariable=self.var_cooldown, width=12).grid(
            row=2, column=1, sticky="w", padx=5, pady=6
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
        raw_offline = self.var_offline_delay.get().strip()
        raw_online = self.var_online_delay.get().strip()
        raw_cooldown = self.var_cooldown.get().strip()
        try:
            offline_delay = int(raw_offline)
            online_delay = int(raw_online)
            cooldown = int(raw_cooldown)
        except Exception:
            mb.showerror("Valeur invalide", "Entrez un nombre entier de secondes.")
            return False
        if offline_delay < 1:
            mb.showerror("Valeur invalide", "Le delai doit etre superieur ou egal a 1 seconde.")
            return False
        if online_delay < 1:
            mb.showerror(
                "Valeur invalide",
                "Le delai de retour en ligne doit etre superieur ou egal a 1 seconde.",
            )
            return False
        if cooldown < 0:
            mb.showerror(
                "Valeur invalide",
                "La frequence max des alertes par equipement doit etre superieure ou egale a 0 seconde.",
            )
            return False
        self.result = {
            "offline_delay_seconds": offline_delay,
            "online_recovery_delay_seconds": online_delay,
            "notification_cooldown_seconds": cooldown,
        }
        return True
