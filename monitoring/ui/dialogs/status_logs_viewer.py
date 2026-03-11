from __future__ import annotations

import ctypes
import os
import tkinter as tk
from tkinter import BOTH, LEFT, RIGHT, X, Button, Frame, Label, Toplevel, messagebox, ttk

from monitoring.config.settings import load_settings
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import bind_control_button_hover


class StatusLogsViewer(Toplevel):
    def __init__(
        self,
        parent,
        *,
        title: str = "Journal des changements de statut",
        dtype: str | None = None,
        device_id: str | None = None,
        manager: SQLiteFileManager | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("980x520")
        self.dtype = dtype
        self.device_id = device_id
        self._mgr = manager or SQLiteFileManager()
        self.var_limit = tk.StringVar(value="300")
        self.theme = resolve_theme(str(getattr(load_settings(), "ui_theme", "light") or "light"))
        self._build_ui()
        self._apply_window_chrome_theme(self.theme.key == "dark")
        self.after(120, lambda: self._apply_window_chrome_theme(self.theme.key == "dark"))
        self.refresh_logs()

    def _apply_window_chrome_theme(self, dark: bool) -> None:
        """Apply native Windows title bar dark/light appearance when supported."""
        if os.name != "nt":
            return
        try:
            self.update_idletasks()
            hwnd = self.winfo_id()
            try:
                parent = ctypes.windll.user32.GetParent(hwnd)  # type: ignore[attr-defined]
                if parent:
                    hwnd = parent
            except Exception:
                pass
            value = ctypes.c_int(1 if dark else 0)
            size = ctypes.sizeof(value)
            for attr in (20, 19):
                try:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(  # type: ignore[attr-defined]
                        hwnd,
                        attr,
                        ctypes.byref(value),
                        size,
                    )
                except Exception:
                    continue
            try:
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_NOZORDER = 0x0004
                SWP_FRAMECHANGED = 0x0020
                ctypes.windll.user32.SetWindowPos(  # type: ignore[attr-defined]
                    hwnd,
                    0,
                    0,
                    0,
                    0,
                    0,
                    SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED,
                )
            except Exception:
                pass
        except Exception:
            pass

    def _build_ui(self) -> None:
        c = self.theme.colors
        self.configure(bg=c["app_bg"])

        top = Frame(self, bg=c["app_bg"])
        top.pack(fill=X, padx=8, pady=8)

        Label(top, text="Lignes:", bg=c["app_bg"], fg=c["text_primary"]).pack(side=LEFT, padx=(0, 6))
        self.entry_limit = tk.Entry(
            top,
            textvariable=self.var_limit,
            width=8,
            relief="solid",
            bd=1,
            bg=c["panel_bg"],
            fg=c["text_primary"],
            insertbackground=c["text_primary"],
            highlightthickness=1,
            highlightbackground=c["placeholder_border"],
            highlightcolor=c["nav_active_bg"],
        )
        self.entry_limit.pack(side=LEFT)
        btn_refresh = Button(
            top,
            text="Rafraichir",
            command=self.refresh_logs,
        )
        btn_refresh.pack(side=LEFT, padx=8)

        btn_clear_scope = Button(
            top,
            text="Effacer cette vue",
            command=self.clear_current_scope,
        )
        btn_clear_scope.pack(side=LEFT, padx=8)

        btn_clear_all = Button(
            top,
            text="Effacer tout",
            command=self.clear_all_logs,
        )
        btn_clear_all.pack(side=LEFT, padx=8)

        btn_close = Button(
            top,
            text="Fermer",
            command=self.destroy,
        )
        btn_close.pack(side=RIGHT)

        for btn in (btn_refresh, btn_clear_scope, btn_clear_all, btn_close):
            bind_control_button_hover(btn, c)

        style = ttk.Style()
        style_name = "Logs.Treeview"
        heading_style = "Logs.Treeview.Heading"
        style.configure(
            style_name,
            background=c["tree_bg"],
            fieldbackground=c["tree_bg"],
            foreground=c["tree_fg"],
            borderwidth=0,
            relief="flat",
        )
        style.configure(
            heading_style,
            background=c["panel_bg"],
            foreground=c["tree_heading_fg"],
            borderwidth=1,
            relief="flat",
        )
        style.map(style_name, background=[("selected", c["tree_select_bg"])])
        style.map(
            heading_style,
            background=[("active", c["panel_hover_bg"]), ("!active", c["panel_bg"])],
            foreground=[("!disabled", c["tree_heading_fg"])],
        )

        self.tree = ttk.Treeview(
            self,
            columns=("date", "dtype", "event", "device", "old", "new", "details"),
            show="headings",
            style=style_name,
        )
        self.tree.heading("date", text="Date")
        self.tree.heading("dtype", text="Type")
        self.tree.heading("event", text="Evenement")
        self.tree.heading("device", text="Device")
        self.tree.heading("old", text="Ancien statut")
        self.tree.heading("new", text="Nouveau statut")
        self.tree.heading("details", text="Details")

        self.tree.column("date", width=180, minwidth=160, anchor="w", stretch=False)
        self.tree.column("dtype", width=90, minwidth=80, anchor="w", stretch=False)
        self.tree.column("event", width=170, minwidth=150, anchor="w", stretch=False)
        self.tree.column("device", width=320, minwidth=220, anchor="w", stretch=True)
        self.tree.column("old", width=130, minwidth=120, anchor="w", stretch=False)
        self.tree.column("new", width=130, minwidth=120, anchor="w", stretch=False)
        self.tree.column("details", width=320, minwidth=220, anchor="w", stretch=True)

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
                    row.get("event_kind", "status_change"),
                    dev_label,
                    row["old_status"],
                    row["new_status"],
                    row.get("details", ""),
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
