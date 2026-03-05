from __future__ import annotations

import os
import re
import tkinter as tk
import unicodedata
from tkinter import BooleanVar, Canvas, Frame, Label, PhotoImage, StringVar, messagebox, ttk

from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.ui.base_window import resource_path
from monitoring.ui.dialogs.themed_dialog import ThemedDialog
from monitoring.ui.utils.action_compat import PLATFORM_OPTIONS, action_allows_os, format_os_scope, normalize_platform, parse_os_scope


class FieldEditorDialog(ThemedDialog):
    FIELD_KINDS = ["text", "ip", "url", "choice"]

    def __init__(self, parent, *, initial: dict | None = None, title: str = "Champ") -> None:
        self._initial = initial or {}
        self.result: dict | None = None

        self.var_label = StringVar(value=str(self._initial.get("label", "")))
        self.var_kind = StringVar(value=str(self._initial.get("field_kind", "text") or "text"))
        self.var_required = BooleanVar(value=bool(self._initial.get("required", False)))
        raw_options = str(self._initial.get("options", "") or "")
        self._options_items: list[str] = [part.strip() for part in raw_options.split(",") if part.strip()]
        self.var_option_item = StringVar(value="")
        self.var_default = StringVar(value=str(self._initial.get("default_value", "")))
        super().__init__(parent, title=title)

    def body(self, master) -> Frame:
        master.grid_columnconfigure(1, weight=1)

        Label(master, text="Label").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(master, textvariable=self.var_label).grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        Label(master, text="Nature du champ").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        ttk.Combobox(master, textvariable=self.var_kind, values=self.FIELD_KINDS, state="readonly").grid(
            row=1,
            column=1,
            sticky="ew",
            padx=4,
            pady=4,
        )

        self.options_frame = ttk.LabelFrame(master, text="Options de la liste")
        self.options_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
        self.options_frame.grid_columnconfigure(0, weight=1)

        self.options_list = tk.Listbox(self.options_frame, height=5, exportselection=False)
        self.options_list.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 2))
        self._refresh_options_list()

        ttk.Entry(self.options_frame, textvariable=self.var_option_item).grid(row=1, column=0, sticky="ew", padx=4, pady=(2, 4))
        ttk.Button(self.options_frame, text="+ Ajouter", command=self._add_option_item, style="Dialog.TButton").grid(row=1, column=1, padx=2, pady=(2, 4))
        ttk.Button(self.options_frame, text="- Supprimer", command=self._remove_option_item, style="Dialog.TButton").grid(row=1, column=2, padx=(2, 4), pady=(2, 4))

        Label(master, text="Valeur par defaut").grid(row=3, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(master, textvariable=self.var_default).grid(row=3, column=1, sticky="ew", padx=4, pady=4)

        ttk.Checkbutton(master, text="Champ obligatoire", variable=self.var_required).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            padx=4,
            pady=(6, 2),
        )

        self.var_kind.trace_add("write", self._on_kind_change)
        self._toggle_options_visibility()
        self.bind("<Return>", lambda _e: self._add_option_item())
        self.apply_theme(master)
        return master

    def _on_kind_change(self, *_args) -> None:
        self._toggle_options_visibility()

    def _toggle_options_visibility(self) -> None:
        is_choice = self.var_kind.get().strip().lower() == "choice"
        if is_choice:
            self.options_frame.grid()
        else:
            self.options_frame.grid_remove()

    def _refresh_options_list(self) -> None:
        self.options_list.delete(0, tk.END)
        for item in self._options_items:
            self.options_list.insert(tk.END, item)

    def _add_option_item(self) -> None:
        item = self.var_option_item.get().strip()
        if not item:
            return
        if item in self._options_items:
            self.var_option_item.set("")
            return
        self._options_items.append(item)
        self.var_option_item.set("")
        self._refresh_options_list()

    def _remove_option_item(self) -> None:
        sel = self.options_list.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._options_items):
            self._options_items.pop(idx)
            self._refresh_options_list()

    def validate(self) -> bool:
        if not self.var_label.get().strip():
            messagebox.showerror("Champ", "Le label est obligatoire.", parent=self)
            return False
        if self.var_kind.get().strip().lower() == "choice" and not self._options_items:
            messagebox.showerror("Champ", "Ajoutez au moins une option pour une liste.", parent=self)
            return False
        return True

    def apply(self) -> None:
        self.result = {
            "label": self.var_label.get().strip(),
            "field_kind": self.var_kind.get().strip().lower() or "text",
            "required": bool(self.var_required.get()),
            "options": ",".join(self._options_items),
            "default_value": self.var_default.get().strip(),
        }


class ActionEditorDialog(ThemedDialog):
    TARGET_KINDS = ["builtin", "custom"]

    def __init__(self, parent, *, initial: dict | None = None) -> None:
        self._initial = initial or {}
        self.result: dict | None = None

        self.var_key = StringVar(value=str(self._initial.get("action_key", "")))
        self.var_label = StringVar(value=str(self._initial.get("label", "")))
        self.var_target_kind = StringVar(value=str(self._initial.get("target_kind", "builtin") or "builtin"))
        self.var_target_value = StringVar(value=str(self._initial.get("target_value", "")))
        self.var_default = BooleanVar(value=bool(self._initial.get("is_default", False)))
        super().__init__(parent, title="Action contextuelle")

    def body(self, master) -> Frame:
        master.grid_columnconfigure(1, weight=1)

        Label(master, text="Cle action").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(master, textvariable=self.var_key).grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        Label(master, text="Label action").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(master, textvariable=self.var_label).grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        Label(master, text="Type cible").grid(row=2, column=0, sticky="e", padx=4, pady=4)
        ttk.Combobox(master, textvariable=self.var_target_kind, values=self.TARGET_KINDS, state="readonly").grid(
            row=2,
            column=1,
            sticky="ew",
            padx=4,
            pady=4,
        )

        Label(master, text="Valeur cible").grid(row=3, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(master, textvariable=self.var_target_value).grid(row=3, column=1, sticky="ew", padx=4, pady=4)

        ttk.Checkbutton(master, text="Action par defaut", variable=self.var_default).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            padx=4,
            pady=(6, 2),
        )

        self.apply_theme(master)
        return master

    def validate(self) -> bool:
        if not self.var_key.get().strip().lower():
            messagebox.showerror("Action", "La cle action est obligatoire.", parent=self)
            return False
        if not self.var_label.get().strip():
            messagebox.showerror("Action", "Le label action est obligatoire.", parent=self)
            return False
        return True

    def apply(self) -> None:
        self.result = {
            "action_key": self.var_key.get().strip().lower(),
            "label": self.var_label.get().strip(),
            "target_kind": self.var_target_kind.get().strip().lower() or "builtin",
            "target_value": self.var_target_value.get().strip(),
            "is_default": bool(self.var_default.get()),
        }

