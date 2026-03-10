from __future__ import annotations

from dataclasses import dataclass
from tkinter import ACTIVE, Entry, Frame, Label, StringVar

from monitoring.ui.dialogs.themed_dialog import ThemedDialog


@dataclass
class ConfigDropConfirmResult:
    detail: str = ""


class ConfigDropConfirmDialog(ThemedDialog):
    def __init__(
        self,
        parent,
        *,
        device_label: str,
        source_name: str,
        target_name: str,
        source_date_label: str,
    ) -> None:
        self.device_label = str(device_label or "").strip()
        self.source_name = str(source_name or "").strip()
        self.target_name = str(target_name or "").strip()
        self.source_date_label = str(source_date_label or "").strip()
        self.var_detail = StringVar(value="")
        self.result: ConfigDropConfirmResult | None = None
        super().__init__(parent, title="Importer fichier de configuration")

    def body(self, master) -> Frame:
        master.grid_columnconfigure(1, weight=1)
        Label(master, text="Device:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        Label(master, text=self.device_label, anchor="w").grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        Label(master, text="Fichier source:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        Label(master, text=self.source_name, anchor="w").grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        Label(master, text="Nom cible:").grid(row=2, column=0, sticky="e", padx=6, pady=4)
        Label(master, text=self.target_name, anchor="w").grid(row=2, column=1, sticky="ew", padx=6, pady=4)
        Label(master, text="Date fichier:").grid(row=3, column=0, sticky="e", padx=6, pady=4)
        Label(master, text=self.source_date_label, anchor="w").grid(row=3, column=1, sticky="ew", padx=6, pady=4)
        Label(master, text="Detail (optionnel):").grid(row=4, column=0, sticky="e", padx=6, pady=4)
        Entry(master, textvariable=self.var_detail).grid(row=4, column=1, sticky="ew", padx=6, pady=4)
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        from tkinter import Button  # local import to match existing dialogs

        btn_ok = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        btn_ok.pack(side="left", padx=5, pady=6)
        btn_cancel = Button(box, text="Annuler", width=10, command=self.cancel)
        btn_cancel.pack(side="left", padx=5, pady=6)
        self.style_button(btn_ok)
        self.style_button(btn_cancel)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def apply(self) -> None:
        self.result = ConfigDropConfirmResult(detail=str(self.var_detail.get() or "").strip())
