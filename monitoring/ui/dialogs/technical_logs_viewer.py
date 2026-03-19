from __future__ import annotations

import os
import tkinter as tk
from collections import deque
from tkinter import BOTH, LEFT, RIGHT, X, Button, Checkbutton, Frame, Label, Toplevel, ttk

from monitoring.config.settings import load_settings
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import bind_control_button_hover
from monitoring.utils.logger import get_log_file_path


class TechnicalLogsViewer(Toplevel):
    def __init__(self, parent, *, title: str = "Logs techniques") -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("1080x620")
        self.minsize(760, 420)
        self.theme = resolve_theme(str(getattr(load_settings(), "ui_theme", "light") or "light"))
        self.var_limit = tk.StringVar(value="500")
        self.var_filter = tk.StringVar(value="")
        self.var_level = tk.StringVar(value="Tous")
        self.var_monitoring_only = tk.BooleanVar(value=False)
        self._log_file_path = get_log_file_path()
        self._build_ui()
        self.refresh_logs()

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
        self.entry_limit.pack(side=LEFT, padx=(0, 12))

        Label(top, text="Filtre:", bg=c["app_bg"], fg=c["text_primary"]).pack(side=LEFT, padx=(0, 6))
        self.entry_filter = tk.Entry(
            top,
            textvariable=self.var_filter,
            width=36,
            relief="solid",
            bd=1,
            bg=c["panel_bg"],
            fg=c["text_primary"],
            insertbackground=c["text_primary"],
            highlightthickness=1,
            highlightbackground=c["placeholder_border"],
            highlightcolor=c["nav_active_bg"],
        )
        self.entry_filter.pack(side=LEFT, padx=(0, 12))
        self.entry_filter.bind("<Return>", lambda _e=None: self.refresh_logs(), add="+")

        Label(top, text="Niveau:", bg=c["app_bg"], fg=c["text_primary"]).pack(side=LEFT, padx=(0, 6))
        self.level_combo = ttk.Combobox(
            top,
            textvariable=self.var_level,
            values=("Tous", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
            state="readonly",
            width=10,
        )
        self.level_combo.pack(side=LEFT, padx=(0, 12))
        self.level_combo.bind("<<ComboboxSelected>>", lambda _e=None: self.refresh_logs(), add="+")

        self.monitoring_only_check = Checkbutton(
            top,
            text="Monitoring uniquement",
            variable=self.var_monitoring_only,
            command=self.refresh_logs,
            bg=c["app_bg"],
            fg=c["text_primary"],
            activebackground=c["app_bg"],
            activeforeground=c["text_primary"],
            selectcolor=c["panel_bg"],
        )
        self.monitoring_only_check.pack(side=LEFT, padx=(0, 12))

        btn_refresh = Button(top, text="Rafraichir", command=self.refresh_logs)
        btn_refresh.pack(side=LEFT, padx=(0, 8))

        btn_open = Button(top, text="Ouvrir le fichier", command=self._open_log_file)
        btn_open.pack(side=LEFT, padx=(0, 8))

        btn_close = Button(top, text="Fermer", command=self.destroy)
        btn_close.pack(side=RIGHT)

        for btn in (btn_refresh, btn_open, btn_close):
            bind_control_button_hover(btn, c)

        info = Frame(self, bg=c["app_bg"])
        info.pack(fill=X, padx=8, pady=(0, 6))
        self.info_label = Label(info, text="", anchor="w", bg=c["app_bg"], fg=c["text_secondary"])
        self.info_label.pack(fill=X)

        text_frame = Frame(self, bg=c["app_bg"])
        text_frame.pack(fill=BOTH, expand=True, padx=8, pady=(0, 8))

        self.text = tk.Text(
            text_frame,
            wrap="none",
            bg=c["tree_bg"],
            fg=c["tree_fg"],
            insertbackground=c["text_primary"],
            selectbackground=c["tree_select_bg"],
            selectforeground=c["text_primary"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=c["placeholder_border"],
            highlightcolor=c["nav_active_bg"],
        )
        self.text.pack(side=LEFT, fill=BOTH, expand=True)
        self.text.configure(state="disabled")

        yscroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        yscroll.pack(side=RIGHT, fill="y")
        self.text.configure(yscrollcommand=yscroll.set)

    def _line_limit(self) -> int:
        try:
            return max(50, int(self.var_limit.get().strip() or "500"))
        except (TypeError, ValueError):
            self.var_limit.set("500")
            return 500

    def refresh_logs(self) -> None:
        path = self._log_file_path
        if not os.path.isfile(path):
            self._set_text("Aucun fichier de log disponible pour le moment.")
            self.info_label.configure(text=path)
            return

        lines = self._read_tail_lines(path, self._line_limit())
        lines = self._filter_lines(
            lines,
            text_filter=str(self.var_filter.get() or "").strip(),
            level_filter=str(self.var_level.get() or "Tous").strip().upper(),
            monitoring_only=bool(self.var_monitoring_only.get()),
        )

        content = "".join(lines).strip()
        self._set_text(content or "Aucune ligne ne correspond au filtre courant.")
        self.info_label.configure(text=path)

    def _set_text(self, content: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")

    @staticmethod
    def _read_tail_lines(path: str, limit: int) -> list[str]:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return list(deque(handle, maxlen=max(1, int(limit))))

    @staticmethod
    def _filter_lines(
        lines: list[str],
        *,
        text_filter: str,
        level_filter: str,
        monitoring_only: bool,
    ) -> list[str]:
        needle = str(text_filter or "").strip().lower()
        normalized_level = str(level_filter or "TOUS").strip().upper()
        filtered = list(lines)
        if normalized_level and normalized_level != "TOUS":
            filtered = [line for line in filtered if f" - {normalized_level} - " in line]
        if monitoring_only:
            filtered = [
                line
                for line in filtered
                if "monitoring.services.monitoring_service" in line
                or "monitoring.services.monitoring_runtime_service" in line
                or "monitoring.utils.logger" in line and "Monitoring " in line
            ]
        if needle:
            filtered = [line for line in filtered if needle in line.lower()]
        return filtered

    def _open_log_file(self) -> None:
        try:
            os.startfile(self._log_file_path)  # type: ignore[attr-defined]
        except Exception:
            self.refresh_logs()
