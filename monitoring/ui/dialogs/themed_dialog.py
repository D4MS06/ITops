from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from tkinter.simpledialog import Dialog

from monitoring.config.settings import load_settings
from monitoring.ui.style_system import resolve_ui_style_tokens
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import apply_control_button_style, bind_control_button_hover
from monitoring.ui.utils.window_chrome import apply_window_chrome_theme

LOGGER = logging.getLogger(__name__)


class ThemedDialog(Dialog):
    """Dialog base with centralized, reusable theming helpers."""

    def __init__(self, parent, title: str | None = None) -> None:
        self.theme = resolve_theme(str(getattr(load_settings(), "ui_theme", "light") or "light"))
        self.ui_tokens = resolve_ui_style_tokens(self.theme.key)
        self._dialog_combo_style = "Dialog.TCombobox"
        self._dialog_frame_style = "Dialog.TFrame"
        self._dialog_label_style = "Dialog.TLabel"
        self._dialog_check_style = "Dialog.TCheckbutton"
        self._dialog_entry_style = "Dialog.TEntry"
        self._dialog_button_style = "Dialog.TButton"
        self._dialog_scrollbar_style = "Dialog.Vertical.TScrollbar"
        self._dialog_hscrollbar_style = "Dialog.Horizontal.TScrollbar"
        self._dialog_tree_style = "Dialog.Treeview"
        self._dialog_tree_heading_style = "Dialog.Treeview.Heading"
        self._dialog_labelframe_style = "Dialog.TLabelframe"
        self._dialog_labelframe_label_style = "Dialog.TLabelframe.Label"
        super().__init__(parent, title=title)
        # Final pass once all widgets are realized by Tk.
        try:
            self.after_idle(self._safe_apply_theme)
            self.after(90, self._safe_apply_theme)
        except Exception as exc:
            LOGGER.debug("ThemedDialog scheduling theme refresh failed: %s", exc)

    def _safe_apply_theme(self) -> None:
        if not self._dialog_exists():
            return
        self.apply_theme(self)

    def apply_theme(self, root: tk.Misc | None = None) -> None:
        if not self._dialog_exists():
            return
        c = self.theme.colors
        self.ui_tokens = resolve_ui_style_tokens(self.theme.key)
        root_widget = root or self
        try:
            self.configure(bg=c["app_bg"])
            self._apply_window_chrome_theme(self.theme.key == "dark")
            # Re-apply shortly after show to stabilize native titlebar color.
            self.after(60, self._safe_apply_window_chrome_theme)
            self.after(180, self._safe_apply_window_chrome_theme)
        except Exception as exc:
            LOGGER.debug("ThemedDialog base apply_theme failed: %s", exc)
        self._configure_ttk_styles()
        self._apply_theme_recursive(root_widget)

    def _safe_apply_window_chrome_theme(self) -> None:
        if not self._dialog_exists():
            return
        self._apply_window_chrome_theme(self.theme.key == "dark")

    def _dialog_exists(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception as exc:
            LOGGER.debug("ThemedDialog winfo_exists failed: %s", exc)
            return False

    def style_button(self, button: tk.Widget) -> None:
        bind_control_button_hover(button, self.theme.colors)

    def _configure_ttk_styles(self) -> None:
        c = self.theme.colors
        style = ttk.Style()
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
            self._dialog_scrollbar_style,
            background=c["surface_bg"],
            troughcolor=c["panel_bg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            arrowcolor=c["text_primary"],
        )
        style.configure(
            self._dialog_hscrollbar_style,
            background=c["surface_bg"],
            troughcolor=c["panel_bg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            arrowcolor=c["text_primary"],
        )
        style.configure(
            self._dialog_tree_style,
            background=c["tree_bg"],
            fieldbackground=c["tree_bg"],
            foreground=c["tree_fg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            rowheight=self.ui_tokens.metrics.dialog_tree_row_height,
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
        except Exception as exc:
            LOGGER.debug("ThemedDialog widget existence check failed: %s", exc)
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
            elif isinstance(widget, tk.Button):
                apply_control_button_style(widget, c, hovered=False)
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
            elif isinstance(widget, tk.Menu):
                widget.configure(
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                    activeforeground=c.get("control_hover_fg", c["text_primary"]),
                    relief="flat",
                    borderwidth=1,
                    tearoff=0,
                )
            elif isinstance(widget, tk.Canvas):
                widget.configure(bg=c["app_bg"], highlightbackground=c["placeholder_border"])
            elif isinstance(widget, tk.Scrollbar):
                widget.configure(
                    bg=c["surface_bg"],
                    activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                    troughcolor=c["panel_bg"],
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
            elif isinstance(widget, ttk.Button):
                widget.configure(style=self._dialog_button_style)
            elif isinstance(widget, ttk.Scrollbar):
                orient = str(widget.cget("orient") or "").strip().lower()
                widget.configure(style=self._dialog_hscrollbar_style if orient == "horizontal" else self._dialog_scrollbar_style)
            elif isinstance(widget, ttk.Treeview):
                widget.configure(style=self._dialog_tree_style)
                # Headings use a distinct style name in ttk.
                try:
                    widget.heading("#0", style=self._dialog_tree_heading_style)
                except Exception as exc:
                    LOGGER.debug("ThemedDialog tree heading style (#0) failed: %s", exc)
                for col in widget.cget("columns") or ():
                    try:
                        widget.heading(col, style=self._dialog_tree_heading_style)
                    except Exception as exc:
                        LOGGER.debug("ThemedDialog tree heading style (%s) failed: %s", col, exc)
                        continue
            elif isinstance(widget, ttk.LabelFrame):
                widget.configure(style=self._dialog_labelframe_style)
        except Exception as exc:
            LOGGER.debug("ThemedDialog recursive style application failed: %s", exc)

        try:
            children = widget.winfo_children()
        except Exception as exc:
            LOGGER.debug("ThemedDialog widget children listing failed: %s", exc)
            return
        for child in children:
            self._apply_theme_recursive(child)

        # Combobox popup list colors are controlled by option database, not ttk style.
        try:
            self.option_add("*TCombobox*Listbox.background", c["panel_bg"])
            self.option_add("*TCombobox*Listbox.foreground", c["text_primary"])
            self.option_add("*TCombobox*Listbox.selectBackground", c["tree_select_bg"])
            self.option_add("*TCombobox*Listbox.selectForeground", c["text_primary"])
            self.option_add("*TCombobox*Listbox.font", "{Segoe UI} 9")
            self.option_add("*Menu.background", c["menu_bg"])
            self.option_add("*Menu.foreground", c["menu_fg"])
            self.option_add("*Menu.activeBackground", c.get("control_hover_bg", c["panel_hover_bg"]))
            self.option_add("*Menu.activeForeground", c.get("control_hover_fg", c["text_primary"]))
        except Exception as exc:
            LOGGER.debug("ThemedDialog option database update failed: %s", exc)

    def _apply_window_chrome_theme(self, dark: bool) -> None:
        try:
            apply_window_chrome_theme(self, dark=bool(dark))
        except Exception as exc:
            LOGGER.debug("ThemedDialog chrome theme application failed: %s", exc)
