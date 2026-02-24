from __future__ import annotations

import tkinter as tk
from tkinter import BOTH, LEFT, RIGHT, X, Button, Frame, Label, Toplevel, messagebox, ttk

from monitoring.storage.sqlite_manager import SQLiteFileManager


class StatusLogsViewer(Toplevel):
    def __init__(
        self,
        parent,
        *,
        title: str = "Journal des changements de statut",
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("980x520")
        self.dtype = dtype
        self.device_id = device_id
        self._mgr = SQLiteFileManager()
        self.var_limit = tk.StringVar(value="300")
        self._build_ui()
        self.refresh_logs()

    def _build_ui(self) -> None:
        top = Frame(self)
        top.pack(fill=X, padx=8, pady=8)

        Label(top, text="Lignes:").pack(side=LEFT, padx=(0, 6))
        ttk.Entry(top, textvariable=self.var_limit, width=8).pack(side=LEFT)
        Button(top, text="Rafraichir", command=self.refresh_logs).pack(side=LEFT, padx=8)
        Button(top, text="Effacer cette vue", command=self.clear_current_scope).pack(side=LEFT, padx=8)
        Button(top, text="Effacer tout", command=self.clear_all_logs).pack(side=LEFT, padx=8)
        Button(top, text="Fermer", command=self.destroy).pack(side=RIGHT)

        self.tree = ttk.Treeview(
            self,
            columns=("date", "type", "device", "old", "new"),
            show="headings",
        )
        self.tree.heading("date", text="Date")
        self.tree.heading("type", text="Type")
        self.tree.heading("device", text="Device")
        self.tree.heading("old", text="Ancien statut")
        self.tree.heading("new", text="Nouveau statut")

        self.tree.column("date", width=180, minwidth=160, anchor="w", stretch=False)
        self.tree.column("type", width=90, minwidth=80, anchor="w", stretch=False)
        self.tree.column("device", width=420, minwidth=240, anchor="w", stretch=True)
        self.tree.column("old", width=130, minwidth=120, anchor="w", stretch=False)
        self.tree.column("new", width=130, minwidth=120, anchor="w", stretch=False)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        vsb.pack(side=RIGHT, fill="y", padx=(0, 8), pady=(0, 8))

    def refresh_logs(self) -> None:
        try:
            limit = max(1, int(self.var_limit.get().strip() or "300"))
        except Exception:
            limit = 300
            self.var_limit.set("300")

        logs = self._mgr.list_status_logs(
            limit=limit,
            dtype=self.dtype,
            device_id=self.device_id,
        )

        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for idx, row in enumerate(logs):
            dev_label = f'{row["device_name"]} [{row["device_id"]}]'
            self.tree.insert(
                "",
                "end",
                iid=f"log-{idx}",
                values=(
                    row["created_at"],
                    row["dtype"],
                    dev_label,
                    row["old_status"],
                    row["new_status"],
                ),
            )

    def clear_current_scope(self) -> None:
        if not messagebox.askyesno(
            "Confirmation",
            "Supprimer les logs affiches dans cette vue ?",
            parent=self,
        ):
            return
        deleted = self._mgr.delete_status_logs(dtype=self.dtype, device_id=self.device_id)
        self.refresh_logs()
        messagebox.showinfo("Logs", f"{deleted} log(s) supprime(s).", parent=self)

    def clear_all_logs(self) -> None:
        if not messagebox.askyesno(
            "Confirmation",
            "Supprimer tous les logs de statut ?",
            parent=self,
        ):
            return
        deleted = self._mgr.delete_status_logs()
        self.refresh_logs()
        messagebox.showinfo("Logs", f"{deleted} log(s) supprime(s).", parent=self)
