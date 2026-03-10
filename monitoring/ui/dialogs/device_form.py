from __future__ import annotations

import ipaddress
import logging
from tkinter import BooleanVar, Entry, Frame, Label, StringVar, messagebox, ttk
from typing import Any

from monitoring.ui.dialogs.themed_dialog import ThemedDialog
from monitoring.services.device_form_service import DeviceFormService
from monitoring.ui.utils.action_compat import PLATFORM_OPTIONS, action_allows_os, normalize_platform

LOGGER = logging.getLogger(__name__)


class DeviceForm(ThemedDialog):
    """Dynamic modal form based on configured device types."""

    ACTION_LABELS = {
        "ssh": "SSH",
        "web": "Web (URL)",
        "teamviewer": "TeamViewer",
        "remote_desktop": "Remote Desktop",
    }

    def __init__(
        self,
        parent,
        *,
        title: str,
        default_type: str | None = None,
        initial: dict[str, Any] | None = None,
    ) -> None:
        self.initial = initial or {}
        self.result: dict[str, Any] | None = None
        self.device_type = str(default_type or self.initial.get("kind", "")).strip().lower()
        self._form_service = DeviceFormService()
        self._types = self._form_service.types
        self._fields_by_type = self._form_service.fields_by_type
        self._actions_by_type = self._form_service.actions_by_type
        self._label_by_code = {str(t["code"]): str(t.get("label", t["code"])) for t in self._types}
        self._code_by_label = {label: code for code, label in self._label_by_code.items()}
        super().__init__(parent, title=title)

    def body(self, master) -> Frame:
        master.grid_columnconfigure(0, weight=0, minsize=180)
        master.grid_columnconfigure(1, weight=1)

        default_code = self.device_type if self.device_type in self._label_by_code else ""
        if not default_code:
            default_code = str(self._types[0].get("code", "switch"))

        self.var_kind = StringVar(value=self._label_by_code.get(default_code, default_code))
        self.var_name = StringVar(value=self.initial.get("name", ""))
        self.var_ip = StringVar(value=self.initial.get("ip", ""))
        self.var_desc = StringVar(value=self.initial.get("desc", ""))
        self.var_type = StringVar(value=self.initial.get("subtype", ""))
        self.var_tv = StringVar(value=self.initial.get("tv_id", ""))
        self.var_action = StringVar(value="")
        self.var_web_url = StringVar(value=self.initial.get("web_url", ""))
        self.var_ssh_user = StringVar(value=self.initial.get("ssh_user", ""))
        self.var_custom: dict[str, StringVar] = {}
        self.var_notify = BooleanVar(value=self.initial.get("notify", True))

        Label(master, text="Type de device :").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        self.combo_kind = ttk.Combobox(
            master,
            textvariable=self.var_kind,
            values=list(self._code_by_label.keys()),
            state="disabled" if self.initial else "readonly",
        )
        self.combo_kind.grid(row=0, column=1, padx=5, sticky="ew")
        if not self.initial:
            self.combo_kind.bind("<<ComboboxSelected>>", self._on_type_change)

        row = 1
        if self._has_field("name"):
            Label(master, text=f"{self._field_label('name', 'Nom')} :").grid(row=row, column=0, sticky="e", padx=5, pady=4)
            Entry(master, textvariable=self.var_name).grid(row=row, column=1, padx=5, sticky="ew")
            row += 1

        if self._has_field("ip"):
            Label(master, text=f"{self._field_label('ip', 'IP')} :").grid(row=row, column=0, sticky="e", padx=5, pady=4)
            Entry(master, textvariable=self.var_ip).grid(row=row, column=1, padx=5, sticky="ew")
            row += 1

        if self._has_field("description"):
            Label(master, text=f"{self._field_label('description', 'Description')} :").grid(
                row=row, column=0, sticky="e", padx=5, pady=4
            )
            Entry(master, textvariable=self.var_desc).grid(row=row, column=1, padx=5, sticky="ew")
            row += 1

        self.advanced_frame = Frame(master)
        self.advanced_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.advanced_frame.grid_columnconfigure(0, weight=0, minsize=180)
        self.advanced_frame.grid_columnconfigure(1, weight=1)
        self._ensure_action_value(initial=True)
        self._render_advanced_fields()
        row += 1

        self.custom_frame = Frame(master)
        self.custom_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.custom_frame.grid_columnconfigure(0, weight=0, minsize=180)
        self.custom_frame.grid_columnconfigure(1, weight=1)
        self._render_custom_fields()
        row += 1

        self.chk_notify = ttk.Checkbutton(
            master,
            text="Recevoir une alerte sur changement de statut",
            variable=self.var_notify,
        )
        self.chk_notify.grid(row=row, column=0, columnspan=2, pady=(8, 4))

        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        ttk.Button(box, text="OK", command=self.ok, style="Dialog.TButton").pack(side="left", padx=5, pady=6)
        ttk.Button(box, text="Annuler", command=self.cancel, style="Dialog.TButton").pack(side="left", padx=5, pady=6)
        box.pack()

    def _selected_type_code(self) -> str:
        return str(self._code_by_label.get(self.var_kind.get().strip(), "")).strip().lower()

    def _current_fields(self) -> list[dict]:
        return list(self._fields_by_type.get(self._selected_type_code(), []))

    def _field_label(self, field_key: str, fallback: str) -> str:
        for field in self._current_fields():
            if str(field.get("field_key", "")) == field_key:
                return str(field.get("label", fallback) or fallback)
        return fallback

    def _field_required(self, field_key: str) -> bool:
        for field in self._current_fields():
            if str(field.get("field_key", "")) == field_key:
                return bool(field.get("required", False))
        return False

    def _known_field_keys(self) -> set[str]:
        return {
            "name",
            "ip",
            "description",
            "type",
            "id_Teamviewer",
            "action_double_click",
            "web_url",
            "ssh_user",
        }

    def _custom_fields(self) -> list[dict]:
        return [f for f in self._current_fields() if str(f.get("field_key", "")) not in self._known_field_keys()]

    def _custom_var_for_field(self, field: dict) -> StringVar:
        key = str(field.get("field_key", "")).strip()
        if key not in self.var_custom:
            initial_custom = self.initial.get("custom_data", {}) if isinstance(self.initial.get("custom_data", {}), dict) else {}
            default_value = str(field.get("default_value", "") or "")
            initial_value = str(initial_custom.get(key, default_value) or "")
            self.var_custom[key] = StringVar(value=initial_value)
        return self.var_custom[key]

    def _has_field(self, field_key: str) -> bool:
        return any(str(f.get("field_key", "")) == field_key for f in self._current_fields())

    def _field_options(self, field_key: str) -> list[str]:
        for field in self._current_fields():
            if str(field.get("field_key", "")) != field_key:
                continue
            raw = str(field.get("options", "") or "")
            return [part.strip() for part in raw.split(",") if part.strip()]
        return []

    def _type_template(self) -> str:
        code = self._selected_type_code()
        for t in self._types:
            if str(t.get("code", "")).strip().lower() == code:
                icon = str(t.get("icon", "")).strip().lower()
                return icon if icon in {"switch", "server"} else "switch"
        return "switch"

    def _action_options(self) -> list[str]:
        code = self._selected_type_code()
        return self._form_service.action_options(type_code=code, platform_label=self.var_type.get())

    def _action_label(self, action_key: str) -> str:
        key = str(action_key or "").strip().lower()
        return self.ACTION_LABELS.get(key, key.replace("_", " ").title())

    def _current_action_key(self) -> str:
        value = self.var_action.get().strip()
        if not value:
            return ""
        for key in self._action_options():
            if value == self._action_label(key):
                return key
        return value.lower()

    def _default_action(self) -> str:
        actions = self._actions_by_type.get(self._selected_type_code(), [])
        platform = normalize_platform(self.var_type.get())
        for action in actions:
            action_key = str(action.get("action_key", "")).strip().lower()
            if not action_allows_os(str(action.get("os_scope", "")), platform):
                continue
            if bool(action.get("is_default", False)):
                return action_key
        options = self._action_options()
        return options[0] if options else ""

    def _fallback_url(self) -> str:
        ip = self.var_ip.get().strip()
        if not ip:
            return ""
        return f"http://{ip}"

    def _ensure_action_value(self, *, initial: bool = False) -> None:
        action_keys = self._action_options()
        if not action_keys:
            self.var_action.set("")
            return

        current_action = str(self.initial.get("action_double_click", "")).strip().lower() if initial else self._current_action_key()
        if current_action not in action_keys:
            current_action = self._default_action()
        self.var_action.set(self._action_label(current_action))

    def _render_advanced_fields(self) -> None:
        for widget in self.advanced_frame.winfo_children():
            widget.destroy()

        row = 0
        if self._has_field("type"):
            options = self._field_options("type") or list(PLATFORM_OPTIONS)
            current_platform = self.var_type.get().strip()
            if current_platform not in options:
                self.var_type.set(options[0])
            Label(self.advanced_frame, text="OS :").grid(row=row, column=0, sticky="e", padx=5, pady=4)
            os_combo = ttk.Combobox(
                self.advanced_frame,
                textvariable=self.var_type,
                values=options,
                state="readonly",
            )
            os_combo.grid(row=row, column=1, padx=5, sticky="ew")
            os_combo.bind("<<ComboboxSelected>>", self._on_os_change)
            row += 1

        action_keys = self._action_options()
        teamviewer_available = "teamviewer" in action_keys and self._has_field("id_Teamviewer")
        if action_keys:
            action_labels = [self._action_label(key) for key in action_keys]
            Label(self.advanced_frame, text="Action double-clic :").grid(row=row, column=0, sticky="e", padx=5, pady=4)
            action_combo = ttk.Combobox(
                self.advanced_frame,
                textvariable=self.var_action,
                values=action_labels,
                state="readonly",
            )
            action_combo.grid(row=row, column=1, padx=5, sticky="ew")
            action_combo.bind("<<ComboboxSelected>>", self._on_action_change)
            row += 1

        if teamviewer_available:
            Label(self.advanced_frame, text="ID TeamViewer :").grid(row=row, column=0, sticky="e", padx=5, pady=4)
            Entry(self.advanced_frame, textvariable=self.var_tv).grid(row=row, column=1, padx=5, sticky="ew")
            row += 1

        current_action = self._current_action_key()
        if current_action == "web" and self._has_field("web_url"):
            if not self.var_web_url.get().strip():
                self.var_web_url.set(self._fallback_url())
            Label(self.advanced_frame, text="URL interface web :").grid(row=row, column=0, sticky="e", padx=5, pady=4)
            Entry(self.advanced_frame, textvariable=self.var_web_url).grid(row=row, column=1, padx=5, sticky="ew")
            row += 1

        if current_action == "ssh" and self._has_field("ssh_user"):
            Label(self.advanced_frame, text="SSH user (optionnel) :").grid(row=row, column=0, sticky="e", padx=5, pady=4)
            Entry(self.advanced_frame, textvariable=self.var_ssh_user).grid(row=row, column=1, padx=5, sticky="ew")

    def _render_custom_fields(self) -> None:
        for widget in self.custom_frame.winfo_children():
            widget.destroy()

        fields = self._custom_fields()
        if not fields:
            return

        row = 0
        for field in fields:
            key = str(field.get("field_key", "")).strip()
            label = str(field.get("label", key) or key)
            kind = str(field.get("field_kind", "text") or "text").strip().lower()
            options = [part.strip() for part in str(field.get("options", "") or "").split(",") if part.strip()]
            var = self._custom_var_for_field(field)

            Label(self.custom_frame, text=f"{label} :").grid(row=row, column=0, sticky="e", padx=5, pady=4)
            if kind == "choice":
                cb = ttk.Combobox(
                    self.custom_frame,
                    textvariable=var,
                    values=options,
                    state="readonly" if options else "normal",
                )
                cb.grid(row=row, column=1, padx=5, sticky="ew")
            else:
                Entry(self.custom_frame, textvariable=var).grid(row=row, column=1, padx=5, sticky="ew")
            row += 1

    def _on_type_change(self, _evt=None) -> None:
        if self._has_field("type"):
            options = self._field_options("type") or list(PLATFORM_OPTIONS)
            if self.var_type.get().strip() not in options:
                self.var_type.set(options[0])
        self._ensure_action_value(initial=False)
        self._render_advanced_fields()
        self._render_custom_fields()
        self.apply_theme(self)

    def _on_os_change(self, _evt=None) -> None:
        self._ensure_action_value(initial=False)
        self._render_advanced_fields()
        self.apply_theme(self)

    def _on_action_change(self, _evt=None) -> None:
        self._render_advanced_fields()
        self.apply_theme(self)

    def validate(self) -> bool:
        kind = self._selected_type_code()
        if not kind:
            messagebox.showerror("Type requis", "Veuillez selectionner le type de device.")
            return False

        if self._has_field("name") and self._field_required("name") and not self.var_name.get().strip():
            messagebox.showerror("Champ manquant", "Le nom est obligatoire.")
            return False

        if self._has_field("ip"):
            raw_ip = self.var_ip.get().strip()
            if raw_ip:
                try:
                    ipaddress.ip_address(raw_ip)
                except ValueError:
                    messagebox.showerror("IP invalide", "Adresse IP non valide.")
                    return False

        action = self._current_action_key()
        action_options = self._action_options()
        if action and action not in action_options:
            messagebox.showerror("Action invalide", "Veuillez selectionner une action valide.")
            return False

        if action == "teamviewer" and self._has_field("id_Teamviewer") and not self.var_tv.get().strip():
            messagebox.showerror("Champ manquant", "L'ID TeamViewer est obligatoire pour cette action.")
            return False

        if action == "web" and self._has_field("web_url") and not self.var_web_url.get().strip():
            self.var_web_url.set(self._fallback_url())

        for field in self._current_fields():
            if not bool(field.get("required", False)):
                continue
            key = str(field.get("field_key", "")).strip()
            value = ""
            if key == "name":
                value = self.var_name.get().strip()
            elif key == "ip":
                value = self.var_ip.get().strip()
            elif key == "description":
                value = self.var_desc.get().strip()
            elif key == "type":
                value = self.var_type.get().strip()
            elif key == "id_Teamviewer":
                value = self.var_tv.get().strip()
            elif key == "web_url":
                value = self.var_web_url.get().strip()
            elif key == "ssh_user":
                value = self.var_ssh_user.get().strip()
            elif key == "action_double_click":
                value = action
            else:
                custom_var = self.var_custom.get(key)
                value = custom_var.get().strip() if custom_var is not None else ""
            if not value:
                messagebox.showerror("Champ manquant", f"Le champ '{field.get('label', key)}' est obligatoire.")
                return False

        return True

    def apply(self) -> None:
        kind = self._selected_type_code()
        self.result = {
            "kind": kind,
            "name": self.var_name.get().strip(),
            "ip": self.var_ip.get().strip(),
            "desc": self.var_desc.get().strip(),
            "notify": bool(self.var_notify.get()),
        }

        if self._has_field("type"):
            self.result["subtype"] = self.var_type.get().strip()
        if self._has_field("id_Teamviewer"):
            self.result["tv_id"] = self.var_tv.get().strip()
        if self._action_options():
            self.result["action_double_click"] = self._current_action_key()
        if self._has_field("web_url"):
            self.result["web_url"] = self.var_web_url.get().strip()
        if self._has_field("ssh_user"):
            self.result["ssh_user"] = self.var_ssh_user.get().strip()

        custom_data: dict[str, str] = {}
        for field in self._custom_fields():
            key = str(field.get("field_key", "")).strip()
            if not key:
                continue
            custom_var = self.var_custom.get(key)
            custom_data[key] = custom_var.get().strip() if custom_var is not None else ""
        self.result["custom_data"] = custom_data
