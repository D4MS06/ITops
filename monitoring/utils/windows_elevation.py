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


def _relaunch_parameters(argv: list[str] | None = None) -> str:
    args = list(argv if argv is not None else sys.argv[1:])
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline(args)
    script = str(sys.argv[0] or "").strip()
    if script:
        return subprocess.list2cmdline([script, *args])
    return subprocess.list2cmdline(args)


def _elevated_executable() -> str:
    exe = str(sys.executable or "").strip()
    if getattr(sys, "frozen", False):
        return exe
    lowered = exe.lower()
    if lowered.endswith("python.exe"):
        candidate = f"{exe[:-10]}pythonw.exe"
        if os.path.isfile(candidate):
            return candidate
    return exe


def relaunch_as_admin(argv: list[str] | None = None) -> bool:
    if os.name != "nt" or is_windows_admin():
        return False
    params = _relaunch_parameters(argv)
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", _elevated_executable(), params, None, 1)
    if int(result) <= 32:
        raise RuntimeError("Elevation administrateur refusee ou indisponible.")
    return True
