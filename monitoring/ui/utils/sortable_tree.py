"""
sortable_tree.py
================
Rend n'importe quel ``ttk.Treeview`` triable par clic sur l'en-tête.

Usage minimal (rétro-compatible) :
    make_treeview_sortable(self.tree)

Usage recommandé pour tri **persistant** après refresh :
    make_treeview_sortable(self.tree, self)

La vue appelante (`owner`) doit simplement définir deux attributs :
    self.sort_col      # str | None
    self.sort_reverse  # bool
Le helper les met à jour à chaque clic, afin que l'IHM puisse ré-insérer
les lignes dans le même ordre lors d'un update_display().
"""
from __future__ import annotations

import ipaddress
from typing import Any
from tkinter import ttk


def _as_key(val: str) -> Any:
    """Convertit *val* en clé triable : IP > nombre > chaîne insensible casse."""
    try:
        return ipaddress.ip_address(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return val.lower()


def make_treeview_sortable(tree: ttk.Treeview, owner: Any | None = None) -> None:
    """
    Ajoute le tri asc/desc à *tree*.

    Args:
        tree: instance ttk.Treeview.
        owner: objet appelant (vue) possédant *sort_col* et *sort_reverse*
               pour mémoriser l'état du tri. Peut être None.
    """
    dirs: dict[str, bool] = {}  # True → ascendant, False → descendant

    def _sort(col: str) -> None:
        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        data.sort(key=lambda t: _as_key(t[0]), reverse=not dirs.get(col, True))

        # ré-ordonnancement visuel
        for idx, (_, iid) in enumerate(data):
            tree.move(iid, "", idx)

        # mémoriser le nouveau sens
        dirs[col] = not dirs.get(col, True)

        # stocker dans la vue pour un tri persistant
        if owner is not None:
            setattr(owner, "sort_col", col)
            setattr(owner, "sort_reverse", not dirs[col])

    # attache le callback à chaque en-tête
    for col in tree["columns"]:
        tree.heading(col, command=lambda c=col: _sort(c))
