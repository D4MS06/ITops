from __future__ import annotations

import ctypes
import os
import tkinter as tk
from tkinter import ttk
from tkinter.simpledialog import Dialog

from monitoring.config.settings import load_settings
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import bind_control_button_hover


class ThemedDialog(Dialog):
    """Dialog base with centralized, reusable theming helpers."""

    def __init__(self, parent, title: str | None = None) -> None:
        self.theme = resolve_theme(str(getattr(load_settings(), "ui_theme", "light") or "light"))
        self._dialog_combo_style = "Dialog.TCombobox"
        self._dialog_frame_style = "Dialog.TFrame"
        self._dialog_label_style = "Dialog.TLabel"
        self._dialog_check_style = "Dialog.TCheckbutton"
        self._dialog_entry_style = "Dialog.TEntry"
        self._dialog_labelframe_style = "Dialog.TLabelframe"
        self._dialog_labelframe_label_style = "Dialog.TLabelframe.Label"
        super().__init__(parent, title=title)
        # Final pass once all widgets are realized by Tk.
        try:
            self.after_idle(self._safe_apply_theme)
            self.after(90, self._safe_apply_theme)
        except Exception:
            pass

    def _safe_apply_theme(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self.apply_theme(self)

    def apply_theme(self, root: tk.Misc | None = None) -> None:
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        c = self.theme.colors
        root_widget = root or self
        try:
            self.configure(bg=c["app_bg"])
            self._apply_window_chrome_theme(self.theme.key == "dark")
            # Re-apply shortly after show to stabilize native titlebar color.
            self.after(60, self._safe_apply_window_chrome_theme)
            self.after(180, self._safe_apply_window_chrome_theme)
        except Exception:
            pass
        self._configure_ttk_styles()
        self._apply_theme_recursive(root_widget)

    def _safe_apply_window_chrome_theme(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._apply_window_chrome_theme(self.theme.key == "dark")

    def style_button(self, button: tk.Widget) -> None:
        bind_control_button_hover(button, self.theme.colors)

    def _configure_ttk_styles(self) -> None:
        c = self.theme.colors
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            self._dialog_frame_style,
            background=c["app_bg"],
        )
        style.configure(
            self._dialog_label_style,
            background=c["app_bg"],
            foreground=c["text_primary"],
        )
        style.configure(
            self._dialog_check_style,
            background=c["app_bg"],
            foreground=c["text_primary"],
        )
        style.map(
            self._dialog_check_style,
            background=[("active", c["app_bg"]), ("!active", c["app_bg"])],
            foreground=[("active", c["text_primary"]), ("!active", c["text_primary"])],
        )
        style.configure(
            self._dialog_entry_style,
            fieldbackground=c["panel_bg"],
            background=c["panel_bg"],
            foreground=c["text_primary"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
        )
        style.map(
            self._dialog_entry_style,
            fieldbackground=[("!disabled", c["panel_bg"])],
            foreground=[("!disabled", c["text_primary"])],
        )
        style.configure(
            self._dialog_labelframe_style,
            background=c["app_bg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
        )
        style.configure(
            self._dialog_labelframe_label_style,
            background=c["app_bg"],
            foreground=c["text_primary"],
        )
        style.configure(
            self._dialog_combo_style,
            fieldbackground=c["panel_bg"],
            background=c["panel_bg"],
            foreground=c["text_primary"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            arrowcolor=c["text_primary"],
        )
        style.map(
            self._dialog_combo_style,
            fieldbackground=[("readonly", c["panel_bg"])],
            foreground=[("readonly", c["text_primary"])],
            selectbackground=[("readonly", c["panel_bg"])],
            selectforeground=[("readonly", c["text_primary"])],
        )

    def _apply_theme_recursive(self, widget: tk.Misc) -> None:
        try:
            if not widget.winfo_exists():
                return
        except Exception:
            return
        c = self.theme.colors
        if getattr(widget, "_theme_skip", False):
            return
        try:
            if isinstance(widget, tk.Frame):
                widget.configure(bg=c["app_bg"])
            elif isinstance(widget, tk.LabelFrame):
                widget.configure(bg=c["app_bg"], fg=c["text_primary"])
            elif isinstance(widget, tk.Label):
                widget.configure(bg=c["app_bg"], fg=c["text_primary"])
            elif isinstance(widget, tk.Entry):
                widget.configure(
                    bg=c["panel_bg"],
                    fg=c["text_primary"],
                    insertbackground=c["text_primary"],
                    relief="solid",
                    bd=1,
                    highlightthickness=1,
                    highlightbackground=c["placeholder_border"],
                    highlightcolor=c["nav_active_bg"],
                )
            elif isinstance(widget, tk.Checkbutton):
                widget.configure(
                    bg=c["app_bg"],
                    fg=c["text_primary"],
                    activebackground=c["app_bg"],
                    activeforeground=c["text_primary"],
                    selectcolor=c["panel_bg"],
                )
            elif isinstance(widget, tk.Listbox):
                widget.configure(
                    bg=c["tree_bg"],
                    fg=c["tree_fg"],
                    selectbackground=c["tree_select_bg"],
                    selectforeground=c["text_primary"],
                    highlightthickness=1,
                    highlightbackground=c["placeholder_border"],
                )
            elif isinstance(widget, tk.Scale):
                widget.configure(
                    bg=c["app_bg"],
                    fg=c["text_primary"],
                    activebackground=c["control_hover_bg"],
                    troughcolor=c["panel_bg"],
                    highlightthickness=0,
                )
            elif isinstance(widget, ttk.Combobox):
                widget.configure(style=self._dialog_combo_style)
            elif isinstance(widget, ttk.Frame):
                widget.configure(style=self._dialog_frame_style)
            elif isinstance(widget, ttk.Label):
                widget.configure(style=self._dialog_label_style)
            elif isinstance(widget, ttk.Checkbutton):
                widget.configure(style=self._dialog_check_style)
            elif isinstance(widget, ttk.Entry):
                widget.configure(style=self._dialog_entry_style)
            elif isinstance(widget, ttk.LabelFrame):
                widget.configure(style=self._dialog_labelframe_style)
        except Exception:
            pass

        try:
            children = widget.winfo_children()
        except Exception:
            return
        for child in children:
            self._apply_theme_recursive(child)

    def _apply_window_chrome_theme(self, dark: bool) -> None:
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
