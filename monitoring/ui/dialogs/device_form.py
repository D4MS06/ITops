from __future__ import annotations

import ipaddress
import logging
from tkinter import BooleanVar, Entry, Frame, Label, StringVar, messagebox, ttk
from tkinter.simpledialog import Dialog
from typing import Any

LOGGER = logging.getLogger(__name__)


class DeviceForm(Dialog):
    """Formulaire modal pour Switch / Serveur avec options avancées."""

    LABELS = {"switch": "Switch", "server": "Serveur"}
    REVERSE = {v: k for k, v in LABELS.items()}

    ACTION_LABELS = {
        "ssh": "SSH",
        "web": "Web (URL)",
        "teamviewer": "TeamViewer",
        "remote_desktop": "Remote Desktop",
    }
    REVERSE_ACTION_LABELS = {v: k for k, v in ACTION_LABELS.items()}

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
        self.device_type = default_type
        super().__init__(parent, title)

    def body(self, master) -> Frame:
        self.var_kind = StringVar()
        self.var_name = StringVar(value=self.initial.get("name", ""))
        self.var_ip = StringVar(value=self.initial.get("ip", ""))
        self.var_desc = StringVar(value=self.initial.get("desc", ""))
        self.var_type = StringVar(value=self.initial.get("subtype", ""))

        self.var_tv = StringVar(value=self.initial.get("tv_id", ""))
        self.var_action = StringVar(value="")
        self.var_web_url = StringVar(value=self.initial.get("web_url", ""))
        self.var_ssh_user = StringVar(value=self.initial.get("ssh_user", ""))

        self._set_initial_action()

        self.var_notify = BooleanVar(value=self.initial.get("notify", True))

        if self.device_type in self.LABELS:
            kind_label = self.LABELS[self.device_type]
        elif self.initial.get("subtype") or self.initial.get("tv_id"):
            kind_label = self.LABELS["server"]
            self.device_type = "server"
        else:
            kind_label = self.LABELS["switch"]
            self.device_type = "switch"
        self.var_kind.set(kind_label)

        Label(master, text="Type d'appareil :").grid(
            row=0, column=0, sticky="e", padx=5, pady=4
        )
        self.combo_kind = ttk.Combobox(
            master,
            textvariable=self.var_kind,
            values=list(self.LABELS.values()),
            width=27,
            state="disabled" if self.initial else "readonly",
        )
        self.combo_kind.grid(row=0, column=1, padx=5, sticky="w")
        if not self.initial:
            self.combo_kind.bind("<<ComboboxSelected>>", self._on_type_change)

        Label(master, text="Nom :").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_name, width=30).grid(row=1, column=1, padx=5)

        Label(master, text="IP :").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        Entry(master, textvariable=self.var_ip, width=30).grid(row=2, column=1, padx=5)

        Label(master, text="Description :").grid(
            row=3, column=0, sticky="e", padx=5, pady=4
        )
        Entry(master, textvariable=self.var_desc, width=30).grid(row=3, column=1, padx=5)

        self.advanced_frame = Frame(master)
        self.advanced_frame.grid(row=4, column=0, columnspan=2, sticky="ew")
        self._render_advanced_fields()

        self.chk_notify = ttk.Checkbutton(
            master,
            text="Recevoir une alerte sur changement de statut",
            variable=self.var_notify,
        )
        self.chk_notify.grid(row=5, column=0, columnspan=2, pady=(8, 4))

        return master

    def _normalize_subtype(self) -> str:
        return self.var_type.get().strip().lower()

    def _action_options(self, subtype: str) -> list[str]:
        if subtype == "linux":
            return ["ssh", "web"]
        if subtype == "windows":
            return ["teamviewer", "remote_desktop"]
        return ["web"]

    def _default_action(self, subtype: str) -> str:
        if subtype == "windows":
            return "teamviewer" if self.var_tv.get().strip() else "remote_desktop"
        if subtype == "linux":
            return "ssh"
        return "web"

    def _fallback_url(self, subtype: str) -> str:
        ip = self.var_ip.get().strip()
        if not ip:
            return ""
        if subtype == "dsm":
            return f"http://{ip}:5000"
        return f"http://{ip}"

    def _current_action_key(self) -> str:
        raw = self.var_action.get().strip()
        return self.REVERSE_ACTION_LABELS.get(raw, raw.lower())

    def _set_initial_action(self) -> None:
        subtype = str(self.initial.get("subtype", "")).strip().lower()
        options = self._action_options(subtype)
        initial_action = str(self.initial.get("action_double_click", "")).strip().lower()
        if initial_action not in options:
            initial_action = self._default_action(subtype)
        self.var_action.set(self.ACTION_LABELS.get(initial_action, ""))

    def _render_advanced_fields(self) -> None:
        for widget in self.advanced_frame.winfo_children():
            widget.destroy()

        if self.var_kind.get() != self.LABELS["server"]:
            return

        Label(self.advanced_frame, text="Type OS :").grid(
            row=0, column=0, sticky="e", padx=5, pady=4
        )
        os_combo = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.var_type,
            values=["Windows", "DSM", "Linux", "Autre"],
            width=27,
            state="readonly",
        )
        os_combo.grid(row=0, column=1, padx=5)
        os_combo.bind("<<ComboboxSelected>>", self._on_os_change)

        subtype = self._normalize_subtype()
        action_keys = self._action_options(subtype)

        current_action = self._current_action_key()
        if current_action not in action_keys:
            current_action = self._default_action(subtype)
            self.var_action.set(self.ACTION_LABELS[current_action])

        action_labels = [self.ACTION_LABELS[key] for key in action_keys]
        Label(self.advanced_frame, text="Action double-clic :").grid(
            row=1, column=0, sticky="e", padx=5, pady=4
        )
        action_combo = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.var_action,
            values=action_labels,
            width=27,
            state="readonly",
        )
        action_combo.grid(row=1, column=1, padx=5)
        action_combo.bind("<<ComboboxSelected>>", self._on_action_change)

        row = 2
        if current_action == "teamviewer":
            Label(self.advanced_frame, text="ID TeamViewer :").grid(
                row=row, column=0, sticky="e", padx=5, pady=4
            )
            Entry(self.advanced_frame, textvariable=self.var_tv, width=30).grid(
                row=row, column=1, padx=5
            )
            self.var_web_url.set("")
            self.var_ssh_user.set("")
            return

        if current_action == "web":
            if not self.var_web_url.get().strip():
                self.var_web_url.set(self._fallback_url(subtype))
            Label(self.advanced_frame, text="URL interface web :").grid(
                row=row, column=0, sticky="e", padx=5, pady=4
            )
            Entry(self.advanced_frame, textvariable=self.var_web_url, width=30).grid(
                row=row, column=1, padx=5
            )
            self.var_ssh_user.set("")
            return

        if current_action == "ssh":
            Label(self.advanced_frame, text="SSH user :").grid(
                row=row, column=0, sticky="e", padx=5, pady=4
            )
            Entry(self.advanced_frame, textvariable=self.var_ssh_user, width=30).grid(
                row=row, column=1, padx=5
            )
            self.var_web_url.set("")
            self.var_tv.set("")
            return

        if current_action == "remote_desktop":
            self.var_web_url.set("")
            self.var_ssh_user.set("")
            self.var_tv.set("")

    def _on_type_change(self, _evt=None) -> None:
        self._render_advanced_fields()

    def _on_os_change(self, _evt=None) -> None:
        subtype = self._normalize_subtype()
        self.var_action.set(self.ACTION_LABELS[self._default_action(subtype)])
        self._render_advanced_fields()

    def _on_action_change(self, _evt=None) -> None:
        self._render_advanced_fields()

    def validate(self) -> bool:
        kind = self.REVERSE.get(self.var_kind.get())
        if kind not in {"switch", "server"}:
            messagebox.showerror("Type requis", "Veuillez sélectionner le type d'appareil.")
            return False

        if not self.var_name.get().strip():
            messagebox.showerror("Champ manquant", "Le nom est obligatoire.")
            return False

        try:
            ipaddress.ip_address(self.var_ip.get().strip())
        except ValueError:
            messagebox.showerror("IP invalide", "Adresse IP non valide.")
            return False

        if kind == "server":
            subtype = self._normalize_subtype()
            action = self._current_action_key()
            allowed = self._action_options(subtype)
            if action not in allowed:
                messagebox.showerror(
                    "Action invalide",
                    "Veuillez sélectionner une action valide pour ce type d'OS.",
                )
                return False

            if action == "teamviewer" and not self.var_tv.get().strip():
                messagebox.showerror("Champ manquant", "L'ID TeamViewer est obligatoire.")
                return False

            if subtype == "linux" and action == "web" and not self.var_web_url.get().strip():
                messagebox.showerror(
                    "Champ manquant",
                    "L'URL interface web est obligatoire pour Linux en mode Web.",
                )
                return False
            if action == "ssh" and not self.var_ssh_user.get().strip():
                messagebox.showerror(
                    "Champ manquant",
                    "Le SSH user est obligatoire pour l'action SSH.",
                )
                return False

        return True

    def apply(self) -> None:
        kind = self.REVERSE[self.var_kind.get()]
        self.result = {
            "kind": kind,
            "name": self.var_name.get().strip(),
            "ip": self.var_ip.get().strip(),
            "desc": self.var_desc.get().strip(),
            "notify": bool(self.var_notify.get()),
        }

        if kind == "server":
            subtype = self.var_type.get().strip()
            action = self._current_action_key()

            tv_id = self.var_tv.get().strip() if action == "teamviewer" else ""
            web_url = self.var_web_url.get().strip() if action == "web" else ""
            ssh_user = self.var_ssh_user.get().strip() if action == "ssh" else ""

            self.result["subtype"] = subtype
            self.result["tv_id"] = tv_id
            self.result["action_double_click"] = action
            self.result["web_url"] = web_url
            self.result["ssh_user"] = ssh_user
