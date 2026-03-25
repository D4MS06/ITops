from __future__ import annotations

import tkinter as tk
from tkinter import BOTH, LEFT, RIGHT, X, Button, Frame, Label, Toplevel, messagebox, ttk

from monitoring.config.settings import load_settings
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import bind_control_button_hover
from monitoring.ui.utils.searchable_sortable_tree import SearchableSortableTreeMixin
from monitoring.ui.utils.window_chrome import apply_window_chrome_theme


class StatusLogsViewer(SearchableSortableTreeMixin, Toplevel):
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
        self.var_search = tk.StringVar(value="")
        self._rows: list[dict] = []
        self._device_index: dict[tuple[str, str], dict] = {}
        self.theme = resolve_theme(str(getattr(load_settings(), "ui_theme", "light") or "light"))
        self._build_ui()
        self._apply_window_chrome_theme(self.theme.key == "dark")
        self.after(120, lambda: self._apply_window_chrome_theme(self.theme.key == "dark"))
        self.refresh_logs()

    def _apply_window_chrome_theme(self, dark: bool) -> None:
        apply_window_chrome_theme(self, dark=bool(dark))

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
        search_group = Frame(top, bg=c["app_bg"])
        search_group.pack(side=LEFT, padx=(14, 0))
        Label(search_group, text="Recherche:", bg=c["app_bg"], fg=c["text_primary"]).pack(side=LEFT, padx=(0, 6))
        self.entry_search = tk.Entry(
            search_group,
            textvariable=self.var_search,
            width=26,
            relief="solid",
            bd=1,
            bg=c["panel_bg"],
            fg=c["text_primary"],
            insertbackground=c["text_primary"],
            highlightthickness=1,
            highlightbackground=c["placeholder_border"],
            highlightcolor=c["nav_active_bg"],
        )
        self.entry_search.pack(side=LEFT)
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
            columns=("date", "dtype", "event", "device", "ip", "transition", "details"),
            show="headings",
            style=style_name,
        )
        self._init_searchable_sortable_tree(
            tree=self.tree,
            search_var=self.var_search,
            on_query_changed=self._render_rows,
            search_container=search_group,
            default_sort_col="date",
            default_sort_reverse=True,
        )
        self.tree.heading("date", text="Date")
        self.tree.heading("dtype", text="Type")
        self.tree.heading("event", text="Evenement")
        self.tree.heading("device", text="Device")
        self.tree.heading("ip", text="IP")
        self.tree.heading("transition", text="Transition")
        self.tree.heading("details", text="Details")

        self.tree.column("date", width=180, minwidth=160, anchor="w", stretch=False)
        self.tree.column("dtype", width=90, minwidth=80, anchor="w", stretch=False)
        self.tree.column("event", width=170, minwidth=150, anchor="w", stretch=False)
        self.tree.column("device", width=260, minwidth=180, anchor="w", stretch=True)
        self.tree.column("ip", width=150, minwidth=120, anchor="w", stretch=False)
        self.tree.column("transition", width=220, minwidth=180, anchor="w", stretch=False)
        self.tree.column("details", width=300, minwidth=220, anchor="w", stretch=True)

        up_bg = "#e9f8ee" if self.theme.key != "dark" else "#1d3a2a"
        down_bg = "#fdecec" if self.theme.key != "dark" else "#3f2020"
        stale_bg = "#f3f4f6" if self.theme.key != "dark" else "#2a2f36"
        self.tree.tag_configure("status-up", background=up_bg)
        self.tree.tag_configure("status-down", background=down_bg)
        self.tree.tag_configure("stale-device", background=stale_bg)

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

        self._rows = self._mgr.list_status_logs(
            limit=limit,
            dtype=self.dtype,
            device_id=self.device_id,
        )
        self._device_index = self._build_device_index()
        self._render_rows()

    def _build_device_index(self) -> dict[tuple[str, str], dict]:
        index: dict[tuple[str, str], dict] = {}
        try:
            devices = self._mgr.read_devices_map()
        except Exception:
            return index
        for dtype, rows in dict(devices or {}).items():
            for item in list(rows or []):
                raw_id = str(item.get("id", "")).strip()
                if not raw_id:
                    continue
                index[(str(dtype or "").strip(), raw_id)] = item
        return index

    @staticmethod
    def _status_label(value: str) -> str:
        key = str(value or "").strip().lower()
        if key == "online":
            return "En ligne"
        if key == "offline":
            return "Hors ligne"
        if key == "idle":
            return "Inactif"
        return str(value or "")

    def _resolve_device_display(self, row: dict) -> tuple[str, str, bool]:
        dtype = str(row.get("dtype", "")).strip()
        device_id = str(row.get("device_id", "")).strip()
        live = self._device_index.get((dtype, device_id))
        if live:
            name = str(live.get("name", "")).strip() or str(row.get("device_name", "")).strip() or device_id
            ip = str(live.get("ip", "")).strip()
            return name, ip, False
        name = str(row.get("device_name", "")).strip() or device_id or "Equipement inconnu"
        return f"{name} (supprime)", "", True

    def _transition_display(self, row: dict) -> tuple[str, str]:
        old_key = str(row.get("old_status", "")).strip().lower()
        new_key = str(row.get("new_status", "")).strip().lower()
        text = f"{self._status_label(old_key)} -> {self._status_label(new_key)}"
        if old_key == "offline" and new_key == "online":
            return f"↑ {text}", "status-up"
        if old_key == "online" and new_key == "offline":
            return f"↓ {text}", "status-down"
        return text, ""

    def _render_rows(self) -> None:
        def row_value(row: dict, col: str) -> str:
            if col == "date":
                return str(row.get("created_at", "")).lower()
            if col == "dtype":
                return str(row.get("dtype", "")).lower()
            if col == "event":
                return str(row.get("event_kind", "")).lower()
            if col == "device":
                return str(self._resolve_device_display(row)[0]).lower()
            if col == "ip":
                return str(self._resolve_device_display(row)[1]).lower()
            if col == "transition":
                return str(self._transition_display(row)[0]).lower()
            return str(row.get("details", "")).lower()

        rows = self._apply_filter_sort(
            self._rows,
            searchable_text=lambda row: " ".join(
                [
                    str(row.get("created_at", "")),
                    str(row.get("dtype", "")),
                    str(row.get("event_kind", "")),
                    str(row.get("device_name", "")),
                    str(row.get("device_id", "")),
                    str(row.get("old_status", "")),
                    str(row.get("new_status", "")),
                    str(row.get("ip", "")),
                    str(row.get("details", "")),
                ]
            ),
            sort_value=lambda row, col: row_value(row, str(col or "")),
        )

        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for idx, row in enumerate(rows):
            dev_label, ip_label, stale = self._resolve_device_display(row)
            transition, transition_tag = self._transition_display(row)
            tags = []
            if transition_tag:
                tags.append(transition_tag)
            if stale:
                tags.append("stale-device")
            self.tree.insert(
                "",
                "end",
                iid=f"log-{idx}",
                values=(
                    row["created_at"],
                    row["dtype"],
                    row.get("event_kind", "status_change"),
                    dev_label,
                    ip_label or "-",
                    transition,
                    row.get("details", ""),
                ),
                tags=tuple(tags),
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
