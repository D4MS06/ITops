# src/monitoring/ui/view_mixins.py

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import Menu, ttk
from typing import Callable, Optional

from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import apply_control_button_style

LOGGER = logging.getLogger(__name__)


class LockableMixin:
    """Mixin Tkinter pour verrouiller temporairement la vue.

    Attributes:
        _is_locked (bool): True si la vue est verrouillée.
    """

    def __init__(self) -> None:
        """Initialise le flag de verrouillage."""
        super().__init__()
        self._is_locked: bool = False

    def lock_view(self, widget: Optional[ttk.Widget] = None) -> None:
        """Verrouille la vue pour empêcher update_display() de tourner.

        Si `widget` est fourni, planifie automatiquement
        un déverrouillage après 500 ms.

        Args:
            widget (Optional[ttk.Widget]): widget Tkinter pour after().
        """
        self._is_locked = True
        if widget:
            try:
                widget.after(500, self.unlock_view)
            except Exception:
                LOGGER.exception("Impossible de planifier unlock_view")

    def unlock_view(self) -> None:
        """Déverrouille la vue, autorisant update_display()."""
        self._is_locked = False

    def is_locked_view(self) -> bool:
        """Retourne True si la vue est actuellement verrouillée."""
        return self._is_locked


class ContextMenuMixin(LockableMixin):
    """Mixin pour lier un menu contextuel qui met en pause l'affichage.

    Utilise `refresh_paused` pour suspendre temporairement
    les rafraîchissements pendant que le menu est ouvert.
    """

    def bind_context_menu_with_pause(
        self,
        tree: ttk.Treeview,
        menu_builder: Callable[[], Menu],
        pause_flag: str = "refresh_paused",
    ) -> None:
        """Lie le clic-droit (<Button-3>) d’un Treeview à un menu contextuel.

        1️⃣ Sélectionne la ligne cliquée.
        2️⃣ Met self.<pause_flag> = True pour suspendre update_display().
        3️⃣ Affiche le menu retourné par menu_builder().
        4️⃣ À la fermeture (<Unmap>), remet self.<pause_flag> = False.

        Args:
            tree (ttk.Treeview): Treeview sur lequel binder le clic-droit.
            menu_builder (Callable[[], Menu]): fonction retournant un Menu.
            pause_flag (str): nom de l’attribut booléen pour suspendre update_display().
        """
        def _on_right_click(event) -> None:
            # 1) mémoriser et sélectionner la ligne sous la souris
            try:
                iid = tree.identify_row(event.y)
                if iid:
                    tree.focus(iid)
                    tree.selection_set(iid)
                    setattr(self, "_last_iid", iid)
            except Exception:
                LOGGER.exception("Erreur identification/sélection IID")

            # 2) pause de l’actualisation
            setattr(self, pause_flag, True)

            # 3) construction et affichage du menu
            try:
                menu = menu_builder()
                # 4) reprise automatique à la fermeture du menu
                menu.bind(
                    "<Unmap>",
                    lambda e: setattr(self, pause_flag, False),
                    add="+",
                )
                menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                LOGGER.exception("Erreur affichage menu contextuel")
            finally:
                try:
                    menu.grab_release()
                except Exception:
                    pass

        tree.bind("<Button-3>", _on_right_click)


