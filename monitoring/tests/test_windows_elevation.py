from __future__ import annotations

from monitoring.utils import windows_elevation


def test_relaunch_as_admin_is_noop_on_non_windows(monkeypatch):
    monkeypatch.setattr(windows_elevation.os, "name", "posix")
    assert windows_elevation.relaunch_as_admin([]) is False


def test_relaunch_as_admin_invokes_shell_execute(monkeypatch):
    monkeypatch.setattr(windows_elevation.os, "name", "nt")
    monkeypatch.setattr(windows_elevation, "is_windows_admin", lambda: False)
    monkeypatch.setattr(windows_elevation.sys, "frozen", False, raising=False)
    monkeypatch.setattr(windows_elevation.sys, "argv", [r"C:\repo\main.py", "--mode", "server"])
    monkeypatch.setattr(windows_elevation.sys, "executable", r"C:\app\NetworkMonitoringProject.exe")
    monkeypatch.setattr(windows_elevation.os.path, "isfile", lambda _path: False)
    monkeypatch.setattr(windows_elevation.subprocess, "list2cmdline", lambda args: " ".join(args))

    calls = []

    class _Shell32:
        @staticmethod
        def ShellExecuteW(_hwnd, verb, exe, params, _cwd, show):
            calls.append((verb, exe, params, show))
            return 33

    class _Windll:
        shell32 = _Shell32()

    monkeypatch.setattr(windows_elevation.ctypes, "windll", _Windll())

    assert windows_elevation.relaunch_as_admin(["--mode", "server"]) is True
    assert calls == [("runas", r"C:\app\NetworkMonitoringProject.exe", r"C:\repo\main.py --mode server", 1)]


def test_relaunch_as_admin_raises_when_shell_execute_fails(monkeypatch):
    monkeypatch.setattr(windows_elevation.os, "name", "nt")
    monkeypatch.setattr(windows_elevation, "is_windows_admin", lambda: False)
    monkeypatch.setattr(windows_elevation.sys, "frozen", False, raising=False)
    monkeypatch.setattr(windows_elevation.sys, "argv", [r"C:\repo\main.py", "--mode", "server"])
    monkeypatch.setattr(windows_elevation.sys, "executable", r"C:\app\NetworkMonitoringProject.exe")
    monkeypatch.setattr(windows_elevation.os.path, "isfile", lambda _path: False)
    monkeypatch.setattr(windows_elevation.subprocess, "list2cmdline", lambda args: " ".join(args))

    class _Shell32:
        @staticmethod
        def ShellExecuteW(_hwnd, _verb, _exe, _params, _cwd, _show):
            return 5

    class _Windll:
        shell32 = _Shell32()

    monkeypatch.setattr(windows_elevation.ctypes, "windll", _Windll())

    try:
        windows_elevation.relaunch_as_admin(["--mode", "server"])
        assert False, "Une erreur etait attendue si l'elevation echoue."
    except RuntimeError as exc:
        assert "Elevation administrateur" in str(exc)


def test_relaunch_parameters_for_frozen_binary(monkeypatch):
    monkeypatch.setattr(windows_elevation.sys, "frozen", True, raising=False)
    monkeypatch.setattr(windows_elevation.subprocess, "list2cmdline", lambda args: " ".join(args))

    params = windows_elevation._relaunch_parameters(["--mode", "server"])

    assert params == "--mode server"


def test_elevated_executable_uses_pythonw_when_available(monkeypatch):
    monkeypatch.setattr(windows_elevation.sys, "frozen", False, raising=False)
    monkeypatch.setattr(windows_elevation.sys, "executable", r"C:\Python312\python.exe")
    monkeypatch.setattr(windows_elevation.os.path, "isfile", lambda path: path.endswith("pythonw.exe"))

    exe = windows_elevation._elevated_executable()

    assert exe == r"C:\Python312\pythonw.exe"