class DeviceTypeSchemaEditorDialog(ThemedDialog):
    CORE_FIELDS = {
        "name": {"label": "Nom", "field_kind": "text", "required": True, "options": "", "default_value": ""},
        "description": {"label": "Description", "field_kind": "text", "required": False, "options": "", "default_value": ""},
        "type": {
            "label": "OS",
            "field_kind": "choice",
            "required": True,
            "options": "Windows,Linux,Firmware,Autre",
            "default_value": "Windows",
        },
        "ip": {"label": "IP", "field_kind": "ip", "required": True, "options": "", "default_value": ""},
    }
    PLUGIN_BLOCKS = [
        {"key": "ssh", "title": "SSH", "badge": "SSH"},
        {"key": "teamviewer", "title": "TeamViewer", "badge": "TV"},
        {"key": "remote_desktop", "title": "Remote Desktop", "badge": "RDP"},
        {"key": "web", "title": "Web", "badge": "WEB"},
    ]
    COLOR_PALETTE_BG = "#EAF3FF"
    COLOR_MENU_BG = "#EAFBF0"
    COLOR_DOUBLE_BG = "#FFF6E8"
    COLOR_CATALOG_FRAME = "#C6DCF7"
    COLOR_BORDER_NORMAL = "#B7C8DC"
    COLOR_BORDER_ADD = "#25A244"
    COLOR_BORDER_REMOVE = "#D62828"

    def __init__(
        self,
        parent,
        *,
        type_code: str,
        type_label: str,
        monitoring_enabled: bool,
        create_mode: bool = False,
        on_saved=None,
    ) -> None:
        self._mgr = SQLiteFileManager()
        self._type_code = str(type_code).strip().lower()
        self._type_label = str(type_label).strip() or self._type_code
        self._monitoring_enabled = bool(monitoring_enabled)
        self._create_mode = bool(create_mode)
        self.var_type_label = StringVar(value=self._type_label if self._create_mode else "")
        self.var_monitoring_enabled = BooleanVar(value=self._monitoring_enabled)
        self.var_catalog_os = StringVar(value=PLATFORM_OPTIONS[0])
        self._on_saved = on_saved
        self._fields: list[dict] = []
        self._actions: list[dict] = []
        self._drag_block_key = ""
        self._drag_action_key = ""
        self._drag_proxy: Label | None = None
        self._menu_tile_by_key: dict[str, Label] = {}
        self._menu_insert_line_id: int | None = None
        self._drag_origin_tile: Label | None = None
        self._plugin_icons: dict[str, PhotoImage | None] = {}
        self._plugin_icons_catalog: dict[str, PhotoImage | None] = {}
        self._tile_images: list[PhotoImage] = []
        self._load_plugin_icons()
        title = "Nouveau type de device" if self._create_mode else f"Edition du formulaire: {self._type_label}"
        super().__init__(parent, title=title)

    def _load_plugin_icons(self) -> None:
        icon_map = {
            "ssh": os.path.join("monitoring", "ui", "assets", "plugin_ssh.png"),
            "teamviewer": os.path.join("monitoring", "ui", "assets", "plugin_teamviewer.png"),
            "remote_desktop": os.path.join("monitoring", "ui", "assets", "plugin_remote_desktop.png"),
            "web": os.path.join("monitoring", "ui", "assets", "plugin_web.png"),
        }
        for key, rel in icon_map.items():
            try:
                img = PhotoImage(file=resource_path(rel))
                self._plugin_icons_catalog[key] = img.subsample(10, 10)
                self._plugin_icons[key] = img.subsample(28, 28)
            except Exception:
                self._plugin_icons_catalog[key] = None
                self._plugin_icons[key] = None

    def body(self, master) -> Frame:
        master.grid_columnconfigure(0, weight=5)
        master.grid_columnconfigure(1, weight=3)
        master.grid_rowconfigure(0, weight=1)

        left = Frame(master)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(3, weight=1)

        start_row = 0
        if self._create_mode:
            setup = ttk.LabelFrame(left, text="Nouveau type")
            setup.grid(row=0, column=0, sticky="ew", pady=(0, 10))
            setup.grid_columnconfigure(1, weight=1)
            Label(setup, text="Nom du type :").grid(row=0, column=0, sticky="e", padx=6, pady=6)
            ttk.Entry(setup, textvariable=self.var_type_label).grid(row=0, column=1, sticky="ew", padx=6, pady=6)
            ttk.Checkbutton(setup, text="Type monitorable", variable=self.var_monitoring_enabled).grid(
                row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6)
            )
            self.var_monitoring_enabled.trace_add("write", self._on_monitoring_changed)
            start_row = 1

        Label(left, text="1) Champs obligatoires", anchor="w", font=("Segoe UI", 10, "bold")).grid(
            row=start_row, column=0, sticky="ew", pady=(0, 4)
        )
        self.core_container = ttk.LabelFrame(left, text="Preconfigures")
        self.core_container.grid(row=start_row + 1, column=0, sticky="ew", pady=(0, 10))
        self.core_container.grid_columnconfigure(0, weight=1)

        Label(left, text="2) Champs personnalises", anchor="w", font=("Segoe UI", 10, "bold")).grid(
            row=start_row + 2, column=0, sticky="ew", pady=(0, 4)
        )
        self.custom_container = ttk.LabelFrame(left, text="Formulaire")
        self.custom_container.grid(row=start_row + 3, column=0, sticky="nsew")
        self.custom_container.grid_columnconfigure(0, weight=1)

        custom_toolbar = Frame(left)
        custom_toolbar.grid(row=start_row + 4, column=0, sticky="ew", pady=(6, 10))
        ttk.Button(custom_toolbar, text="+ Ajouter un champ", command=self._add_custom_field, style="Dialog.TButton").pack(side="left")

        right = Frame(master)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        Label(right, text="Apercu de la fenetre Modifier un device", anchor="w", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="ew", pady=(0, 4)
        )
        self.preview_box = ttk.LabelFrame(right, text="Rendu du formulaire")
        self.preview_box.grid(row=1, column=0, sticky="nsew")
        self.preview_box.grid_columnconfigure(0, weight=1)

        self.preview_form = Frame(self.preview_box)
        self.preview_form.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.preview_form.grid_columnconfigure(1, weight=1)

        toolbox = ttk.LabelFrame(right, text="Catalogue plugins")
        toolbox.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        toolbox.grid_columnconfigure(0, weight=1)

        scope_picker = Frame(toolbox)
        scope_picker.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))
        Label(scope_picker, text="OS cible :").pack(side="left")
        self.catalog_os_combo = ttk.Combobox(
            scope_picker,
            textvariable=self.var_catalog_os,
            values=list(PLATFORM_OPTIONS),
            state="readonly",
            width=12,
        )
        self.catalog_os_combo.pack(side="left", padx=(6, 0))
        self.catalog_os_combo.bind("<<ComboboxSelected>>", self._on_catalog_os_change)

        palette_panel = Frame(toolbox, bg=self.COLOR_CATALOG_FRAME, bd=2, relief="ridge")
        palette_panel.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        palette = Frame(palette_panel, bg=self.COLOR_PALETTE_BG, bd=1, relief="solid")
        palette.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        for idx, block in enumerate(self.PLUGIN_BLOCKS):
            block_key = str(block["key"])
            img = self._plugin_icons_catalog.get(block_key)
            icon = Label(
                palette,
                text=str(block["badge"]),
                relief="ridge",
                bd=1,
                padx=4,
                pady=4,
                cursor="hand2",
                compound="left",
                bg=self.COLOR_PALETTE_BG,
            )
            if img is not None:
                icon.configure(image=img, text="")
                icon.image = img
            icon.grid(row=0, column=idx, padx=(0 if idx == 0 else 6, 0), pady=2, sticky="w")
            icon.bind("<ButtonPress-1>", lambda evt, k=block_key: self._start_drag_plugin(evt, k))
            icon.bind("<B1-Motion>", self._drag_plugin_motion)
            icon.bind("<ButtonRelease-1>", self._drop_plugin)

        self.drop_menu_zone = ttk.LabelFrame(toolbox, text="Deposer ici: Menu contextuel")
        self.drop_menu_zone.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 3))
        self.menu_panel = Frame(
            self.drop_menu_zone,
            bg=self.COLOR_MENU_BG,
            bd=1,
            relief="solid",
            highlightthickness=2,
            highlightbackground=self.COLOR_BORDER_NORMAL,
        )
        self.menu_panel.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 4))
        self.menu_panel.grid_columnconfigure(0, weight=1)
        self.menu_tiles_canvas = Canvas(self.menu_panel, bg=self.COLOR_MENU_BG, height=38, highlightthickness=0, bd=0)
        self.menu_tiles_canvas.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 1))
        self.menu_tiles_scroll = ttk.Scrollbar(self.menu_panel, orient="horizontal", command=self.menu_tiles_canvas.xview)
        self.menu_tiles_scroll.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 3))
        self.menu_tiles_canvas.configure(xscrollcommand=self.menu_tiles_scroll.set)
        self.menu_tiles_container = Frame(self.menu_tiles_canvas, bg=self.COLOR_MENU_BG)
        self._menu_canvas_window = self.menu_tiles_canvas.create_window(
            (0, 0),
            window=self.menu_tiles_container,
            anchor="nw",
        )
        self.menu_tiles_container.bind(
            "<Configure>",
            lambda _e: self.menu_tiles_canvas.configure(scrollregion=self.menu_tiles_canvas.bbox("all")),
        )

        self._load_schema()
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        ttk.Button(box, text="Enregistrer formulaire", command=self._save_schema, style="Dialog.TButton").pack(side="left", padx=5, pady=6)
        ttk.Button(box, text="Fermer", command=self.cancel, style="Dialog.TButton").pack(side="left", padx=5, pady=6)
        box.pack()

    def _load_schema(self) -> None:
        if self._create_mode:
            self._fields = []
            self._actions = []
            self._monitoring_enabled = bool(self.var_monitoring_enabled.get())
        else:
            self._fields = sorted(self._mgr.list_type_fields(self._type_code), key=lambda x: int(x.get("sort_order", 0)))
            self._actions = sorted(self._mgr.list_type_actions(self._type_code), key=lambda x: int(x.get("sort_order", 0)))
        for action in self._actions:
            scope = str(action.get("os_scope", "")).strip()
            if not scope:
                action["os_scope"] = format_os_scope(["windows", "linux", "firmware", "autre"])
        self._fields = [f for f in self._fields if str(f.get("field_key", "")).strip() != "action_double_click"]
        self._ensure_core_fields()
        self._reindex_sorts()
        self._render_all()

    def _on_monitoring_changed(self, *_args) -> None:
        self._monitoring_enabled = bool(self.var_monitoring_enabled.get())
        self._ensure_core_fields()
        self._reindex_sorts()
        self._render_all()

    def _on_catalog_os_change(self, _evt=None) -> None:
        self._render_drop_tiles()

    def _start_drag_plugin(self, event, block_key: str) -> None:
        self._drag_block_key = str(block_key or "").strip().lower()
        if not self._drag_block_key:
            return
        if self._drag_proxy is not None:
            self._drag_proxy.destroy()
        self._drag_proxy = Label(self, text=self._drag_block_key.upper(), relief="solid", bd=1, padx=6, pady=4)
        self._move_drag_proxy(event.x_root, event.y_root)
        self._set_menu_border(self.COLOR_BORDER_NORMAL)

    def _drag_plugin_motion(self, event) -> None:
        if self._drag_proxy is None:
            return
        self._move_drag_proxy(event.x_root, event.y_root)
        target = self.winfo_containing(event.x_root, event.y_root)
        in_menu = bool(target is not None and self._widget_inside(target, self.drop_menu_zone))
        self._set_menu_border(self.COLOR_BORDER_ADD if in_menu else self.COLOR_BORDER_NORMAL)

    def _drop_plugin(self, event) -> None:
        block_key = self._drag_block_key
        self._drag_block_key = ""
        if self._drag_proxy is not None:
            self._drag_proxy.destroy()
            self._drag_proxy = None
        self._set_menu_border(self.COLOR_BORDER_NORMAL)
        if not block_key:
            return

        target = self.winfo_containing(event.x_root, event.y_root)
        if target is None:
            return
        if self._widget_inside(target, self.drop_menu_zone):
            self._apply_block_to_menu(block_key)
            return

    def _selected_catalog_os(self) -> str:
        return normalize_platform(self.var_catalog_os.get())

    def _action_in_selected_os(self, action: dict) -> bool:
        return action_allows_os(str(action.get("os_scope", "")), self._selected_catalog_os())

    def _set_action_os_membership(self, action_key: str, enabled: bool) -> bool:
        key = str(action_key or "").strip().lower()
        target_os = self._selected_catalog_os()
        changed = False
        for action in self._actions:
            if str(action.get("action_key", "")).strip().lower() != key:
                continue
            scope = parse_os_scope(str(action.get("os_scope", "")))
            before = set(scope)
            if enabled:
                scope.add(target_os)
            else:
                scope.discard(target_os)
            action["os_scope"] = format_os_scope(scope)
            changed = scope != before
            break
        return changed

    def _start_drag_menu_action(self, event, action_key: str) -> None:
        self._drag_action_key = str(action_key or "").strip().lower()
        if not self._drag_action_key:
            return
        if self._drag_proxy is not None:
            self._drag_proxy.destroy()
        self._drag_proxy = Label(
            self,
            text=self._drag_action_key.upper(),
            relief="solid",
            bd=1,
            padx=6,
            pady=4,
            bg="#F6FAFF",
            fg="#3D4B5B",
        )
        self._set_drag_origin_tile(self._drag_action_key)
        self._clear_menu_insert_marker()
        self._move_drag_proxy(event.x_root, event.y_root)
        self._set_menu_border(self.COLOR_BORDER_NORMAL)

    def _drag_menu_action_motion(self, event) -> None:
        if self._drag_proxy is None:
            return
        self._move_drag_proxy(event.x_root, event.y_root)
        target = self.winfo_containing(event.x_root, event.y_root)
        in_menu = bool(target is not None and self._widget_inside(target, self.drop_menu_zone))
        if in_menu:
            self._set_menu_border(self.COLOR_BORDER_NORMAL)
            self._show_menu_insert_marker(self._drag_action_key, int(event.x_root))
        else:
            self._set_menu_border(self.COLOR_BORDER_REMOVE)
            self._clear_menu_insert_marker()

    def _drop_menu_action(self, event) -> None:
        action_key = self._drag_action_key
        self._drag_action_key = ""
        if self._drag_proxy is not None:
            self._drag_proxy.destroy()
            self._drag_proxy = None
        self._set_drag_origin_tile("")
        self._clear_menu_insert_marker()
        self._set_menu_border(self.COLOR_BORDER_NORMAL)
        if not action_key:
            return
        target = self.winfo_containing(event.x_root, event.y_root)
        if target is None:
            return
        if self._widget_inside(target, self.drop_menu_zone):
            self._reorder_action_by_position(action_key, int(event.x_root))
            return
        changed = self._set_action_os_membership(action_key, False)
        self._actions = [a for a in self._actions if str(a.get("os_scope", "")).strip()]
        if changed:
            self._reindex_sorts()
            self._render_all()

    def _reorder_action_by_position(self, action_key: str, x_root: int) -> None:
        dragged_key = str(action_key or "").strip().lower()
        if not dragged_key:
            return

        current_keys = [str(a.get("action_key", "")).strip().lower() for a in self._actions]
        visible_keys = [
            str(a.get("action_key", "")).strip().lower()
            for a in self._actions
            if self._action_in_selected_os(a)
        ]
        if dragged_key not in current_keys or dragged_key not in visible_keys:
            return
        if len(visible_keys) <= 1:
            return

        other_keys = [k for k in visible_keys if k != dragged_key]
        insert_idx = self._compute_menu_insert_index(dragged_key, x_root, other_keys)

        new_keys = list(other_keys)
        new_keys.insert(insert_idx, dragged_key)
        if new_keys == visible_keys:
            return

        visible_set = set(visible_keys)
        replacement = iter(new_keys)
        ordered_keys = [next(replacement) if key in visible_set else key for key in current_keys]
        action_by_key = {str(a.get("action_key", "")).strip().lower(): a for a in self._actions}
        self._actions = [action_by_key[k] for k in ordered_keys if k in action_by_key]
        self._reindex_sorts()
        self._render_all()

    def _compute_menu_insert_index(self, dragged_key: str, x_root: int, other_keys: list[str] | None = None) -> int:
        if other_keys is None:
            current_keys = [str(a.get("action_key", "")).strip().lower() for a in self._actions]
            other_keys = [k for k in current_keys if k != dragged_key]
        insert_idx = len(other_keys)
        for idx, key in enumerate(other_keys):
            tile = self._menu_tile_by_key.get(key)
            if tile is None or not tile.winfo_exists():
                continue
            center_x = tile.winfo_rootx() + (tile.winfo_width() // 2)
            if x_root < center_x:
                insert_idx = idx
                break
        return insert_idx

    def _show_menu_insert_marker(self, dragged_key: str, x_root: int) -> None:
        key = str(dragged_key or "").strip().lower()
        if not key:
            self._clear_menu_insert_marker()
            return
        current_keys = [
            str(a.get("action_key", "")).strip().lower()
            for a in self._actions
            if self._action_in_selected_os(a)
        ]
        other_keys = [k for k in current_keys if k != key]
        insert_idx = self._compute_menu_insert_index(key, x_root, other_keys)
        x = self._marker_x_for_insert_index(insert_idx, other_keys)
        if x < 0:
            self._clear_menu_insert_marker()
            return

        top = 4
        bottom = max(8, int(self.menu_tiles_canvas.winfo_height()) - 4)
        if self._menu_insert_line_id is None:
            self._menu_insert_line_id = self.menu_tiles_canvas.create_line(
                x,
                top,
                x,
                bottom,
                fill=self.COLOR_BORDER_ADD,
                width=2,
            )
        else:
            self.menu_tiles_canvas.coords(self._menu_insert_line_id, x, top, x, bottom)
            self.menu_tiles_canvas.itemconfigure(self._menu_insert_line_id, fill=self.COLOR_BORDER_ADD, width=2)

    def _marker_x_for_insert_index(self, insert_idx: int, keys: list[str]) -> int:
        if not keys:
            return 8
        if insert_idx <= 0:
            first = self._menu_tile_by_key.get(keys[0])
            if first is None or not first.winfo_exists():
                return 8
            return max(4, int(first.winfo_x()) - 3)
        if insert_idx >= len(keys):
            last = self._menu_tile_by_key.get(keys[-1])
            if last is None or not last.winfo_exists():
                return 8
            return int(last.winfo_x() + last.winfo_width() + 3)
        nxt = self._menu_tile_by_key.get(keys[insert_idx])
        if nxt is None or not nxt.winfo_exists():
            return 8
        return max(4, int(nxt.winfo_x()) - 3)

    def _clear_menu_insert_marker(self) -> None:
        if self._menu_insert_line_id is None:
            return
        try:
            self.menu_tiles_canvas.delete(self._menu_insert_line_id)
        except Exception:
            pass
        self._menu_insert_line_id = None

    def _set_drag_origin_tile(self, action_key: str) -> None:
        if self._drag_origin_tile is not None and self._drag_origin_tile.winfo_exists():
            try:
                self._drag_origin_tile.configure(bg=self.COLOR_MENU_BG, relief="ridge", bd=1)
            except Exception:
                pass
        self._drag_origin_tile = None
        key = str(action_key or "").strip().lower()
        if not key:
            return
        tile = self._menu_tile_by_key.get(key)
        if tile is None or not tile.winfo_exists():
            return
        try:
            tile.configure(bg="#D9E4F2", relief="sunken", bd=1)
        except Exception:
            return
        self._drag_origin_tile = tile

    def _move_drag_proxy(self, x_root: int, y_root: int) -> None:
        if self._drag_proxy is None:
            return
        x = int(x_root - self.winfo_rootx() + 10)
        y = int(y_root - self.winfo_rooty() + 10)
        self._drag_proxy.place(x=x, y=y)

    def _set_menu_border(self, color: str) -> None:
        try:
            self.menu_panel.configure(highlightbackground=color)
        except Exception:
            pass

    @staticmethod
    def _widget_inside(widget, container) -> bool:
        cur = widget
        while cur is not None:
            if cur == container:
                return True
            cur = cur.master
        return False

    @staticmethod
    def _slugify_label(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.strip().lower()).strip("_")
        return slug or "type"

    def _generate_unique_type_code(self, label: str) -> str:
        base = self._slugify_label(label)
        existing = {str(t.get("code", "")).strip().lower() for t in self._mgr.list_device_types()}
        candidate = base
        idx = 2
        while candidate in existing:
            candidate = f"{base}_{idx}"
            idx += 1
        return candidate

    def _ensure_core_fields(self) -> None:
        by_key = {str(f.get("field_key", "")): f for f in self._fields}
        for key in ("name", "description", "type"):
            if key not in by_key:
                by_key[key] = {"field_key": key, **self.CORE_FIELDS[key]}
        by_key["type"] = {
            **by_key["type"],
            "field_key": "type",
            "label": str(by_key["type"].get("label", "OS") or "OS"),
            "field_kind": "choice",
            "required": True,
            "options": self.CORE_FIELDS["type"]["options"],
            "default_value": str(by_key["type"].get("default_value", "Windows") or "Windows"),
        }
        if str(by_key["type"].get("default_value", "")).strip() not in {"Windows", "Linux", "Firmware", "Autre"}:
            by_key["type"]["default_value"] = "Windows"
        if self._monitoring_enabled:
            if "ip" not in by_key:
                by_key["ip"] = {"field_key": "ip", **self.CORE_FIELDS["ip"]}
        else:
            by_key.pop("ip", None)

        ordered = []
        for key in ("name", "description", "type", "ip"):
            if key in by_key:
                ordered.append(by_key.pop(key))
        custom_existing = [f for f in self._fields if str(f.get("field_key", "")) in by_key]
        seen = {str(f.get("field_key", "")) for f in ordered}
        for field in custom_existing:
            key = str(field.get("field_key", ""))
            if key not in seen and key in by_key:
                ordered.append(by_key[key])
                seen.add(key)
        for key, val in by_key.items():
            if key not in seen:
                ordered.append(val)
        self._fields = ordered

    def _reindex_sorts(self) -> None:
        for idx, field in enumerate(self._fields):
            field["sort_order"] = (idx + 1) * 10
        for idx, action in enumerate(self._actions):
            action["sort_order"] = (idx + 1) * 10

    def _render_all(self) -> None:
        self._render_core_fields()
        self._render_custom_fields()
        self._render_drop_tiles()
        self._render_preview()

    def _render_drop_tiles(self) -> None:
        self._tile_images = []
        self._menu_tile_by_key = {}
        self._clear_menu_insert_marker()
        self._drag_origin_tile = None
        self._clear_children(self.menu_tiles_container)

        visible_actions = [a for a in self._actions if self._action_in_selected_os(a)]
        for idx, action in enumerate(visible_actions):
            key = str(action.get("action_key", "")).strip().lower()
            label = str(action.get("label", key)).strip() or key
            tile = self._build_action_tile(self.menu_tiles_container, key, label)
            tile.grid(row=0, column=idx, padx=(0 if idx == 0 else 6, 0), pady=2, sticky="w")
            self._menu_tile_by_key[key] = tile
            tile.bind("<ButtonPress-1>", lambda evt, k=key: self._start_drag_menu_action(evt, k))
            tile.bind("<B1-Motion>", self._drag_menu_action_motion)
            tile.bind("<ButtonRelease-1>", self._drop_menu_action)
        self.menu_tiles_canvas.configure(scrollregion=self.menu_tiles_canvas.bbox("all"))

    def _build_action_tile(self, parent: Frame, action_key: str, _label: str) -> Label:
        icon = self._action_badge(action_key)
        tile = Label(parent, text=icon, relief="ridge", bd=1, padx=1, pady=1, compound="left", bg=parent.cget("bg"))
        img = self._plugin_icons.get(str(action_key).strip().lower())
        if img is not None:
            tile.configure(image=img, text="")
            tile.image = img
            self._tile_images.append(img)
        return tile

    def _action_badge(self, action_key: str) -> str:
        key = str(action_key or "").strip().lower()
        for block in self.PLUGIN_BLOCKS:
            if str(block.get("key", "")).strip().lower() == key:
                return str(block.get("badge", "ACT"))
        return "ACT"

    @staticmethod
    def _clear_children(widget: Frame) -> None:
        for child in widget.winfo_children():
            child.destroy()

    @staticmethod
    def _kind_label(kind: str) -> str:
        return {"text": "Texte", "ip": "IP", "url": "URL", "choice": "Liste"}.get(str(kind), str(kind))

    def _core_field_keys(self) -> list[str]:
        keys = ["name", "description", "type"]
        if self._monitoring_enabled:
            keys.append("ip")
        return keys

    def _field_by_key(self, key: str) -> dict | None:
        return next((f for f in self._fields if str(f.get("field_key", "")) == key), None)

    def _render_core_fields(self) -> None:
        self._clear_children(self.core_container)
        for idx, key in enumerate(self._core_field_keys()):
            field = self._field_by_key(key)
            if not field:
                continue
            row = Frame(self.core_container)
            row.grid(row=idx, column=0, sticky="ew", padx=6, pady=3)
            row.grid_columnconfigure(0, weight=1)
            meta = self._kind_label(str(field.get("field_kind", "text")))
            if bool(field.get("required", False)):
                meta += " | obligatoire"
            Label(row, text=f"{field.get('label', key)}\n{meta}", anchor="w", justify="left").grid(row=0, column=0, sticky="ew")
            ttk.Button(row, text="\u270E Modifier", width=11, command=lambda k=key: self._edit_field(k, core=True), style="Dialog.TButton").grid(row=0, column=1, padx=(4, 0))

    def _render_custom_fields(self) -> None:
        self._clear_children(self.custom_container)
        custom_fields = [
            f
            for f in self._fields
            if str(f.get("field_key", "")) not in {"name", "description", "type", "ip", "action_double_click"}
        ]
        if not custom_fields:
            Label(self.custom_container, text="Aucun champ personnalise. Cliquez sur + Ajouter un champ.").grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        for idx, field in enumerate(custom_fields):
            key = str(field.get("field_key", ""))
            row = Frame(self.custom_container)
            row.grid(row=idx, column=0, sticky="ew", padx=6, pady=3)
            row.grid_columnconfigure(0, weight=1)
            meta = self._kind_label(str(field.get("field_kind", "text")))
            options = str(field.get("options", "")).strip()
            if options and str(field.get("field_kind", "")).strip().lower() == "choice":
                meta += f" | {options}"
            if bool(field.get("required", False)):
                meta += " | obligatoire"
            Label(row, text=f"{field.get('label', key)}\n{meta}", anchor="w", justify="left").grid(row=0, column=0, sticky="ew")
            ttk.Button(row, text="↑", width=3, command=lambda k=key: self._move_field_by_key(k, -1), style="Dialog.TButton").grid(row=0, column=1, padx=2)
            ttk.Button(row, text="↓", width=3, command=lambda k=key: self._move_field_by_key(k, 1), style="Dialog.TButton").grid(row=0, column=2, padx=2)
            ttk.Button(row, text="\u270E Modifier", width=11, command=lambda k=key: self._edit_field(k, core=False), style="Dialog.TButton").grid(row=0, column=3, padx=2)
            ttk.Button(row, text="Supprimer", width=10, command=lambda k=key: self._delete_custom_field(k), style="Dialog.TButton").grid(row=0, column=4, padx=(2, 0))

    def _render_actions(self) -> None:
        self._clear_children(self.actions_container)
        if not self._actions:
            Label(self.actions_container, text="Aucune action contextuelle.").grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        for idx, action in enumerate(self._actions):
            key = str(action.get("action_key", ""))
            row = Frame(self.actions_container)
            row.grid(row=idx, column=0, sticky="ew", padx=6, pady=3)
            row.grid_columnconfigure(0, weight=1)
            meta = f"{action.get('target_kind', 'builtin')} -> {action.get('target_value', '')}"
            if bool(action.get("is_default", False)):
                meta += " | action par defaut"
            Label(row, text=f"{action.get('label', key)} ({key})\n{meta}", anchor="w", justify="left").grid(row=0, column=0, sticky="ew")
            ttk.Button(row, text="↑", width=3, command=lambda i=idx: self._move_action(i, -1), style="Dialog.TButton").grid(row=0, column=1, padx=2)
            ttk.Button(row, text="↓", width=3, command=lambda i=idx: self._move_action(i, 1), style="Dialog.TButton").grid(row=0, column=2, padx=2)
            ttk.Button(row, text="\u270E Modifier", width=11, command=lambda k=key: self._edit_action(k), style="Dialog.TButton").grid(row=0, column=3, padx=2)
            ttk.Button(row, text="Par defaut", width=10, command=lambda k=key: self._set_default_action(k), style="Dialog.TButton").grid(row=0, column=4, padx=2)
            ttk.Button(row, text="Supprimer", width=10, command=lambda k=key: self._delete_action(k), style="Dialog.TButton").grid(row=0, column=5, padx=(2, 0))

    def _render_preview(self) -> None:
        self._clear_children(self.preview_form)
        row = 0
        label_type = self.var_type_label.get().strip() if self._create_mode else self._type_label
        Label(self.preview_form, text="Type de device :").grid(row=row, column=0, sticky="e", padx=4, pady=4)
        combo = ttk.Combobox(self.preview_form, values=[label_type or "(Nouveau type)"], state="disabled")
        combo.set(label_type or "(Nouveau type)")
        combo.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        row += 1

        for field in self._fields:
            key = str(field.get("field_key", ""))
            label = str(field.get("label", key)).strip() or key
            kind = str(field.get("field_kind", "text")).strip().lower()
            if bool(field.get("required", False)):
                label = f"{label} *"
            Label(self.preview_form, text=f"{label} :").grid(row=row, column=0, sticky="e", padx=4, pady=4)
            if kind == "choice":
                opts = [v.strip() for v in str(field.get("options", "")).split(",") if v.strip()]
                w = ttk.Combobox(self.preview_form, values=opts, state="disabled")
                default_val = str(field.get("default_value", "")).strip()
                if default_val and default_val in opts:
                    w.set(default_val)
                elif opts:
                    w.set(opts[0])
            else:
                w = ttk.Entry(self.preview_form)
                default_val = str(field.get("default_value", ""))
                if default_val:
                    w.insert(0, default_val)
                w.configure(state="disabled")
            w.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            row += 1

        ttk.Checkbutton(self.preview_form, text="Recevoir une alerte sur changement de statut").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(8, 4)
        )

    def _next_custom_key(self) -> str:
        base = "custom_field_"
        idx = 1
        keys = {str(f.get("field_key", "")) for f in self._fields}
        while f"{base}{idx}" in keys:
            idx += 1
        return f"{base}{idx}"

    def _add_custom_field(self) -> None:
        dlg = FieldEditorDialog(self, title="Ajouter un champ")
        if dlg.result is None:
            return
        self._fields.append({"field_key": self._next_custom_key(), **dlg.result})
        self._reindex_sorts()
        self._render_all()

    def _edit_field(self, key: str, *, core: bool) -> None:
        if key == "action_double_click":
            return
        idx = next((i for i, f in enumerate(self._fields) if str(f.get("field_key", "")) == key), None)
        if idx is None:
            return
        current = self._fields[int(idx)]
        dlg = FieldEditorDialog(self, initial=current, title="Modifier champ")
        if dlg.result is None:
            return
        updated = {**current, **dlg.result}
        if core and key == "name":
            updated["required"] = True
        if core and key == "type":
            updated["field_kind"] = "choice"
            updated["required"] = True
            updated["options"] = self.CORE_FIELDS["type"]["options"]
            if str(updated.get("default_value", "")).strip() not in {"Windows", "Linux", "Firmware", "Autre"}:
                updated["default_value"] = "Windows"
        if core and key == "ip" and self._monitoring_enabled:
            updated["required"] = True
        self._fields[int(idx)] = updated
        self._reindex_sorts()
        self._render_all()

    def _delete_custom_field(self, key: str) -> None:
        if key == "action_double_click":
            return
        self._fields = [f for f in self._fields if str(f.get("field_key", "")) != key]
        self._reindex_sorts()
        self._render_all()

    def _move_field_by_key(self, key: str, delta: int) -> None:
        if key == "action_double_click":
            return
        idx = next((i for i, f in enumerate(self._fields) if str(f.get("field_key", "")) == key), None)
        if idx is None:
            return
        target = int(idx) + int(delta)
        if target < 0 or target >= len(self._fields):
            return
        target_key = str(self._fields[target].get("field_key", ""))
        if target_key in {"name", "description", "type", "ip", "action_double_click"}:
            return
        self._fields[int(idx)], self._fields[target] = self._fields[target], self._fields[int(idx)]
        self._reindex_sorts()
        self._render_all()

    def _add_action(self) -> None:
        dlg = ActionEditorDialog(self)
        if dlg.result is None:
            return
        key = str(dlg.result.get("action_key", ""))
        if any(str(a.get("action_key", "")) == key for a in self._actions):
            messagebox.showerror("Action", f"Action '{key}' deja existante.", parent=self)
            return
        if bool(dlg.result.get("is_default", False)):
            for action in self._actions:
                action["is_default"] = False
        dlg.result["os_scope"] = format_os_scope([self._selected_catalog_os()])
        self._actions.append(dlg.result)
        self._reindex_sorts()
        self._render_all()

    def _edit_action(self, key: str) -> None:
        idx = next((i for i, a in enumerate(self._actions) if str(a.get("action_key", "")) == key), None)
        if idx is None:
            return
        current = self._actions[int(idx)]
        dlg = ActionEditorDialog(self, initial=current)
        if dlg.result is None:
            return
        new_key = str(dlg.result.get("action_key", ""))
        if new_key != key and any(str(a.get("action_key", "")) == new_key for a in self._actions):
            messagebox.showerror("Action", f"Action '{new_key}' deja existante.", parent=self)
            return
        if bool(dlg.result.get("is_default", False)):
            for action in self._actions:
                action["is_default"] = False
        merged = {**current, **dlg.result}
        merged["os_scope"] = str(current.get("os_scope", ""))
        self._actions[int(idx)] = merged
        self._reindex_sorts()
        self._render_all()

    def _delete_action(self, key: str) -> None:
        self._actions = [a for a in self._actions if str(a.get("action_key", "")) != key]
        self._reindex_sorts()
        self._render_all()

    def _move_action(self, idx: int, delta: int) -> None:
        target = idx + delta
        if target < 0 or target >= len(self._actions):
            return
        self._actions[idx], self._actions[target] = self._actions[target], self._actions[idx]
        self._reindex_sorts()
        self._render_all()

    def _set_default_action(self, key: str) -> None:
        for action in self._actions:
            action["is_default"] = str(action.get("action_key", "")) == key
        self._render_all()

    def _ensure_field(
        self,
        field_key: str,
        *,
        label: str,
        field_kind: str = "text",
        required: bool = False,
        options: str = "",
        default_value: str = "",
    ) -> None:
        idx = next((i for i, f in enumerate(self._fields) if str(f.get("field_key", "")) == field_key), None)
        payload = {
            "field_key": field_key,
            "label": label,
            "field_kind": field_kind,
            "required": required,
            "options": options,
            "default_value": default_value,
        }
        if idx is None:
            self._fields.append(payload)
        else:
            self._fields[int(idx)] = {**self._fields[int(idx)], **payload}

    def _ensure_action(
        self,
        action_key: str,
        *,
        label: str,
        target_kind: str,
        target_value: str,
        is_default: bool = False,
        include_selected_os: bool = False,
    ) -> None:
        idx = next((i for i, a in enumerate(self._actions) if str(a.get("action_key", "")) == action_key), None)
        scope_values = set(parse_os_scope(""))
        if include_selected_os:
            scope_values.add(self._selected_catalog_os())
        payload = {
            "action_key": action_key,
            "label": label,
            "target_kind": target_kind,
            "target_value": target_value,
            "is_default": is_default,
            "os_scope": format_os_scope(scope_values) if include_selected_os else "",
        }
        if idx is None:
            self._actions.append(payload)
        else:
            current = dict(self._actions[int(idx)])
            if include_selected_os:
                merged_scope = parse_os_scope(str(current.get("os_scope", "")))
                merged_scope.add(self._selected_catalog_os())
                payload["os_scope"] = format_os_scope(merged_scope)
            self._actions[int(idx)] = {**current, **payload}
        if is_default:
            self._set_default_action(action_key)

    def _ensure_action_double_click_field(self) -> None:
        idx = next(
            (i for i, f in enumerate(self._fields) if str(f.get("field_key", "")).strip() == "action_double_click"),
            None,
        )
        keys = [str(a.get("action_key", "")).strip().lower() for a in self._actions if str(a.get("action_key", "")).strip()]
        options = ",".join(keys)
        previous_default = ""
        if idx is not None:
            previous_default = str(self._fields[int(idx)].get("default_value", "")).strip().lower()
        default_value = previous_default if previous_default in keys else (keys[0] if keys else "")
        payload = {
            "field_key": "action_double_click",
            "label": "Action double-clic",
            "field_kind": "choice",
            "required": False,
            "options": options,
            "default_value": default_value,
        }
        if idx is None:
            self._fields.append(payload)
        else:
            self._fields[int(idx)] = {**self._fields[int(idx)], **payload}

    def _set_double_click_action(self, action_key: str) -> None:
        key = str(action_key or "").strip().lower()
        if not key:
            return
        self._ensure_action_double_click_field()
        idx = next(
            (i for i, f in enumerate(self._fields) if str(f.get("field_key", "")).strip() == "action_double_click"),
            None,
        )
        if idx is None:
            return
        current = self._fields[int(idx)]
        self._fields[int(idx)] = {**current, "default_value": key}

    def _double_click_action_key(self) -> str:
        field = next(
            (f for f in self._fields if str(f.get("field_key", "")).strip() == "action_double_click"),
            None,
        )
        if not field:
            return ""
        current = str(field.get("default_value", "")).strip().lower()
        if current:
            return current
        options = [v.strip().lower() for v in str(field.get("options", "")).split(",") if v.strip()]
        return options[0] if options else ""

    def _apply_block_to_menu(self, block_key: str) -> None:
        if block_key == "ssh":
            self._ensure_field("ssh_user", label="Login SSH", field_kind="text", required=False)
            self._ensure_action("ssh", label="Ouvrir SSH", target_kind="builtin", target_value="ssh", include_selected_os=True)
        elif block_key == "teamviewer":
            self._ensure_field("id_Teamviewer", label="ID TeamViewer", field_kind="text", required=False)
            self._ensure_action("teamviewer", label="Ouvrir TeamViewer", target_kind="builtin", target_value="teamviewer", include_selected_os=True)
        elif block_key == "remote_desktop":
            self._ensure_action(
                "remote_desktop",
                label="Ouvrir Remote Desktop",
                target_kind="builtin",
                target_value="remote_desktop",
                include_selected_os=True,
            )
        elif block_key == "web":
            self._ensure_field("web_url", label="URL interface web", field_kind="url", required=False)
            self._ensure_action("web", label="Ouvrir Web", target_kind="builtin", target_value="web", include_selected_os=True)
        self._reindex_sorts()
        self._render_all()

    def _apply_block_to_double_click(self, block_key: str) -> None:
        self._apply_block_to_menu(block_key)
        action_key = {
            "ssh": "ssh",
            "teamviewer": "teamviewer",
            "remote_desktop": "remote_desktop",
            "web": "web",
        }.get(str(block_key).strip().lower(), "")
        self._ensure_action_double_click_field()
        if action_key:
            self._set_double_click_action(action_key)
        self._reindex_sorts()
        self._render_all()

    def _add_block_ssh(self) -> None:
        self._apply_block_to_menu("ssh")

    def _add_block_teamviewer(self) -> None:
        self._apply_block_to_menu("teamviewer")

    def _add_block_rdp(self) -> None:
        self._apply_block_to_menu("remote_desktop")

    def _add_block_web(self) -> None:
        self._apply_block_to_menu("web")

    def _save_schema(self) -> None:
        self._ensure_core_fields()
        self._reindex_sorts()

        if self._create_mode:
            label = self.var_type_label.get().strip()
            if not label:
                messagebox.showerror("Formulaire", "Le nom du type est obligatoire.", parent=self)
                return
            self._type_label = label
            self._monitoring_enabled = bool(self.var_monitoring_enabled.get())
            generated_code = self._generate_unique_type_code(label)
            try:
                self._type_code = self._mgr.save_device_type(
                    code=generated_code,
                    label=label,
                    monitoring_enabled=self._monitoring_enabled,
                )
            except ValueError as exc:
                messagebox.showerror("Formulaire", str(exc), parent=self)
                return
            except Exception as exc:
                messagebox.showerror("Formulaire", f"Impossible de creer le type: {exc}", parent=self)
                return

        try:
            self._mgr.replace_type_schema(type_code=self._type_code, fields=self._fields, actions=self._actions)
        except ValueError as exc:
            messagebox.showerror("Formulaire", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Formulaire", f"Impossible d'enregistrer le formulaire: {exc}", parent=self)
            return

        if callable(self._on_saved):
            self._on_saved(self._type_code)
        messagebox.showinfo("Formulaire", "Formulaire enregistre.", parent=self)
        self.ok()

