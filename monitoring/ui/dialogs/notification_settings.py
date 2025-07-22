from __future__ import annotations

from tkinter import (
    Frame, Label, Entry, BooleanVar, Checkbutton, StringVar,
    Button, ACTIVE
)
from tkinter import messagebox as mb
from tkinter.simpledialog import Dialog

from monitoring.config.settings import NotificationSettings
from monitoring.utils.alerts import send_alert_email  # adapte si ton module s'appelle autrement


class NotificationSettingsDialog(Dialog):
    """Dialog modal pour configurer l'envoi d'emails de notification."""

    def __init__(self, parent, settings: NotificationSettings) -> None:
        self.settings = settings
        self.result: NotificationSettings | None = None
        super().__init__(parent, title="Paramètres de notification")

    # --
    # Construction UI
    def body(self, master: Frame) -> Frame:
        self.var_host = StringVar(value=self.settings.smtp_host)
        self.var_port = StringVar(value=str(self.settings.smtp_port))
        self.var_user = StringVar(value=self.settings.user)
        self.var_password = StringVar(value=self.settings.password)
        self.var_tls = BooleanVar(value=self.settings.use_tls)
        self.var_rcpt = StringVar(value=self.settings.recipients)

        Label(master, text="Hôte SMTP:").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_host, width=30).grid(row=0, column=1, padx=5)
        Label(master, text="Port:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_port, width=30).grid(row=1, column=1, padx=5)
        Label(master, text="Utilisateur:").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_user, width=30).grid(row=2, column=1, padx=5)
        Label(master, text="Mot de passe:").grid(row=3, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_password, width=30, show="*").grid(row=3, column=1, padx=5)
        Checkbutton(master, text="Utiliser TLS", variable=self.var_tls).grid(row=4, column=0, columnspan=2, pady=4)
        Label(master, text="Destinataires:").grid(row=5, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_rcpt, width=30).grid(row=5, column=1, padx=5)
        return master

    def buttonbox(self) -> None:
        box = Frame(self)
        Button(box, text="OK", width=10, command=self.ok, default=ACTIVE).pack(side="left", padx=5, pady=5)
        Button(box, text="Tester", width=10, command=self._on_test).pack(side="left", padx=5, pady=5)
        Button(box, text="Annuler", width=10, command=self.cancel).pack(side="right", padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def apply(self) -> None:
        self.result = NotificationSettings(
            smtp_host=self.var_host.get().strip(),
            smtp_port=int(self.var_port.get() or 0),
            user=self.var_user.get().strip(),
            password=self.var_password.get(),
            use_tls=self.var_tls.get(),
            recipients=self.var_rcpt.get().strip(),
        )

    def _gather_settings(self) -> NotificationSettings:
        return NotificationSettings(
            smtp_host=self.var_host.get().strip(),
            smtp_port=int(self.var_port.get() or 0),
            user=self.var_user.get().strip(),
            password=self.var_password.get(),
            use_tls=self.var_tls.get(),
            recipients=self.var_rcpt.get().strip(),
        )

    def _on_test(self) -> None:
        try:
            # adapte l'appel à ta signature réelle de send_alert_email
            send_alert_email(
                ["test@example.com"],  # ou self.var_rcpt.get().split(",")
                "Test notification",
                "Ceci est un email de test.",
            )
            mb.showinfo("Test envoyé", "Email de test envoyé")
        except Exception as exc:
            mb.showerror("Erreur", f"Impossible d'envoyer l'email: {exc}")
