from __future__ import annotations

from tkinter import ACTIVE, BooleanVar, Button, Checkbutton, Entry, Frame, Label, StringVar, ttk
from tkinter import messagebox as mb

from monitoring.config.settings import NotificationSettings
from monitoring.ui.dialogs.themed_dialog import ThemedDialog
from monitoring.utils.updater import list_installable_releases


class UpdateSettingsDialog(ThemedDialog):
    _TOKEN_MASK = "*****"

    def __init__(self, parent, settings: NotificationSettings) -> None:
        self.settings = settings
        self._had_saved_token = bool(getattr(settings, "github_token", ""))
        self._update_test_validated = bool(getattr(settings, "updates_connection_validated", False))
        self.result: NotificationSettings | None = None
        super().__init__(parent, title="Parametres mise a jour")

    def body(self, master: Frame) -> Frame:
        c = self.theme.colors
        master.configure(bg=c["app_bg"])
        self.var_enabled = BooleanVar(value=bool(getattr(self.settings, "updates_enabled", False)))
        self.var_include_prerelease = BooleanVar(
            value=bool(getattr(self.settings, "include_prerelease", False))
        )
        self.var_target_tag = StringVar(value=str(getattr(self.settings, "update_target_tag", "latest") or "latest"))
        self.var_token = StringVar(
            value=self._TOKEN_MASK if self._had_saved_token else ""
        )

        self.chk_enabled = Checkbutton(
            master,
            text="Activer la verification des mises a jour au demarrage",
            variable=self.var_enabled,
            command=self._on_enabled_toggle,
            bg=c["app_bg"],
            fg=c["text_primary"],
            activebackground=c["app_bg"],
            activeforeground=c["text_primary"],
            selectcolor=c["panel_bg"],
        )
        self.chk_enabled.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(6, 4))

        Label(master, text="Token GitHub (repo prive):", bg=c["app_bg"], fg=c["text_primary"]).grid(
            row=1, column=0, sticky="e", padx=5, pady=4
        )
        self.entry_token = Entry(
            master,
            textvariable=self.var_token,
            width=34,
            show="*",
            relief="solid",
            bd=1,
            bg=c["panel_bg"],
            fg=c["text_primary"],
            insertbackground=c["text_primary"],
            highlightthickness=1,
            highlightbackground=c["placeholder_border"],
            highlightcolor=c["nav_active_bg"],
        )
        self.entry_token.grid(
            row=1, column=1, padx=5, pady=4
        )

        self.chk_prerelease = Checkbutton(
            master,
            text="Inclure les pre-releases",
            variable=self.var_include_prerelease,
            bg=c["app_bg"],
            fg=c["text_primary"],
            activebackground=c["app_bg"],
            activeforeground=c["text_primary"],
            selectcolor=c["panel_bg"],
        )
        self.chk_prerelease.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(2, 4))

        Label(master, text="Version cible:", bg=c["app_bg"], fg=c["text_primary"]).grid(row=3, column=0, sticky="e", padx=5, pady=4)
        self.version_combo = ttk.Combobox(
            master,
            state="readonly",
            width=34,
            values=["Derniere disponible (auto)"],
        )
        self.version_combo.grid(row=3, column=1, padx=5, pady=4, sticky="we")
        self.version_combo.set("Derniere disponible (auto)")
        self._version_choices: dict[str, str] = {"Derniere disponible (auto)": "latest"}

        self.btn_test = Button(master, text="Tester", command=self._run_update_test)
        self.btn_test.grid(row=4, column=0, sticky="w", padx=5, pady=(0, 4))
        self.style_button(self.btn_test)

        self.btn_refresh_versions = Button(master, text="Charger versions", command=self._refresh_versions)
        self.btn_refresh_versions.grid(row=4, column=1, sticky="e", padx=5, pady=(0, 4))
        self.style_button(self.btn_refresh_versions)

        self.var_token.trace_add("write", lambda *_: self._mark_test_invalid())
        self.var_include_prerelease.trace_add("write", lambda *_: self._mark_test_invalid())
        self._set_update_controls_state()
        if self.var_enabled.get() and self._update_test_validated:
            self._refresh_versions(show_error=False)
        self.apply_theme(master)

        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        btn_ok = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        btn_ok.pack(side="left", padx=5, pady=5)
        btn_cancel = Button(box, text="Annuler", width=10, command=self.cancel)
        btn_cancel.pack(side="right", padx=5, pady=5)
        self.style_button(btn_ok)
        self.style_button(btn_cancel)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()
        self.apply_theme(self)

    def _resolved_token(self) -> str:
        entered = self.var_token.get()
        if entered == self._TOKEN_MASK and self._had_saved_token:
            return getattr(self.settings, "github_token", "") or ""
        return entered.strip()

    def _set_update_controls_state(self) -> None:
        enabled = bool(self.var_enabled.get())
        try:
            self.btn_test.configure(state="normal" if enabled else "disabled")
            self.btn_refresh_versions.configure(
                state=("normal" if (enabled and self._update_test_validated) else "disabled")
            )
            self.version_combo.configure(
                state=("readonly" if (enabled and self._update_test_validated) else "disabled")
            )
        except Exception:
            pass

    def _on_enabled_toggle(self) -> None:
        if not self.var_enabled.get():
            self.var_target_tag.set("latest")
            self.version_combo.set("Derniere disponible (auto)")
        self._set_update_controls_state()

    def _mark_test_invalid(self) -> None:
        self._update_test_validated = False
        self._set_update_controls_state()

    def _run_update_test(self) -> None:
        if not self.var_enabled.get():
            mb.showinfo("Mises a jour", "Activez d'abord les mises a jour.")
            return
        if not self._resolved_token():
            mb.showerror("Mises a jour", "Token GitHub requis pour tester la connexion.")
            return
        releases = self._refresh_versions(show_error=True)
        if releases is None:
            self._update_test_validated = False
            self._set_update_controls_state()
            return
        self._update_test_validated = True
        self._set_update_controls_state()
        mb.showinfo("Mises a jour", f"Connexion validee. {len(releases)} version(s) disponible(s).")

    def _refresh_versions(self, *, show_error: bool = True):
        if not self.var_enabled.get():
            return []
        token = self._resolved_token()
        if not token:
            if show_error:
                mb.showerror("Mises a jour", "Token GitHub requis pour charger les versions.")
            return None
        temp = NotificationSettings(
            github_token=token,
            updates_enabled=True,
            include_prerelease=True,
        )
        try:
            releases = list_installable_releases(temp)
        except Exception as exc:
            if show_error:
                mb.showerror("Mises a jour", f"Impossible de charger les versions: {exc}")
            return None

        choices: dict[str, str] = {"Derniere disponible (auto)": "latest"}
        for rel in releases:
            tag = str(rel.tag_name).strip()
            label = tag
            if rel.prerelease:
                label = f"{tag} (pre-release)"
            choices[label] = tag

        self._version_choices = choices
        values = list(choices.keys())
        self.version_combo.configure(values=values)

        current_target = (self.var_target_tag.get() or "latest").strip()
        target_label = next((k for k, v in choices.items() if v == current_target), "")
        if not target_label:
            stable_label = ""
            for rel in releases:
                if not rel.prerelease:
                    stable_label = next((k for k, v in choices.items() if v == rel.tag_name), "")
                    if stable_label:
                        break
            target_label = stable_label or values[0]
        self.version_combo.set(target_label)
        self.var_target_tag.set(choices.get(target_label, "latest"))
        self.version_combo.bind("<<ComboboxSelected>>", self._on_version_selected, add="+")
        self._update_test_validated = True
        self._set_update_controls_state()
        return releases

    def _on_version_selected(self, _evt=None) -> None:
        label = self.version_combo.get().strip()
        self.var_target_tag.set(self._version_choices.get(label, "latest"))

    def validate(self) -> bool:
        if not self.var_enabled.get():
            return True
        if not self._resolved_token():
            mb.showerror("Champ manquant", "Le token GitHub est obligatoire pour un repo prive.")
            return False
        if not self._update_test_validated:
            mb.showerror("Validation requise", "Cliquez sur 'Tester' et validez la connexion GitHub avant de continuer.")
            return False
        self._on_version_selected()
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
            github_owner="D4MS06",
            github_repo="NetworkMonitoringProject",
            github_token=self._resolved_token(),
            include_prerelease=bool(self.var_include_prerelease.get()),
            update_target_tag=str(self.var_target_tag.get() or "latest").strip(),
            updates_connection_validated=bool(self._update_test_validated),
            watermark_image_path=str(getattr(self.settings, "watermark_image_path", "")).strip(),
            watermark_source_path=str(getattr(self.settings, "watermark_source_path", "")).strip(),
            watermark_opacity=float(getattr(self.settings, "watermark_opacity", 0.16) or 0.16),
            ui_theme=str(getattr(self.settings, "ui_theme", "light") or "light").strip().lower(),
            theme_overrides_json=str(getattr(self.settings, "theme_overrides_json", "") or "").strip(),
            status_indicator_style=str(getattr(self.settings, "status_indicator_style", "badge") or "badge").strip().lower(),
        )
