from __future__ import annotations

from tkinter import ACTIVE, BooleanVar, Button, Checkbutton, Entry, Frame, Label, StringVar
from tkinter import messagebox as mb
from tkinter.simpledialog import Dialog

from monitoring.config.settings import NotificationSettings
from monitoring.config.settings import load_settings
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import bind_control_button_hover


class UpdateSettingsDialog(Dialog):
    _TOKEN_MASK = "*****"

    def __init__(self, parent, settings: NotificationSettings) -> None:
        self.settings = settings
        self._had_saved_token = bool(getattr(settings, "github_token", ""))
        self.theme = resolve_theme(str(getattr(load_settings(), "ui_theme", "light") or "light"))
        self.result: NotificationSettings | None = None
        super().__init__(parent, title="Parametres mise a jour")

    def body(self, master: Frame) -> Frame:
        self.var_enabled = BooleanVar(value=bool(getattr(self.settings, "updates_enabled", False)))
        self.var_owner = StringVar(value=str(getattr(self.settings, "github_owner", "")))
        self.var_repo = StringVar(value=str(getattr(self.settings, "github_repo", "")))
        self.var_include_prerelease = BooleanVar(
            value=bool(getattr(self.settings, "include_prerelease", False))
        )
        self.var_token = StringVar(
            value=self._TOKEN_MASK if self._had_saved_token else ""
        )

        Checkbutton(
            master,
            text="Activer la verification des mises a jour au demarrage",
            variable=self.var_enabled,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(6, 4))

        Label(master, text="Owner GitHub:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_owner, width=34).grid(row=1, column=1, padx=5, pady=4)

        Label(master, text="Repo GitHub:").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_repo, width=34).grid(row=2, column=1, padx=5, pady=4)

        Label(master, text="Token GitHub (repo prive):").grid(
            row=3, column=0, sticky="e", padx=5, pady=4
        )
        Entry(master, textvariable=self.var_token, width=34, show="*").grid(
            row=3, column=1, padx=5, pady=4
        )

        Checkbutton(
            master,
            text="Inclure les pre-releases",
            variable=self.var_include_prerelease,
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=(2, 4))

        return master

    def buttonbox(self) -> None:
        box = Frame(self)
        btn_ok = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        btn_ok.pack(side="left", padx=5, pady=5)
        btn_cancel = Button(box, text="Annuler", width=10, command=self.cancel)
        btn_cancel.pack(side="right", padx=5, pady=5)
        bind_control_button_hover(btn_ok, self.theme.colors)
        bind_control_button_hover(btn_cancel, self.theme.colors)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def _resolved_token(self) -> str:
        entered = self.var_token.get()
        if entered == self._TOKEN_MASK and self._had_saved_token:
            return getattr(self.settings, "github_token", "") or ""
        return entered.strip()

    def validate(self) -> bool:
        if not self.var_enabled.get():
            return True
        if not self.var_owner.get().strip():
            mb.showerror("Champ manquant", "Le owner GitHub est obligatoire.")
            return False
        if not self.var_repo.get().strip():
            mb.showerror("Champ manquant", "Le nom du repo GitHub est obligatoire.")
            return False
        if not self._resolved_token():
            mb.showerror("Champ manquant", "Le token GitHub est obligatoire pour un repo prive.")
            return False
        return True

    def apply(self) -> None:
        self.result = NotificationSettings(
            smtp_host=self.settings.smtp_host,
            smtp_port=self.settings.smtp_port,
            user=self.settings.user,
            password=self.settings.password,
            use_tls=self.settings.use_tls,
            recipients=self.settings.recipients,
            offline_delay_seconds=self.settings.offline_delay_seconds,
            online_recovery_delay_seconds=self.settings.online_recovery_delay_seconds,
            notification_cooldown_seconds=self.settings.notification_cooldown_seconds,
            failures_for_offline=max(1, int(getattr(self.settings, "failures_for_offline", 3) or 3)),
            successes_for_online=max(1, int(getattr(self.settings, "successes_for_online", 2) or 2)),
            ping_timeout_ms=max(250, int(getattr(self.settings, "ping_timeout_ms", 1500) or 1500)),
            probe_interval_ms=max(250, int(getattr(self.settings, "probe_interval_ms", 1000) or 1000)),
            log_diagnostic_events=bool(getattr(self.settings, "log_diagnostic_events", False)),
            show_status_popup=self.settings.show_status_popup,
            updates_enabled=bool(self.var_enabled.get()),
            github_owner=self.var_owner.get().strip(),
            github_repo=self.var_repo.get().strip(),
            github_token=self._resolved_token(),
            include_prerelease=bool(self.var_include_prerelease.get()),
            watermark_image_path=str(getattr(self.settings, "watermark_image_path", "")).strip(),
            watermark_source_path=str(getattr(self.settings, "watermark_source_path", "")).strip(),
            watermark_opacity=float(getattr(self.settings, "watermark_opacity", 0.16) or 0.16),
            ui_theme=str(getattr(self.settings, "ui_theme", "light") or "light").strip().lower(),
            theme_overrides_json=str(getattr(self.settings, "theme_overrides_json", "") or "").strip(),
            status_indicator_style=str(getattr(self.settings, "status_indicator_style", "badge") or "badge").strip().lower(),
        )
