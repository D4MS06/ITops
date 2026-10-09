from __future__ import annotations

import platform
import subprocess


def windows_no_window_kwargs() -> dict:
    if not platform.system().lower().startswith("win"):
        return {}
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = 0
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startup_info,
    }
