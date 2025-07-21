# src/monitoring/ui/view_mixins.py

from __future__ import annotations

import logging
from tkinter import Menu, ttk
from typing import Callable, Optional

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
