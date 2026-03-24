from __future__ import annotations

import ctypes
import os
import subprocess
import sys


def is_windows_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(argv: list[str] | None = None) -> bool:
    if os.name != "nt" or is_windows_admin():
        return False
    params = subprocess.list2cmdline(list(argv if argv is not None else sys.argv[1:]))
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    if int(result) <= 32:
        raise RuntimeError("Elevation administrateur refusee ou indisponible.")
    return True

