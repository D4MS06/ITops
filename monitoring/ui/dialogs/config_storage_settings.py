from __future__ import annotations

from dataclasses import replace
from tkinter import ACTIVE, BooleanVar, Button, Entry, Frame, Label, LabelFrame, Radiobutton, StringVar, filedialog
from tkinter import messagebox as mb

from monitoring.config.settings import NotificationSettings
from monitoring.ui.dialogs.themed_dialog import ThemedDialog
from monitoring.utils.config_files import ensure_smb3_connection


class ConfigStorageSettingsDialog(ThemedDialog):
    _PASSWORD_MASK = "*****"

    def __init__(self, parent, settings: NotificationSettings) -> None:
        self.settings = settings
        self._had_saved_smb_password = bool(getattr(settings, "config_smb_password", ""))
        self._smb_test_validated = bool(
            str(getattr(settings, "config_storage_mode", "local") or "local").strip().lower() == "smb3"
            and str(getattr(settings, "config_smb_unc_path", "") or "").strip()
            and str(getattr(settings, "config_smb_username", "") or "").strip()
            and bool(getattr(settings, "config_smb_password", ""))
        )
        self.result: NotificationSettings | None = None
        super().__init__(parent, title="Parametres sauvegarde")

    def body(self, master: Frame) -> Frame:
        self.var_mode = StringVar(value=str(getattr(self.settings, "config_storage_mode", "local") or "local"))
        self.var_local_dir = StringVar(value=str(getattr(self.settings, "switch_configs_dir", "") or ""))
        self.var_smb_unc = StringVar(value=str(getattr(self.settings, "config_smb_unc_path", "") or ""))
        self.var_smb_user = StringVar(value=str(getattr(self.settings, "config_smb_username", "") or ""))
        self.var_smb_password = StringVar(
            value=self._PASSWORD_MASK if self._had_saved_smb_password else ""
        )
        self.var_auto = BooleanVar(value=bool(getattr(self.settings, "config_auto_sync_enabled", False)))
        self.var_interval = StringVar(
            value=str(int(getattr(self.settings, "config_auto_sync_interval_seconds", 3600) or 3600))
        )

        root_box = LabelFrame(master, text="Emplacement des sauvegardes", padx=6, pady=6)
        root_box.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        root_box.grid_columnconfigure(1, weight=1)

        Radiobutton(
            root_box,
            text="Dossier local",
            value="local",
            variable=self.var_mode,
            command=self._update_mode_state,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=4, pady=(2, 4))
        Label(root_box, text="Chemin local:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self.entry_local_dir = Entry(root_box, textvariable=self.var_local_dir, width=48)
        self.entry_local_dir.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        self.btn_browse_local = Button(root_box, text="Parcourir...", command=self._browse_local)
        self.btn_browse_local.grid(row=1, column=2, sticky="w", padx=4, pady=4)
        self.style_button(self.btn_browse_local)

        Radiobutton(
            root_box,
            text="Dossier reseau SMB3",
            value="smb3",
            variable=self.var_mode,
            command=self._update_mode_state,
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=4, pady=(10, 4))

        Label(root_box, text="Chemin UNC:").grid(row=3, column=0, sticky="e", padx=4, pady=4)
        self.entry_smb_unc = Entry(root_box, textvariable=self.var_smb_unc, width=48)
        self.entry_smb_unc.grid(row=3, column=1, columnspan=2, sticky="ew", padx=4, pady=4)
        Label(root_box, text="Utilisateur:").grid(row=4, column=0, sticky="e", padx=4, pady=4)
        self.entry_smb_user = Entry(root_box, textvariable=self.var_smb_user, width=48)
        self.entry_smb_user.grid(row=4, column=1, columnspan=2, sticky="ew", padx=4, pady=4)
        Label(root_box, text="Mot de passe:").grid(row=5, column=0, sticky="e", padx=4, pady=4)
        self.entry_smb_password = Entry(root_box, textvariable=self.var_smb_password, width=48, show="*")
        self.entry_smb_password.grid(row=5, column=1, columnspan=2, sticky="ew", padx=4, pady=4)
        self.btn_test_smb = Button(root_box, text="Tester connexion SMB3", command=self._test_smb_connection)
        self.btn_test_smb.grid(row=6, column=1, sticky="w", padx=4, pady=(2, 4))
        self.style_button(self.btn_test_smb)

        sync_box = LabelFrame(master, text="Mode de sauvegarde", padx=6, pady=6)
        sync_box.grid(row=1, column=0, sticky="ew", padx=8, pady=6)
        sync_box.grid_columnconfigure(1, weight=1)
        self.chk_auto = Radiobutton(
            sync_box,
            text="Automatique (sur nouvelles confs)",
            value=True,
            variable=self.var_auto,
            command=self._update_mode_state,
        )
        self.chk_auto.grid(row=0, column=0, columnspan=3, sticky="w", padx=4, pady=2)
        self.chk_manual = Radiobutton(
            sync_box,
            text="Manuel (declenchement utilisateur)",
            value=False,
            variable=self.var_auto,
            command=self._update_mode_state,
        )
        self.chk_manual.grid(row=1, column=0, columnspan=3, sticky="w", padx=4, pady=2)
        Label(sync_box, text="Intervalle auto (sec):").grid(row=2, column=0, sticky="e", padx=4, pady=4)
        self.entry_interval = Entry(sync_box, textvariable=self.var_interval, width=10)
        self.entry_interval.grid(row=2, column=1, sticky="w", padx=4, pady=4)

        master.grid_columnconfigure(0, weight=1)
        self.var_smb_unc.trace_add("write", lambda *_: self._invalidate_smb_test())
        self.var_smb_user.trace_add("write", lambda *_: self._invalidate_smb_test())
        self.var_smb_password.trace_add("write", lambda *_: self._invalidate_smb_test())
        self._update_mode_state()
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        btn_ok = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        btn_ok.pack(side="left", padx=5, pady=5)
        btn_cancel = Button(box, text="Annuler", width=10, command=self.cancel)
        btn_cancel.pack(side="right", padx=5, pady=5)
        for btn in (btn_ok, btn_cancel):
            self.style_button(btn)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()
        self.apply_theme(self)

    def _resolved_smb_password(self) -> str:
        entered = self.var_smb_password.get().strip()
        if entered == self._PASSWORD_MASK and self._had_saved_smb_password:
            return str(getattr(self.settings, "config_smb_password", "") or "")
        return entered

    def _browse_local(self) -> None:
        chosen = filedialog.askdirectory(
            parent=self,
            title="Selectionner le dossier local de sauvegarde",
            initialdir=self.var_local_dir.get().strip() or ".",
            mustexist=False,
        )
        if chosen:
            self.var_local_dir.set(chosen)

    def _update_mode_state(self) -> None:
        mode = str(self.var_mode.get() or "local").strip().lower()
        local_state = "normal" if mode == "local" else "disabled"
        smb_state = "normal" if mode == "smb3" else "disabled"
        interval_state = "normal" if bool(self.var_auto.get()) else "disabled"
        for w in (self.entry_local_dir, self.btn_browse_local):
            try:
                w.configure(state=local_state)
            except Exception:
                pass
        for w in (self.entry_smb_unc, self.entry_smb_user, self.entry_smb_password):
            try:
                w.configure(state=smb_state)
            except Exception:
                pass
        try:
            self.btn_test_smb.configure(state=smb_state)
        except Exception:
            pass
        try:
            self.entry_interval.configure(state=interval_state)
        except Exception:
            pass
        if mode != "smb3":
            self._smb_test_validated = False

    def _invalidate_smb_test(self) -> None:
        self._smb_test_validated = False

    def _test_smb_connection(self) -> None:
        candidate = replace(
            self.settings,
            config_storage_mode="smb3",
            config_smb_unc_path=self.var_smb_unc.get().strip(),
            config_smb_username=self.var_smb_user.get().strip(),
            config_smb_password=self._resolved_smb_password(),
        )
        ok, info = ensure_smb3_connection(candidate)
        if not ok:
            self._smb_test_validated = False
            mb.showerror("SMB3", f"Echec connexion SMB3: {info}")
            return
        self._smb_test_validated = True
        mb.showinfo("SMB3", "Connexion SMB3 valide. Les parametres peuvent etre enregistres.")

    def validate(self) -> bool:
        mode = str(self.var_mode.get() or "local").strip().lower()
        if mode not in {"local", "smb3"}:
            mb.showerror("Mode invalide", "Choisissez un mode de stockage valide.")
            return False
        if mode == "local":
            if not self.var_local_dir.get().strip():
                mb.showerror("Champ manquant", "Le dossier local est obligatoire.")
                return False
        else:
            if not self.var_smb_unc.get().strip():
                mb.showerror("Champ manquant", "Le chemin UNC SMB3 est obligatoire.")
                return False
            if not self.var_smb_user.get().strip():
                mb.showerror("Champ manquant", "L'utilisateur SMB est obligatoire.")
                return False
            if not self._resolved_smb_password():
                mb.showerror("Champ manquant", "Le mot de passe SMB est obligatoire.")
                return False
            if not self._smb_test_validated:
                mb.showerror("Validation requise", "Testez et validez la connexion SMB3 avant d'enregistrer.")
                return False
        if bool(self.var_auto.get()):
            try:
                interval = int(self.var_interval.get().strip())
            except Exception:
                mb.showerror("Valeur invalide", "L'intervalle auto doit etre un entier.")
                return False
            if interval < 5:
                mb.showerror("Valeur invalide", "L'intervalle auto doit etre >= 5 secondes.")
                return False
        return True

    def apply(self) -> None:
        interval = 3600
        try:
            interval = max(5, int(self.var_interval.get().strip() or 3600))
        except Exception:
            interval = 3600
        self.result = replace(
            self.settings,
            switch_configs_dir=self.var_local_dir.get().strip(),
            config_storage_mode=str(self.var_mode.get() or "local").strip().lower(),
            config_smb_unc_path=self.var_smb_unc.get().strip(),
            config_smb_username=self.var_smb_user.get().strip(),
            config_smb_password=self._resolved_smb_password(),
            config_auto_sync_enabled=bool(self.var_auto.get()),
            config_auto_sync_interval_seconds=interval,
        )
