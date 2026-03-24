from __future__ import annotations

import shutil
from pathlib import Path
from tkinter import Frame, Label, Menu, StringVar, filedialog, messagebox, simpledialog, ttk

from monitoring.ui.dialogs.themed_dialog import ThemedDialog
from monitoring.ui.utils.searchable_sortable_tree import SearchableSortableTreeMixin
from monitoring.utils.config_files import (
    delete_local_config_version,
    list_local_config_versions,
    open_path_with_default_app,
    rename_local_config_version,
    resolve_local_device_versions_dir,
    store_imported_config_version,
)


class ConfigFilesManagerDialog(SearchableSortableTreeMixin, ThemedDialog):
    def __init__(
        self,
        parent,
        *,
        local_versions_root: Path,
        device_type_label: str,
        device_name: str,
    ) -> None:
        self.local_versions_root = Path(local_versions_root)
        self.device_type_label = str(device_type_label or "").strip() or "Type"
        self.device_name = str(device_name or "").strip() or "Device"
        self.var_detail = StringVar(value="")
        self.var_search = StringVar(value="")
        self._rows: list[dict] = []
        super().__init__(parent, title=f"Gestion des fichiers - {self.device_name}")

    def body(self, master) -> Frame:
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(2, weight=1)
        Label(
            master,
            text=f"{self.device_type_label} / {self.device_name}",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 2))
        search_row = Frame(master)
        search_row.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 2))
        search_row.grid_columnconfigure(1, weight=1)
        Label(search_row, text="Recherche:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(search_row, textvariable=self.var_search, style="Dialog.TEntry").grid(row=0, column=1, sticky="ew")

        self.tree = ttk.Treeview(master, columns=("date", "name", "detail"), show="headings", height=12)
        self.tree.heading("date", text="Date")
        self.tree.heading("name", text="Fichier")
        self.tree.heading("detail", text="Detail")
        self.tree.column("date", width=140, minwidth=120, stretch=False)
        self.tree.column("name", width=320, minwidth=220, stretch=True)
        self.tree.column("detail", width=260, minwidth=160, stretch=True)
        self.tree.grid(row=2, column=0, sticky="nsew", padx=6, pady=4)
        self._init_searchable_sortable_tree(
            tree=self.tree,
            search_var=self.var_search,
            on_query_changed=self._reload,
            search_container=search_row,
            default_sort_col="date",
            default_sort_reverse=True,
        )
        self.tree.bind("<Button-3>", self._on_tree_right_click)

        bottom = Frame(master)
        bottom.grid(row=3, column=0, sticky="ew", padx=6, pady=(2, 6))
        bottom.grid_columnconfigure(4, weight=1)
        ttk.Button(bottom, text="+", width=3, command=self._import_file, style="Dialog.TButton").grid(
            row=0, column=0, sticky="w", padx=(0, 4)
        )
        ttk.Button(bottom, text="-", width=3, command=self._delete_selected, style="Dialog.TButton").grid(
            row=0, column=1, sticky="w", padx=(0, 10)
        )
        ttk.Button(
            bottom,
            text="Ouvrir le dossier",
            command=self._open_device_folder,
            style="Dialog.TButton",
        ).grid(row=0, column=2, sticky="w", padx=(0, 12))
        Label(bottom, text="Detail (optionnel):").grid(row=0, column=3, sticky="e", padx=(8, 4))
        ttk.Entry(bottom, textvariable=self.var_detail).grid(row=0, column=4, sticky="ew")

        self._reload()
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        ttk.Button(box, text="Fermer", command=self.cancel, style="Dialog.TButton").pack(padx=5, pady=6)
        box.pack()

    def _reload(self) -> None:
        all_rows = list_local_config_versions(
            local_versions_root=self.local_versions_root,
            device_type_label=self.device_type_label,
            device_name=self.device_name,
        )
        rows = self._apply_filter_sort(
            all_rows,
            searchable_text=lambda row: " ".join(
                [
                    str(row.get("modified_at", "")),
                    str(row.get("name", "")),
                    str(row.get("detail", "")),
                ]
            ),
            sort_value=lambda row, col: (
                str(row.get("name", "")).lower()
                if col == "name"
                else str(row.get("detail", "")).lower()
                if col == "detail"
                else str(row.get("modified_at", "")).lower()
            ),
        )
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for idx, row in enumerate(rows):
            iid = f"row_{idx}"
            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(str(row.get("modified_at", "")), str(row.get("name", "")), str(row.get("detail", ""))),
            )
        self._rows = rows

    def _selected_filename(self) -> str:
        sel = self.tree.selection()
        if not sel:
            return ""
        idx = int(str(sel[0]).split("_")[-1])
        if idx < 0 or idx >= len(self._rows):
            return ""
        return str(self._rows[idx].get("name", ""))

    def _selected_row(self) -> dict | None:
        filename = self._selected_filename()
        if not filename:
            return None
        for row in self._rows:
            if str(row.get("name", "")) == filename:
                return row
        return None

    def _device_folder(self) -> Path:
        return resolve_local_device_versions_dir(
            local_versions_root=self.local_versions_root,
            device_type_label=self.device_type_label,
            device_name=self.device_name,
        )

    def _open_device_folder(self) -> None:
        folder = self._device_folder()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            open_path_with_default_app(folder)
        except Exception as exc:
            messagebox.showerror("Fichiers de configuration", f"Impossible d'ouvrir le dossier: {exc}", parent=self)

    def _download_selected(self) -> None:
        row = self._selected_row()
        if not row:
            return
        source = Path(str(row.get("path", "")))
        if not source.is_file():
            messagebox.showwarning("Fichiers de configuration", "Fichier introuvable.", parent=self)
            self._reload()
            return
        target = filedialog.asksaveasfilename(
            parent=self,
            title="Telecharger le fichier de configuration",
            initialfile=source.name,
            defaultextension=source.suffix or ".cfg",
            filetypes=[("Config", "*.cfg *.conf *.txt"), ("Tous les fichiers", "*.*")],
        )
        if not target:
            return
        try:
            shutil.copy2(source, target)
        except Exception as exc:
            messagebox.showerror("Fichiers de configuration", f"Telechargement impossible: {exc}", parent=self)

    def _rename_selected(self) -> None:
        current = self._selected_filename()
        if not current:
            return
        new_name = simpledialog.askstring(
            "Renommer le fichier",
            "Nouveau nom du fichier :",
            initialvalue=current,
            parent=self,
        )
        if new_name is None:
            return
        try:
            renamed = rename_local_config_version(
                local_versions_root=self.local_versions_root,
                device_type_label=self.device_type_label,
                device_name=self.device_name,
                filename=current,
                new_filename=new_name,
            )
        except FileExistsError as exc:
            messagebox.showerror("Fichiers de configuration", str(exc), parent=self)
            return
        except ValueError as exc:
            messagebox.showerror("Fichiers de configuration", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Fichiers de configuration", f"Renommage impossible: {exc}", parent=self)
            return
        if renamed is None:
            messagebox.showwarning("Fichiers de configuration", "Fichier introuvable.", parent=self)
        self._reload()

    def _on_tree_right_click(self, event) -> None:
        row_id = str(self.tree.identify_row(event.y))
        if row_id:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
        if not self._selected_filename():
            return
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Telecharger", command=self._download_selected)
        menu.add_command(label="Editer", command=self._rename_selected)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _import_file(self) -> None:
        source = filedialog.askopenfilename(
            parent=self,
            title="Importer un fichier de configuration",
            filetypes=[("Config", "*.cfg *.conf *.txt"), ("Tous les fichiers", "*.*")],
        )
        if not source:
            return
        try:
            store_imported_config_version(
                local_versions_root=self.local_versions_root,
                device_type_label=self.device_type_label,
                device_name=self.device_name,
                source_file=Path(source),
                detail=self.var_detail.get().strip(),
            )
        except Exception as exc:
            messagebox.showerror("Fichiers de configuration", f"Import impossible: {exc}", parent=self)
            return
        self.var_detail.set("")
        self._reload()

    def _delete_selected(self) -> None:
        filename = self._selected_filename()
        if not filename:
            return
        if not messagebox.askyesno(
            "Fichiers de configuration",
            f"Supprimer ce fichier ?\n{filename}",
            parent=self,
        ):
            return
        deleted = delete_local_config_version(
            local_versions_root=self.local_versions_root,
            device_type_label=self.device_type_label,
            device_name=self.device_name,
            filename=filename,
        )
        if not deleted:
            messagebox.showwarning("Fichiers de configuration", "Fichier introuvable.", parent=self)
        self._reload()