class ThemedViewMixin:
    """Mixin de theming reutilisable pour les vues Tk/ttk."""

    def _init_theme_support(self, theme_key: str, *, style_scope: str = "View") -> None:
        self.theme = resolve_theme(theme_key)
        self._view_style_scope = style_scope
        self._view_frame_style = f"{style_scope}.TFrame"
        self._view_label_style = f"{style_scope}.TLabel"
        self._view_check_style = f"{style_scope}.TCheckbutton"
        self._view_entry_style = f"{style_scope}.TEntry"
        self._view_button_style = f"{style_scope}.TButton"
        self._view_labelframe_style = f"{style_scope}.TLabelframe"
        self._view_labelframe_label_style = f"{style_scope}.TLabelframe.Label"
        self._view_combo_style = f"{style_scope}.TCombobox"
        self._view_scrollbar_style = f"{style_scope}.Vertical.TScrollbar"
        self._view_hscrollbar_style = f"{style_scope}.Horizontal.TScrollbar"

    def _configure_view_ttk_styles(self) -> None:
        c = self.theme.colors
        style = ttk.Style()
        style.configure(self._view_frame_style, background=c["app_bg"])
        style.configure(
            self._view_label_style,
            background=c["app_bg"],
            foreground=c["text_primary"],
        )
        style.configure(
            self._view_check_style,
            background=c["app_bg"],
            foreground=c["text_primary"],
        )
        style.map(
            self._view_check_style,
            background=[("active", c["app_bg"]), ("!active", c["app_bg"])],
            foreground=[("active", c["text_primary"]), ("!active", c["text_primary"])],
        )
        style.configure(
            self._view_entry_style,
            fieldbackground=c["panel_bg"],
            background=c["panel_bg"],
            foreground=c["text_primary"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
        )
        style.map(
            self._view_entry_style,
            fieldbackground=[("!disabled", c["panel_bg"])],
            foreground=[("!disabled", c["text_primary"])],
        )
        style.configure(
            self._view_labelframe_style,
            background=c["app_bg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
        )
        style.configure(
            self._view_labelframe_label_style,
            background=c["app_bg"],
            foreground=c["text_primary"],
        )
        style.configure(
            self._view_combo_style,
            fieldbackground=c["panel_bg"],
            background=c["panel_bg"],
            foreground=c["text_primary"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            arrowcolor=c["text_primary"],
        )
        style.map(
            self._view_combo_style,
            fieldbackground=[("readonly", c["panel_bg"])],
            foreground=[("readonly", c["text_primary"])],
            selectbackground=[("readonly", c["panel_bg"])],
            selectforeground=[("readonly", c["text_primary"])],
        )
        style.configure(
            self._view_button_style,
            background=c["button_inactive_bg"],
            foreground=c["button_inactive_fg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            padding=(8, 4),
        )
        style.map(
            self._view_button_style,
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
            self._view_scrollbar_style,
            background=c["surface_bg"],
            troughcolor=c["panel_bg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            arrowcolor=c["text_primary"],
        )
        style.configure(
            self._view_hscrollbar_style,
            background=c["surface_bg"],
            troughcolor=c["panel_bg"],
            bordercolor=c["placeholder_border"],
            lightcolor=c["placeholder_border"],
            darkcolor=c["placeholder_border"],
            arrowcolor=c["text_primary"],
        )

    def _apply_theme_recursive(self, widget: tk.Misc) -> None:
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
            elif isinstance(widget, tk.Text):
                widget.configure(
                    bg=c["tree_bg"],
                    fg=c["tree_fg"],
                    insertbackground=c["text_primary"],
                    highlightthickness=1,
                    highlightbackground=c["placeholder_border"],
                )
            elif isinstance(widget, ttk.Combobox):
                widget.configure(style=self._view_combo_style)
            elif isinstance(widget, ttk.Frame):
                widget.configure(style=self._view_frame_style)
            elif isinstance(widget, ttk.Label):
                widget.configure(style=self._view_label_style)
            elif isinstance(widget, ttk.Checkbutton):
                widget.configure(style=self._view_check_style)
            elif isinstance(widget, ttk.Entry):
                widget.configure(style=self._view_entry_style)
            elif isinstance(widget, ttk.Button):
                widget.configure(style=self._view_button_style)
            elif isinstance(widget, ttk.Scrollbar):
                orient = str(widget.cget("orient") or "").strip().lower()
                widget.configure(style=self._view_hscrollbar_style if orient == "horizontal" else self._view_scrollbar_style)
            elif isinstance(widget, ttk.LabelFrame):
                widget.configure(style=self._view_labelframe_style)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._apply_theme_recursive(child)
        try:
            root = widget.winfo_toplevel()
            root.option_add("*TCombobox*Listbox.background", c["panel_bg"])
            root.option_add("*TCombobox*Listbox.foreground", c["text_primary"])
            root.option_add("*TCombobox*Listbox.selectBackground", c["tree_select_bg"])
            root.option_add("*TCombobox*Listbox.selectForeground", c["text_primary"])
            root.option_add("*Menu.background", c["menu_bg"])
            root.option_add("*Menu.foreground", c["menu_fg"])
            root.option_add("*Menu.activeBackground", c.get("control_hover_bg", c["panel_hover_bg"]))
            root.option_add("*Menu.activeForeground", c.get("control_hover_fg", c["text_primary"]))
        except Exception:
            pass
