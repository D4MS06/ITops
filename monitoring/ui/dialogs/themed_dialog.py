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
        self._dialog_button_style = "Dialog.TButton"
        self._dialog_tree_style = "Dialog.Treeview"
        self._dialog_tree_heading_style = "Dialog.Treeview.Heading"
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
            "TCheckbutton",
            background=c["app_bg"],
            foreground=c["text_primary"],
        )
        style.map(
            "TCheckbutton",
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
            "TEntry",
            fieldbackground=c["panel_bg"],
            background=c["panel_bg"],
            foreground=c["text_primary"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
        )
        style.map(
            "TEntry",
            fieldbackground=[
                ("disabled", c["surface_bg"]),
                ("readonly", c["panel_bg"]),
                ("!disabled", c["panel_bg"]),
            ],
            foreground=[
                ("disabled", c["text_muted"]),
                ("readonly", c["text_primary"]),
                ("!disabled", c["text_primary"]),
            ],
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
            "TLabelframe",
            background=c["app_bg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
        )
        style.configure(
            "TLabelframe.Label",
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
        # Fallback styles for widgets that don't explicitly set a custom style.
        style.configure(
            "TCombobox",
            fieldbackground=c["panel_bg"],
            background=c["panel_bg"],
            foreground=c["text_primary"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            arrowcolor=c["text_primary"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", c["panel_bg"])],
            foreground=[("readonly", c["text_primary"])],
            selectbackground=[("readonly", c["panel_bg"])],
            selectforeground=[("readonly", c["text_primary"])],
        )
        style.configure(
            self._dialog_button_style,
            background=c["button_inactive_bg"],
            foreground=c["button_inactive_fg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            padding=(8, 4),
        )
        style.map(
            self._dialog_button_style,
            background=[
                ("disabled", c["panel_bg"]),
                ("pressed", c.get("control_hover_bg", c["panel_hover_bg"])),
                ("active", c.get("control_hover_bg", c["panel_hover_bg"])),
                ("!disabled", c["button_inactive_bg"]),
            ],
            foreground=[
                ("disabled", c["text_muted"]),
                ("pressed", c.get("control_hover_fg", c["text_primary"])),
                ("active", c.get("control_hover_fg", c["text_primary"])),
                ("!disabled", c["button_inactive_fg"]),
            ],
        )
        style.configure(
            "TButton",
            background=c["button_inactive_bg"],
            foreground=c["button_inactive_fg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            padding=(8, 4),
        )
        style.map(
            "TButton",
            background=[
                ("disabled", c["panel_bg"]),
                ("pressed", c.get("control_hover_bg", c["panel_hover_bg"])),
                ("active", c.get("control_hover_bg", c["panel_hover_bg"])),
                ("!disabled", c["button_inactive_bg"]),
            ],
            foreground=[
                ("disabled", c["text_muted"]),
                ("pressed", c.get("control_hover_fg", c["text_primary"])),
                ("active", c.get("control_hover_fg", c["text_primary"])),
                ("!disabled", c["button_inactive_fg"]),
            ],
        )
        style.configure(
            self._dialog_tree_style,
            background=c["tree_bg"],
            fieldbackground=c["tree_bg"],
            foreground=c["tree_fg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            rowheight=24,
        )
        style.map(
            self._dialog_tree_style,
            background=[("selected", c["tree_select_bg"])],
            foreground=[("selected", c["text_primary"])],
        )
        style.configure(
            self._dialog_tree_heading_style,
            background=c["surface_bg"],
            foreground=c["text_primary"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
        )
        style.map(
            self._dialog_tree_heading_style,
            background=[("active", c.get("control_hover_bg", c["panel_hover_bg"]))],
            foreground=[("active", c.get("control_hover_fg", c["text_primary"]))],
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
                self._patch_combobox_popdown(widget)
            elif isinstance(widget, ttk.Frame):
                widget.configure(style=self._dialog_frame_style)
            elif isinstance(widget, ttk.Label):
                widget.configure(style=self._dialog_label_style)
            elif isinstance(widget, ttk.Checkbutton):
                widget.configure(style=self._dialog_check_style)
            elif isinstance(widget, ttk.Entry):
                widget.configure(style=self._dialog_entry_style)
            elif isinstance(widget, ttk.Button):
                widget.configure(style=self._dialog_button_style)
            elif isinstance(widget, ttk.Treeview):
                widget.configure(style=self._dialog_tree_style)
                # Headings use a distinct style name in ttk.
                try:
                    widget.heading("#0", style=self._dialog_tree_heading_style)
                except Exception:
                    pass
                for col in widget.cget("columns") or ():
                    try:
                        widget.heading(col, style=self._dialog_tree_heading_style)
                    except Exception:
                        continue
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

        # Combobox popup list colors are controlled by option database, not ttk style.
        try:
            self.option_add("*TCombobox*Listbox.background", c["panel_bg"])
            self.option_add("*TCombobox*Listbox.foreground", c["text_primary"])
            self.option_add("*TCombobox*Listbox.selectBackground", c["tree_select_bg"])
            self.option_add("*TCombobox*Listbox.selectForeground", c["text_primary"])
            self.option_add("*TCombobox*Listbox.font", "Segoe UI 9")
        except Exception:
            pass

    def _patch_combobox_popdown(self, combo: ttk.Combobox) -> None:
        """Force popup Listbox colors on Windows/Tk where ttk style is ignored."""
        c = self.theme.colors
        try:
            popdown = combo.tk.call("ttk::combobox::PopdownWindow", str(combo))
            listbox = f"{popdown}.f.l"
            combo.tk.call(
                listbox,
                "configure",
                "-background",
                c["panel_bg"],
                "-foreground",
                c["text_primary"],
                "-selectbackground",
                c["tree_select_bg"],
                "-selectforeground",
                c["text_primary"],
            )
        except Exception:
            pass

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
