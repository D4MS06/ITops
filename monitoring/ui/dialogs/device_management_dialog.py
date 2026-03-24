from __future__ import annotations

from tkinter import Frame, StringVar, messagebox, ttk

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.dialogs.themed_dialog import ThemedDialog
from monitoring.ui.utils.searchable_sortable_tree import SearchableSortableTreeMixin


class DeviceManagementDialog(SearchableSortableTreeMixin, ThemedDialog):
    """Dedicated inventory management dialog, independent from monitoring runtime state."""

    _DELETE_COL = "delete"
    _DELETE_COL_INDEX = "#4"
    _TRASH_ICON = "\U0001F5D1"

    def __init__(
        self,
        parent,
        *,
        model: DevicesModel,
        controller: AppController,
        settings_service=None,
        device_actions_service=None,
    ) -> None:
        self.model = model
        self.controller = controller
        self.settings_service = settings_service
        self.device_actions_service = device_actions_service
        self.var_type = StringVar(value="")
        self.var_search = StringVar(value="")
        self._type_code_by_label: dict[str, str] = {}
        super().__init__(parent, title="Gestion des equipements")

    def body(self, master) -> Frame:
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(2, weight=1)

        top = Frame(master)
        top.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))
        top.grid_columnconfigure(1, weight=1)

        ttk.Label(top, text="Type :").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.type_combo = ttk.Combobox(
            top,
            textvariable=self.var_type,
            state="readonly",
            style="Dialog.TCombobox",
        )
        self.type_combo.grid(row=0, column=1, sticky="ew")
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)
        self.btn_add = ttk.Button(top, text="+", width=3, command=self._on_add, style="Dialog.TButton")
        self.btn_add.grid(row=0, column=2, sticky="e", padx=(8, 0))

        search_row = Frame(master)
        search_row.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 2))
        search_row.grid_columnconfigure(1, weight=1)
        ttk.Label(search_row, text="Recherche :").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.search_entry = ttk.Entry(search_row, textvariable=self.var_search, style="Dialog.TEntry")
        self.search_entry.grid(row=0, column=1, sticky="ew")

        table = Frame(master)
        table.grid(row=2, column=0, sticky="nsew", padx=6, pady=4)
        table.grid_columnconfigure(0, weight=1)
        table.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table,
            columns=("name", "ip", "description", self._DELETE_COL),
            show="headings",
            selectmode="browse",
            style="Dialog.Treeview",
        )
        self.tree.heading("name", text="Nom")
        self.tree.heading("ip", text="IP")
        self.tree.heading("description", text="Description")
        self.tree.heading(self._DELETE_COL, text="")
        self.tree.column("name", width=220, minwidth=160, stretch=True, anchor="w")
        self.tree.column("ip", width=150, minwidth=120, stretch=False, anchor="w")
        self.tree.column("description", width=300, minwidth=180, stretch=True, anchor="w")
        self.tree.column(self._DELETE_COL, width=52, minwidth=44, stretch=False, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-1>", self._on_tree_click)
        self._init_searchable_sortable_tree(
            tree=self.tree,
            search_var=self.var_search,
            on_query_changed=self._reload_tree,
            search_container=search_row,
            default_sort_col="name",
            default_sort_reverse=False,
        )

        scroll = ttk.Scrollbar(
            table,
            orient="vertical",
            command=self.tree.yview,
            style="Dialog.Vertical.TScrollbar",
        )
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")

        self._reload_type_choices()
        self._reload_tree()
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        ttk.Button(box, text="Fermer", command=self.cancel, style="Dialog.TButton").pack(padx=6, pady=8)
        box.pack()

    def _reload_type_choices(self) -> None:
        try:
            self.model.refresh_type_definitions()
        except Exception:
            pass
        pairs = sorted(
            (
                str(meta.get("label", code) or code),
                str(code),
            )
            for code, meta in dict(self.model.type_definitions).items()
        )
        self._type_code_by_label = {label: code for label, code in pairs}
        labels = [label for label, _code in pairs]
        self.type_combo["values"] = labels
        current_label = self.var_type.get().strip()
        if current_label in self._type_code_by_label:
            return
        self.var_type.set(labels[0] if labels else "")
        self.btn_add.configure(state="normal" if labels else "disabled")

    def _selected_type_code(self) -> str:
        return str(self._type_code_by_label.get(self.var_type.get().strip(), "")).strip().lower()

    def _selected_type_label(self) -> str:
        return str(self.var_type.get() or "").strip() or self._selected_type_code()

    def _reload_tree(self) -> None:
        selected_type = self._selected_type_code()
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not selected_type:
            self._set_search_visible(False)
            return

        devices = list(self.model.device_data.get(selected_type, {}).items())
        devices = self._apply_filter_sort(
            devices,
            searchable_text=lambda item: " ".join(
                [
                    str(getattr(item[1], "name", "")),
                    str(getattr(item[1], "ip", "")),
                    str(getattr(item[1], "description", "")),
                ]
            ),
            sort_value=lambda item, col: (
                str(getattr(item[1], "ip", "")).strip()
                if col == "ip"
                else str(getattr(item[1], "description", "")).lower()
                if col == "description"
                else str(getattr(item[1], "name", "")).lower()
            ),
        )
        for device_id, dev in devices:
            row_id = str(device_id)
            self.tree.insert(
                "",
                "end",
                iid=row_id,
                values=(
                    str(getattr(dev, "name", "")),
                    str(getattr(dev, "ip", "")),
                    str(getattr(dev, "description", "")),
                    self._TRASH_ICON,
                ),
            )

    def _current_selection(self) -> tuple[str | None, object | None]:
        selected_type = self._selected_type_code()
        if not selected_type:
            return None, None
        selection = tuple(self.tree.selection())
        if not selection:
            focused = str(self.tree.focus() or "").strip()
            device_id = focused or None
        else:
            device_id = str(selection[0])
        if not device_id:
            return None, None
        return device_id, self.model.device_data.get(selected_type, {}).get(device_id)

    def _device_form_initial(self, device_id: str, device) -> dict[str, object]:
        selected_type = self._selected_type_code()
        return {
            "name": getattr(device, "name", ""),
            "ip": getattr(device, "ip", ""),
            "desc": getattr(device, "description", ""),
            "subtype": getattr(device, "type", ""),
            "tv_id": getattr(device, "id_Teamviewer", ""),
            "action_double_click": getattr(device, "action_double_click", ""),
            "web_url": getattr(device, "web_url", ""),
            "ssh_user": getattr(device, "ssh_user", ""),
            "notify": self.model.notify_flags.get(selected_type, {}).get(device_id, True),
            "custom_data": self.model.extract_custom_data(device),
        }

    def _on_type_changed(self, _event=None) -> None:
        self._reload_tree()

    def _on_add(self) -> None:
        selected_type = self._selected_type_code()
        if not selected_type:
            messagebox.showinfo("Gestion des equipements", "Aucun type disponible.", parent=self)
            return
        dialog = DeviceForm(
            self.parent,
            title=f"Ajouter {self._selected_type_label()}",
            default_type=selected_type,
        )
        if dialog.result is None:
            return
        created_id = self.model.add_device(
            selected_type,
            str(dialog.result.get("name", "")),
            str(dialog.result.get("ip", "")),
            str(dialog.result.get("desc", "")),
            id_Teamviewer=str(dialog.result.get("tv_id", "")),
            device_subtype=str(dialog.result.get("subtype", "")),
            action_double_click=str(dialog.result.get("action_double_click", "")),
            web_url=str(dialog.result.get("web_url", "")),
            ssh_user=str(dialog.result.get("ssh_user", "")),
            custom_data=dict(dialog.result.get("custom_data", {}) or {}),
            notify=bool(dialog.result.get("notify", True)),
        )
        if not created_id:
            messagebox.showwarning("Gestion des equipements", "Adresse IP deja utilisee.", parent=self)
            return
        self._reload_tree()
        self.controller.refresh_views()

    def _edit_selected_device(self) -> None:
        selected_type = self._selected_type_code()
        if not selected_type:
            return
        device_id, device = self._current_selection()
        if not device_id or device is None:
            return

        dialog = DeviceForm(
            self.parent,
            title=f"Modifier {self._selected_type_label()}",
            default_type=selected_type,
            initial=self._device_form_initial(device_id, device),
        )
        if dialog.result is None:
            return
        updated = self.model.update_device(
            selected_type,
            device_id,
            new_name=str(dialog.result.get("name", "")),
            new_ip=str(dialog.result.get("ip", "")),
            new_description=str(dialog.result.get("desc", "")),
            id_Teamviewer=str(dialog.result.get("tv_id", "")),
            device_subtype=str(dialog.result.get("subtype", "")),
            action_double_click=str(dialog.result.get("action_double_click", "")),
            web_url=str(dialog.result.get("web_url", "")),
            ssh_user=str(dialog.result.get("ssh_user", "")),
            custom_data=dict(dialog.result.get("custom_data", {}) or {}),
            notify=bool(dialog.result.get("notify", True)),
        )
        if not updated:
            messagebox.showerror("Gestion des equipements", "Mise a jour impossible.", parent=self)
            return
        self._reload_tree()
        try:
            self.tree.selection_set(device_id)
            self.tree.focus(device_id)
        except Exception:
            pass
        self.controller.refresh_views()

    def _delete_device(self, device_id: str) -> None:
        selected_type = self._selected_type_code()
        if not selected_type:
            return
        device = self.model.device_data.get(selected_type, {}).get(device_id)
        if device is None:
            self._reload_tree()
            return
        device_name = str(getattr(device, "name", "")).strip() or str(getattr(device, "ip", "")).strip() or device_id
        confirmed = messagebox.askyesno(
            "Confirmation",
            f"Supprimer cet equipement ?\n{device_name}",
            parent=self,
        )
        if not confirmed:
            return
        if not self.model.delete_device(selected_type, device_id):
            messagebox.showwarning("Gestion des equipements", "Suppression impossible.", parent=self)
            return
        self._reload_tree()
        self.controller.refresh_views()

    def _on_tree_double_click(self, event) -> None:
        row_id = str(self.tree.identify_row(event.y))
        if not row_id:
            return
        column = str(self.tree.identify_column(event.x))
        if column == self._DELETE_COL_INDEX:
            self._delete_device(row_id)
            return
        self.tree.selection_set(row_id)
        self.tree.focus(row_id)
        self._edit_selected_device()

    def _on_tree_click(self, event) -> None:
        row_id = str(self.tree.identify_row(event.y))
        if not row_id:
            return
        column = str(self.tree.identify_column(event.x))
        if column != self._DELETE_COL_INDEX:
            return
        self.tree.selection_set(row_id)
        self.tree.focus(row_id)
        self._delete_device(row_id)
        return "break"
