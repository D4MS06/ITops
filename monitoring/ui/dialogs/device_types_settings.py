from __future__ import annotations

from tkinter import Frame, Label, StringVar, messagebox, simpledialog, ttk

from monitoring.controllers.device_type_controller import DeviceTypeController
from monitoring.ui.dialogs.device_type_schema_editor import DeviceTypeSchemaEditorDialog
from monitoring.ui.dialogs.themed_dialog import ThemedDialog
from monitoring.ui.utils.searchable_sortable_tree import SearchableSortableTreeMixin


class DeviceTypesSettingsDialog(SearchableSortableTreeMixin, ThemedDialog):
    """Manage dynamic device types with a tree-first UX."""

    def __init__(self, parent, *, on_changed=None) -> None:
        self._controller = DeviceTypeController()
        self._on_changed = on_changed
        self._types: list[dict] = []
        self.var_search = StringVar(value="")

        super().__init__(parent, title="Types de devices")

    def body(self, master) -> Frame:
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        main = Frame(master)
        main.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)
        main.grid_rowconfigure(0, weight=1)

        left = Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        search_row = Frame(left)
        search_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        search_row.grid_columnconfigure(1, weight=1)
        Label(search_row, text="Recherche:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.entry_search = ttk.Entry(search_row, textvariable=self.var_search, style="Dialog.TEntry")
        self.entry_search.grid(row=0, column=1, sticky="ew")

        self.tree = ttk.Treeview(left, columns=("code", "label", "mon", "cfg"), show="headings", height=12)
        self.tree.heading("code", text="Code")
        self.tree.heading("label", text="Libelle")
        self.tree.heading("mon", text="Monitoring")
        self.tree.heading("cfg", text="Conf")
        self.tree.column("code", width=140, minwidth=110, stretch=False)
        self.tree.column("label", width=260, minwidth=180, stretch=True)
        self.tree.column("mon", width=95, minwidth=75, stretch=False, anchor="center")
        self.tree.column("cfg", width=75, minwidth=60, stretch=False, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self._init_searchable_sortable_tree(
            tree=self.tree,
            search_var=self.var_search,
            on_query_changed=lambda: self._reload_types(select_code=self._selected_code() or None),
            search_container=search_row,
            default_sort_col="label",
            default_sort_reverse=False,
        )

        Label(
            left,
            text=(
                "Double-clic: Libelle=renommer, Monitoring/Conf=Oui/Non, "
                "Code=editer champs/actions"
            ),
            anchor="w",
            justify="left",
        ).grid(row=2, column=0, sticky="ew", padx=2, pady=(4, 0))

        right = Frame(main)
        right.grid(row=0, column=1, sticky="ns")
        right.grid_columnconfigure(0, weight=1)

        self.btn_new = ttk.Button(right, text="Nouveau", command=self._start_new, style="Dialog.TButton")
        self.btn_new.grid(row=0, column=0, sticky="ew", padx=4, pady=(2, 4))

        self.btn_delete = ttk.Button(right, text="Supprimer", command=self._delete_current, style="Dialog.TButton")
        self.btn_delete.grid(row=1, column=0, sticky="ew", padx=4, pady=4)

        self.btn_schema = ttk.Button(
            right,
            text="Editer champs/actions...",
            command=self._open_schema_editor,
            style="Dialog.TButton",
        )
        self.btn_schema.grid(row=2, column=0, sticky="ew", padx=4, pady=4)

        self._reload_types(select_code="switch")
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        ttk.Button(box, text="Fermer", command=self.cancel, style="Dialog.TButton").pack(padx=5, pady=6)
        box.pack()

    @staticmethod
    def _config_enabled(item: dict) -> bool:
        cfg_flag = item.get("config_backups_enabled", None)
        if cfg_flag is None:
            return str(item.get("icon", "")).strip().lower() == "switch"
        return bool(cfg_flag)

    def _selected_code(self) -> str:
        sel = self.tree.selection()
        return str(sel[0]) if sel else ""

    def _selected_type(self) -> dict | None:
        code = self._selected_code()
        return self._find_type(code) if code else None

    def _reload_types(self, *, select_code: str | None = None) -> None:
        self._types = self._controller.list_types()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        rows = self._apply_filter_sort(
            list(self._types),
            searchable_text=lambda item: " ".join(
                [
                    str(item.get("code", "")),
                    str(item.get("label", "")),
                ]
            ),
            sort_value=lambda item, col: (
                str(item.get("code", "")).lower()
                if col == "code"
                else bool(item.get("monitoring_enabled", True))
                if col == "mon"
                else self._config_enabled(item)
                if col == "cfg"
                else str(item.get("label", "")).lower()
            ),
        )
        for item in rows:
            code = str(item.get("code", ""))
            label = str(item.get("label", ""))
            mon = "Oui" if bool(item.get("monitoring_enabled", True)) else "Non"
            cfg = "Oui" if self._config_enabled(item) else "Non"
            self.tree.insert("", "end", iid=code, values=(code, label, mon, cfg))

        if select_code and self.tree.exists(select_code):
            self.tree.selection_set(select_code)
            self.tree.focus(select_code)
        elif self.tree.get_children():
            first = str(self.tree.get_children()[0])
            self.tree.selection_set(first)
            self.tree.focus(first)
        self._on_select()

    def _find_type(self, code: str) -> dict | None:
        for item in self._types:
            if str(item.get("code", "")) == code:
                return item
        return None

    def _on_select(self, _evt=None) -> None:
        item = self._selected_type()
        if not item:
            self.btn_delete.configure(state="disabled")
            self.btn_schema.configure(state="disabled")
            return

        is_system = bool(item.get("is_system", False))
        self.btn_delete.configure(state="disabled" if is_system else "normal")
        self.btn_schema.configure(state="normal")

    def _start_new(self) -> None:
        DeviceTypeSchemaEditorDialog(
            self,
            type_code="",
            type_label="",
            monitoring_enabled=True,
            config_backups_enabled=False,
            create_mode=True,
            on_saved=self._on_schema_saved,
            controller=self._controller,
        )

    def _open_schema_editor(self, _evt=None) -> None:
        item = self._selected_type()
        if not item:
            messagebox.showinfo("Type", "Selectionnez d'abord un type.", parent=self)
            return

        code = str(item.get("code", "")).strip().lower()
        label = str(item.get("label", "")).strip() or code
        DeviceTypeSchemaEditorDialog(
            self,
            type_code=code,
            type_label=label,
            monitoring_enabled=bool(item.get("monitoring_enabled", True)),
            config_backups_enabled=self._config_enabled(item),
            on_saved=self._on_schema_saved,
            controller=self._controller,
        )

    def _on_tree_double_click(self, evt=None) -> None:
        row_id = str(self.tree.identify_row(evt.y)) if evt is not None else ""
        col_id = str(self.tree.identify_column(evt.x)) if evt is not None else ""
        if not row_id:
            return
        self.tree.selection_set(row_id)
        self.tree.focus(row_id)
        self._on_select()

        item = self._find_type(row_id)
        if not item:
            return

        if col_id == "#2":
            self._rename_type(item)
            return
        if col_id == "#3":
            self._toggle_monitoring_flag(item)
            return
        if col_id == "#4":
            self._toggle_config_flag(item)
            return
        self._open_schema_editor()

    def _toggle_monitoring_flag(self, item: dict) -> None:
        code = str(item.get("code", "")).strip().lower()
        label = str(item.get("label", "")).strip() or code
        next_monitoring = not bool(item.get("monitoring_enabled", True))
        if not next_monitoring:
            log_count = 0
            try:
                log_count = int(self._controller.count_type_logs(type_code=code) or 0)
            except Exception:
                log_count = 0
            if log_count > 0:
                confirm = messagebox.askyesno(
                    "Confirmer la desactivation",
                    (
                        f"Desactiver le monitoring pour '{label}' ?\n\n"
                        f"{log_count} log(s) seront supprimes."
                    ),
                    parent=self,
                )
                if not confirm:
                    return
        try:
            saved_code = self._controller.save_type(
                code=code,
                label=label,
                monitoring_enabled=next_monitoring,
                config_backups_enabled=self._config_enabled(item),
            )
        except Exception as exc:
            messagebox.showerror("Type", f"Impossible de modifier Monitoring: {exc}", parent=self)
            return
        self._reload_types(select_code=saved_code)
        if callable(self._on_changed):
            self._on_changed()

    def _toggle_config_flag(self, item: dict) -> None:
        code = str(item.get("code", "")).strip().lower()
        label = str(item.get("label", "")).strip() or code
        monitoring = bool(item.get("monitoring_enabled", True))
        next_cfg = not self._config_enabled(item)
        if not next_cfg:
            purge_count = 0
            try:
                purge_count = int(self._controller.count_type_config_files(type_label=label) or 0)
            except Exception:
                purge_count = 0
            confirm = messagebox.askyesno(
                "Confirmer la desactivation",
                (
                    f"Desactiver la gestion des fichiers de configuration pour '{label}' ?\n\n"
                    f"{purge_count} fichier(s) seront supprimes."
                ),
                parent=self,
            )
            if not confirm:
                return
        try:
            saved_code = self._controller.save_type(
                code=code,
                label=label,
                monitoring_enabled=monitoring,
                config_backups_enabled=next_cfg,
            )
        except Exception as exc:
            messagebox.showerror("Type", f"Impossible de modifier Conf: {exc}", parent=self)
            return
        self._reload_types(select_code=saved_code)
        if callable(self._on_changed):
            self._on_changed()

    def _rename_type(self, item: dict) -> None:
        code = str(item.get("code", "")).strip().lower()
        current_label = str(item.get("label", "")).strip()
        new_label = simpledialog.askstring(
            "Renommer le type",
            f"Nouveau libelle pour '{code}' :",
            initialvalue=current_label,
            parent=self,
        )
        if new_label is None:
            return
        new_label = str(new_label).strip()
        if not new_label or new_label == current_label:
            return
        try:
            saved_code = self._controller.save_type(
                code=code,
                label=new_label,
                monitoring_enabled=bool(item.get("monitoring_enabled", True)),
                config_backups_enabled=self._config_enabled(item),
            )
        except Exception as exc:
            messagebox.showerror("Type", f"Impossible de renommer le type: {exc}", parent=self)
            return
        self._reload_types(select_code=saved_code)
        if callable(self._on_changed):
            self._on_changed()

    def _on_schema_saved(self, saved_code: str | None = None) -> None:
        if saved_code:
            self._reload_types(select_code=str(saved_code))
        if callable(self._on_changed):
            self._on_changed()

    def _delete_current(self) -> None:
        item = self._selected_type()
        if not item:
            return

        code = str(item.get("code", "")).strip().lower()
        if not code:
            return

        if bool(item.get("is_system", False)):
            messagebox.showwarning("Type", "Impossible de supprimer un type systeme.", parent=self)
            return

        try:
            count = int(self._controller.count_devices(code) or 0)
        except Exception:
            count = 0

        if count > 0:
            confirmed = messagebox.askyesno(
                "Supprimer le type",
                (
                    f"Le type '{code}' est utilise par {count} device(s).\n\n"
                    "Si vous confirmez, le type ET tous les devices de ce type seront supprimes.\n"
                    "Continuer ?"
                ),
                parent=self,
            )
            if not confirmed:
                return
            cascade_devices = True
        else:
            confirmed = messagebox.askyesno("Supprimer le type", f"Supprimer le type '{code}' ?", parent=self)
            if not confirmed:
                return
            cascade_devices = False

        try:
            deleted = self._controller.delete_type(code, cascade_devices=cascade_devices)
            if not deleted:
                messagebox.showinfo("Type", "Type introuvable.", parent=self)
                return
        except ValueError as exc:
            messagebox.showwarning("Type", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Type", f"Impossible de supprimer le type: {exc}", parent=self)
            return

        self._reload_types(select_code="switch")
        if callable(self._on_changed):
            self._on_changed()
