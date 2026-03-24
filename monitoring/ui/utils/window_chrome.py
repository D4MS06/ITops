from __future__ import annotations

import ctypes
import os


def apply_window_chrome_theme(widget, *, dark: bool) -> None:
    """Apply native Windows title bar dark/light appearance when supported."""
    if os.name != "nt":
        return
    try:
        widget.update_idletasks()
        hwnd = widget.winfo_id()
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
