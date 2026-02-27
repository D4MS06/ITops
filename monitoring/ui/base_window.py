# monitoring/ui/base_window.py

import os
import sys
import ctypes
from tkinter import Tk, Frame, PhotoImage
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
        self._set_windows_app_id()
        self._apply_app_icon()
        self._apply_modern_theme()

    @staticmethod
    def _set_windows_app_id() -> None:
        """Ensure Windows taskbar uses a stable app identity/icon."""
        if os.name != "nt":
            return
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
                "NetworkMonitoringProject.DesktopApp"
            )
        except Exception:
            pass

    def _apply_app_icon(self) -> None:
        """Apply app icon to window title bar and taskbar when possible."""
        png_icon = resource_path(os.path.join("monitoring", "ui", "assets", "app_icon_pulse.png"))
        fallback_png_icon = resource_path(os.path.join("monitoring", "ui", "assets", "logo.png"))
        ico_icon = resource_path(os.path.join("monitoring", "ui", "assets", "app.ico"))

        # Cross-platform icon for Tk windows.
        try:
            self._icon_image = None
            if os.path.exists(png_icon):
                self._icon_image = PhotoImage(file=png_icon)
            elif os.path.exists(fallback_png_icon):
                self._icon_image = PhotoImage(file=fallback_png_icon)
            if self._icon_image is not None:
                self.root.iconphoto(True, self._icon_image)
        except Exception:
            self._icon_image = None

        # Native Windows .ico support (helps title bar/taskbar in some environments).
        if os.name == "nt":
            try:
                if os.path.exists(ico_icon):
                    self.root.iconbitmap(default=ico_icon)
            except Exception:
                pass

    def _apply_window_chrome_theme(self, dark: bool) -> None:
        """Apply native Windows title bar dark/light appearance when supported."""
        if os.name != "nt":
            return
        try:
            self.root.update_idletasks()
            hwnd = self.root.winfo_id()
            try:
                parent = ctypes.windll.user32.GetParent(hwnd)  # type: ignore[attr-defined]
                if parent:
                    hwnd = parent
            except Exception:
                pass
            value = ctypes.c_int(1 if dark else 0)
            size = ctypes.sizeof(value)
            # 20 on recent Windows 10/11, 19 on some builds.
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
