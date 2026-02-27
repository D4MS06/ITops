from __future__ import annotations

from tkinter import (
    ACTIVE,
    END,
    SINGLE,
    BooleanVar,
    Button,
    Checkbutton,
    Entry,
    Frame,
    Label,
    Listbox,
    StringVar,
)
from tkinter import messagebox as mb

from monitoring.config.settings import NotificationSettings
from monitoring.ui.dialogs.themed_dialog import ThemedDialog
from monitoring.utils.notifications import send_alert_email


class NotificationSettingsDialog(ThemedDialog):
    """Dialog modal pour configurer l'envoi d'emails de notification."""
    _PASSWORD_MASK = "*****"

    def __init__(self, parent, settings: NotificationSettings) -> None:
        self.settings = settings
        self._had_saved_password = bool(settings.password)
        self.result: NotificationSettings | None = None
        super().__init__(parent, title="Parametres de notification")

    def body(self, master: Frame) -> Frame:
        self.var_host = StringVar(value=self.settings.smtp_host)
        self.var_port = StringVar(value=str(self.settings.smtp_port))
        self.var_user = StringVar(value=self.settings.user)
        # Affiche un masque si un secret existe deja, sans exposer sa valeur.
        self.var_password = StringVar(
            value=self._PASSWORD_MASK if self._had_saved_password else ""
        )
        self.var_tls = BooleanVar(value=self.settings.use_tls)
        self.var_popup = BooleanVar(value=bool(getattr(self.settings, "show_status_popup", True)))
        self.var_rcpt = StringVar(value="")

        Label(master, text="Hote SMTP:").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_host, width=30).grid(row=0, column=1, padx=5)
        Label(master, text="Port:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_port, width=30).grid(row=1, column=1, padx=5)
        Label(master, text="Utilisateur:").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_user, width=30).grid(row=2, column=1, padx=5)
        Label(master, text="Mot de passe:").grid(row=3, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_password, width=30, show="*").grid(row=3, column=1, padx=5)
        Checkbutton(
            master,
            text="Utiliser TLS",
            variable=self.var_tls,
            command=self._on_tls_toggle,
        ).grid(row=5, column=0, columnspan=2, pady=4)
        Label(master, text="Destinataire:").grid(row=6, column=0, sticky="e", padx=5, pady=4)

        rcpt_row = Frame(master)
        rcpt_row.grid(row=6, column=1, sticky="we", padx=5, pady=2)
        Entry(rcpt_row, textvariable=self.var_rcpt, width=28).pack(side="left")
        btn_add = Button(rcpt_row, text="+", width=3, command=self._add_recipient)
        btn_add.pack(side="left", padx=(4, 0))
        btn_remove = Button(rcpt_row, text="-", width=3, command=self._remove_selected_recipient)
        btn_remove.pack(side="left", padx=(4, 0))
        self.style_button(btn_add)
        self.style_button(btn_remove)

        Label(master, text="Liste:").grid(row=7, column=0, sticky="ne", padx=5, pady=4)
        self.lst_recipients = Listbox(master, width=32, height=6, selectmode=SINGLE)
        self.lst_recipients.grid(row=7, column=1, sticky="we", padx=5, pady=(2, 4))

        for addr in self._parse_recipients(self.settings.recipients):
            self.lst_recipients.insert(END, addr)

        Checkbutton(
            master,
            text="Afficher la fenetre de notification changement de statut",
            variable=self.var_popup,
        ).grid(row=8, column=0, columnspan=2, sticky="w", padx=5, pady=(2, 4))

        master.grid_columnconfigure(1, weight=1)
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        btn_ok = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        btn_ok.pack(side="left", padx=5, pady=5)
        btn_test = Button(box, text="Tester", width=10, command=self._on_test)
        btn_test.pack(side="left", padx=5, pady=5)
        btn_cancel = Button(box, text="Annuler", width=10, command=self.cancel)
        btn_cancel.pack(side="right", padx=5, pady=5)
        for btn in (btn_ok, btn_test, btn_cancel):
            self.style_button(btn)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()
        self.apply_theme(self)

    def _resolved_password(self) -> str:
        entered = self.var_password.get()
        if entered == self._PASSWORD_MASK and self._had_saved_password:
            return self.settings.password or ""
        return entered

    def _on_tls_toggle(self) -> None:
        self.var_port.set("587" if self.var_tls.get() else "25")

    def apply(self) -> None:
        self.result = NotificationSettings(
            smtp_host=self.var_host.get().strip(),
            smtp_port=int(self.var_port.get() or 0),
            user=self.var_user.get().strip(),
            password=self._resolved_password(),
            use_tls=self.var_tls.get(),
            recipients=", ".join(self._listbox_recipients()),
            offline_delay_seconds=max(1, int(getattr(self.settings, "offline_delay_seconds", 5) or 5)),
            online_recovery_delay_seconds=max(
                1,
                int(
                    getattr(
                        self.settings,
                        "online_recovery_delay_seconds",
                        getattr(self.settings, "offline_delay_seconds", 5),
                    )
                    or getattr(self.settings, "offline_delay_seconds", 5)
                ),
            ),
            notification_cooldown_seconds=max(
                0, int(getattr(self.settings, "notification_cooldown_seconds", 120) or 0)
            ),
            failures_for_offline=max(1, int(getattr(self.settings, "failures_for_offline", 3) or 3)),
            successes_for_online=max(1, int(getattr(self.settings, "successes_for_online", 2) or 2)),
            ping_timeout_ms=max(250, int(getattr(self.settings, "ping_timeout_ms", 1500) or 1500)),
            probe_interval_ms=max(250, int(getattr(self.settings, "probe_interval_ms", 1000) or 1000)),
            log_diagnostic_events=bool(getattr(self.settings, "log_diagnostic_events", False)),
            show_status_popup=self.var_popup.get(),
            updates_enabled=bool(getattr(self.settings, "updates_enabled", False)),
            github_owner="D4MS06",
            github_repo="NetworkMonitoringProject",
            github_token=str(getattr(self.settings, "github_token", "")).strip(),
            include_prerelease=bool(getattr(self.settings, "include_prerelease", False)),
            update_target_tag=str(getattr(self.settings, "update_target_tag", "latest") or "latest").strip(),
            updates_connection_validated=bool(getattr(self.settings, "updates_connection_validated", False)),
            watermark_image_path=str(getattr(self.settings, "watermark_image_path", "")).strip(),
            watermark_source_path=str(getattr(self.settings, "watermark_source_path", "")).strip(),
            watermark_opacity=float(getattr(self.settings, "watermark_opacity", 0.16) or 0.16),
            ui_theme=str(getattr(self.settings, "ui_theme", "light") or "light").strip().lower(),
            theme_overrides_json=str(getattr(self.settings, "theme_overrides_json", "") or "").strip(),
            status_indicator_style=str(getattr(self.settings, "status_indicator_style", "badge") or "badge").strip().lower(),
        )

    def _gather_settings(self) -> NotificationSettings:
        return NotificationSettings(
            smtp_host=self.var_host.get().strip(),
            smtp_port=int(self.var_port.get() or 0),
            user=self.var_user.get().strip(),
            password=self._resolved_password(),
            use_tls=self.var_tls.get(),
            recipients=", ".join(self._listbox_recipients()),
            offline_delay_seconds=max(1, int(getattr(self.settings, "offline_delay_seconds", 5) or 5)),
            online_recovery_delay_seconds=max(
                1,
                int(
                    getattr(
                        self.settings,
                        "online_recovery_delay_seconds",
                        getattr(self.settings, "offline_delay_seconds", 5),
                    )
                    or getattr(self.settings, "offline_delay_seconds", 5)
                ),
            ),
            notification_cooldown_seconds=max(
                0, int(getattr(self.settings, "notification_cooldown_seconds", 120) or 0)
            ),
            failures_for_offline=max(1, int(getattr(self.settings, "failures_for_offline", 3) or 3)),
            successes_for_online=max(1, int(getattr(self.settings, "successes_for_online", 2) or 2)),
            ping_timeout_ms=max(250, int(getattr(self.settings, "ping_timeout_ms", 1500) or 1500)),
            probe_interval_ms=max(250, int(getattr(self.settings, "probe_interval_ms", 1000) or 1000)),
            log_diagnostic_events=bool(getattr(self.settings, "log_diagnostic_events", False)),
            show_status_popup=self.var_popup.get(),
            updates_enabled=bool(getattr(self.settings, "updates_enabled", False)),
            github_owner="D4MS06",
            github_repo="NetworkMonitoringProject",
            github_token=str(getattr(self.settings, "github_token", "")).strip(),
            include_prerelease=bool(getattr(self.settings, "include_prerelease", False)),
            update_target_tag=str(getattr(self.settings, "update_target_tag", "latest") or "latest").strip(),
            updates_connection_validated=bool(getattr(self.settings, "updates_connection_validated", False)),
            watermark_image_path=str(getattr(self.settings, "watermark_image_path", "")).strip(),
            watermark_source_path=str(getattr(self.settings, "watermark_source_path", "")).strip(),
            watermark_opacity=float(getattr(self.settings, "watermark_opacity", 0.16) or 0.16),
            ui_theme=str(getattr(self.settings, "ui_theme", "light") or "light").strip().lower(),
            theme_overrides_json=str(getattr(self.settings, "theme_overrides_json", "") or "").strip(),
            status_indicator_style=str(getattr(self.settings, "status_indicator_style", "badge") or "badge").strip().lower(),
        )

    @staticmethod
    def _parse_recipients(raw: str) -> list[str]:
        return [part.strip() for part in (raw or "").replace(";", ",").split(",") if part.strip()]

    def _listbox_recipients(self) -> list[str]:
        return [str(v).strip() for v in self.lst_recipients.get(0, END) if str(v).strip()]

    def _add_recipient(self) -> None:
        addr = self.var_rcpt.get().strip()
        if not addr:
            return
        if "@" not in addr or "." not in addr.split("@")[-1]:
            mb.showerror("Adresse invalide", "Entrez une adresse email valide.")
            return
        current = set(self._listbox_recipients())
        if addr in current:
            self.var_rcpt.set("")
            return
        self.lst_recipients.insert(END, addr)
        self.var_rcpt.set("")

    def _remove_selected_recipient(self) -> None:
        sel = self.lst_recipients.curselection()
        if not sel:
            return
        self.lst_recipients.delete(sel[0])

    def _on_test(self) -> None:
        """Envoie un email de test avec les parametres saisis."""
        try:
            send_alert_email(
                "Test notification",
                "Ceci est un email de test.",
                settings=self._gather_settings(),
            )
            mb.showinfo("Test envoye", "Email de test envoye")
        except Exception as exc:
            mb.showerror("Erreur", f"Impossible d'envoyer l'email: {exc}")
