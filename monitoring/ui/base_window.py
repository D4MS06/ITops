# monitoring/ui/base_window.py

import os
import sys
from tkinter import Tk, Frame
from tkinter import ttk

def resource_path(relative_path: str) -> str:
    """
    Retourne le chemin absolu vers une ressource,
    que ce soit en dev ou après empaquetage PyInstaller.
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class BaseWindow:
    """
    Classe de base pour une fenêtre Tkinter.
    Fournit le centrage et le run loop.
    """
    def __init__(self, root: Tk, title: str = ""):
        self.root = root
        if title:
            self.root.title(title)
        self._apply_modern_theme()

    def _apply_modern_theme(self) -> None:
        """Applique un theme moderne (ttkbootstrap si dispo, sinon ttk natif)."""
        try:
            import ttkbootstrap as tb  # type: ignore

            style = tb.Style(theme="flatly")
            self.root.option_add("*Font", "Segoe UI 10")
            try:
                style.configure("Card.TFrame", background="#ffffff", relief="flat")
                style.configure("Treeview", rowheight=28)
            except Exception:
                pass
        except Exception:
            style = ttk.Style(self.root)
            try:
                style.theme_use("vista")
            except Exception:
                try:
                    style.theme_use("clam")
                except Exception:
                    pass

            style.configure("TButton", padding=(10, 6))
            style.configure("Treeview", rowheight=28)
            style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
            style.configure("Card.TFrame", background="#ffffff", relief="flat")

    def center_window(self) -> None:
        """Centre la fenêtre sur l’écran."""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def run(self) -> None:
        """Démarre la boucle événementielle."""
        self.root.mainloop()
