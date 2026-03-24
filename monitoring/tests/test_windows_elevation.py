from __future__ import annotations

from monitoring.utils import windows_elevation


def test_relaunch_as_admin_is_noop_on_non_windows(monkeypatch):
    monkeypatch.setattr(windows_elevation.os, "name", "posix")
    assert windows_elevation.relaunch_as_admin([]) is False


def test_relaunch_as_admin_invokes_shell_execute(monkeypatch):
    monkeypatch.setattr(windows_elevation.os, "name", "nt")
    monkeypatch.setattr(windows_elevation, "is_windows_admin", lambda: False)
    monkeypatch.setattr(windows_elevation.sys, "executable", r"C:\app\NetworkMonitoringProject.exe")
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

    assert windows_elevation.relaunch_as_admin(["--mode", "desktop"]) is True
    assert calls == [("runas", r"C:\app\NetworkMonitoringProject.exe", "--mode desktop", 1)]


def test_relaunch_as_admin_raises_when_shell_execute_fails(monkeypatch):
    monkeypatch.setattr(windows_elevation.os, "name", "nt")
    monkeypatch.setattr(windows_elevation, "is_windows_admin", lambda: False)
    monkeypatch.setattr(windows_elevation.sys, "executable", r"C:\app\NetworkMonitoringProject.exe")
    monkeypatch.setattr(windows_elevation.subprocess, "list2cmdline", lambda args: " ".join(args))

    class _Shell32:
        @staticmethod
        def ShellExecuteW(_hwnd, _verb, _exe, _params, _cwd, _show):
            return 5

    class _Windll:
        shell32 = _Shell32()

    monkeypatch.setattr(windows_elevation.ctypes, "windll", _Windll())

    try:
        windows_elevation.relaunch_as_admin(["--mode", "desktop"])
        assert False, "Une erreur etait attendue si l'elevation echoue."
    except RuntimeError as exc:
        assert "Elevation administrateur" in str(exc)
