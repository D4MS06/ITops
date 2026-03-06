from __future__ import annotations

from tkinter import BooleanVar, Frame, Label, StringVar, messagebox, ttk

from monitoring.controllers.device_type_controller import DeviceTypeController
from monitoring.ui.dialogs.device_type_schema_editor import DeviceTypeSchemaEditorDialog
from monitoring.ui.dialogs.themed_dialog import ThemedDialog


class DeviceTypesSettingsDialog(ThemedDialog):
    """Manage dynamic device types stored in SQLite."""

    def __init__(self, parent, *, on_changed=None) -> None:
        self._controller = DeviceTypeController()
        self._on_changed = on_changed
        self._types: list[dict] = []
        self._creating_new = False

        self.var_code = StringVar(value="")
        self.var_label = StringVar(value="")
        self.var_monitoring = BooleanVar(value=True)

        super().__init__(parent, title="Types de devices")

    def body(self, master) -> Frame:
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        main = Frame(master)
        main.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        main.grid_columnconfigure(0, weight=2)
        main.grid_columnconfigure(1, weight=3)
        main.grid_rowconfigure(0, weight=1)

        left = Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(left, columns=("code", "label", "mon"), show="headings", height=12)
        self.tree.heading("code", text="Code")
        self.tree.heading("label", text="Libelle")
        self.tree.heading("mon", text="Monitoring")
        self.tree.column("code", width=120, minwidth=100, stretch=False)
        self.tree.column("label", width=230, minwidth=170, stretch=True)
        self.tree.column("mon", width=85, minwidth=70, stretch=False, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._open_schema_editor)
        Label(
            left,
            text="Double-clic sur un type pour editer ses champs/actions et voir la preview du formulaire.",
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=2, pady=(4, 0))

        right = Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(1, weight=1)

        Label(right, text="Code :").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.entry_code = ttk.Entry(right, textvariable=self.var_code)
        self.entry_code.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        Label(right, text="Libelle :").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self.entry_label = ttk.Entry(right, textvariable=self.var_label)
        self.entry_label.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        self.chk_monitoring = ttk.Checkbutton(
            right,
            text="Type monitorable",
            variable=self.var_monitoring,
        )
        self.chk_monitoring.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(8, 4))

        actions = Frame(right)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", padx=4, pady=(12, 4))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(2, weight=1)

        self.btn_new = ttk.Button(actions, text="Nouveau", command=self._start_new, style="Dialog.TButton")
        self.btn_new.grid(row=0, column=0, sticky="ew", padx=2)
        self.btn_save = ttk.Button(actions, text="Enregistrer", command=self._save_current, style="Dialog.TButton")
        self.btn_save.grid(row=0, column=1, sticky="ew", padx=2)
        self.btn_delete = ttk.Button(actions, text="Supprimer", command=self._delete_current, style="Dialog.TButton")
        self.btn_delete.grid(row=0, column=2, sticky="ew", padx=2)

        self.btn_schema = ttk.Button(right, text="Editer champs/actions...", command=self._open_schema_editor, style="Dialog.TButton")
        self.btn_schema.grid(row=4, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 0))

        self._reload_types(select_code="switch")
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        ttk.Button(box, text="Fermer", command=self.cancel, style="Dialog.TButton").pack(padx=5, pady=6)
        box.pack()

    def _reload_types(self, *, select_code: str | None = None) -> None:
        self._types = self._controller.list_types()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for item in self._types:
            code = str(item.get("code", ""))
            label = str(item.get("label", ""))
            mon = "Oui" if bool(item.get("monitoring_enabled", True)) else "Non"
            self.tree.insert("", "end", iid=code, values=(code, label, mon))

        if select_code and self.tree.exists(select_code):
            self.tree.selection_set(select_code)
            self.tree.focus(select_code)
            self._on_select()
        elif self.tree.get_children():
            first = str(self.tree.get_children()[0])
            self.tree.selection_set(first)
            self.tree.focus(first)
            self._on_select()
        else:
            self._start_new()

    def _find_type(self, code: str) -> dict | None:
        for item in self._types:
            if str(item.get("code", "")) == code:
                return item
        return None

    def _on_select(self, _evt=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        code = str(sel[0])
        item = self._find_type(code)
        if not item:
            return

        self._creating_new = False
        self.var_code.set(code)
        self.var_label.set(str(item.get("label", "")))
        self.var_monitoring.set(bool(item.get("monitoring_enabled", True)))

        is_system = bool(item.get("is_system", False))
        self.entry_code.configure(state="disabled")
        self.btn_delete.configure(state="disabled" if is_system else "normal")
        self.btn_schema.configure(state="normal")

    def _start_new(self) -> None:
        DeviceTypeSchemaEditorDialog(
            self,
            type_code="",
            type_label="",
            monitoring_enabled=True,
            create_mode=True,
            on_saved=self._on_schema_saved,
            controller=self._controller,
        )

    def _open_schema_editor(self, _evt=None) -> None:
        if self._creating_new:
            messagebox.showinfo("Type", "Enregistrez d'abord le type avant d'editer son formulaire.", parent=self)
            return
        code = self.var_code.get().strip().lower()
        if not code:
            return
        label = self.var_label.get().strip() or code
        DeviceTypeSchemaEditorDialog(
            self,
            type_code=code,
            type_label=label,
            monitoring_enabled=bool(self.var_monitoring.get()),
            on_saved=self._on_schema_saved,
            controller=self._controller,
        )

    def _on_schema_saved(self, saved_code: str | None = None) -> None:
        if saved_code:
            self._reload_types(select_code=str(saved_code))
        if callable(self._on_changed):
            self._on_changed()

    def _save_current(self) -> None:
        code = self.var_code.get().strip().lower()
        label = self.var_label.get().strip()
        if not code:
            messagebox.showerror("Type", "Le code du type est obligatoire.", parent=self)
            return
        if not label:
            messagebox.showerror("Type", "Le libelle du type est obligatoire.", parent=self)
            return

        try:
            saved_code = self._controller.save_type(code=code, label=label, monitoring_enabled=bool(self.var_monitoring.get()))
        except ValueError as exc:
            messagebox.showerror("Type", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Type", f"Impossible de sauvegarder le type: {exc}", parent=self)
            return

        self._reload_types(select_code=saved_code)
        if callable(self._on_changed):
            self._on_changed()

    def _delete_current(self) -> None:
        if self._creating_new:
            return
        code = self.var_code.get().strip().lower()
        if not code:
            return
        if not messagebox.askyesno("Type", f"Supprimer le type '{code}' ?", parent=self):
            return

        try:
            deleted = self._controller.delete_type(code)
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
