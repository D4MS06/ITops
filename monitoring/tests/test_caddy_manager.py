from __future__ import annotations

from pathlib import Path

from monitoring.config.settings import NotificationSettings
from monitoring.services.caddy_manager import CaddyManager


def test_caddy_manager_writes_config_and_runs_commands(monkeypatch, tmp_path):
    manager = CaddyManager()
    manager._program_data_dir = tmp_path / "programdata"
    manager._config_path = manager._program_data_dir / "Caddyfile"

    executed: list[tuple[list[str], bool]] = []
    monkeypatch.setattr(manager, "_resolve_caddy_exe", lambda: tmp_path / "caddy.exe")
    monkeypatch.setattr(manager, "_validate_config", lambda _exe: executed.append((["validate"], False)))
    monkeypatch.setattr(manager, "_ensure_service", lambda _exe: executed.append((["service"], False)))
    monkeypatch.setattr(manager, "_ensure_firewall_rule", lambda: executed.append((["firewall"], False)))
    monkeypatch.setattr(manager, "_reload_or_restart", lambda _exe: executed.append((["reload"], False)))

    settings = NotificationSettings(
        web_server_host="127.0.0.1",
        web_server_port=8123,
        web_server_public_url="https://monitoring.mvl",
        web_server_use_public_url=True,
    )

    monkeypatch.setattr("monitoring.services.caddy_manager.os.name", "nt")
    manager.sync_from_settings(settings)

    content = manager._config_path.read_text(encoding="ascii")
    assert "monitoring.mvl" in content
    assert "reverse_proxy 127.0.0.1:8123" in content
    assert executed == [(["validate"], False), (["service"], False), (["firewall"], False), (["reload"], False)]


def test_caddy_manager_noop_when_public_proxy_disabled(monkeypatch):
    manager = CaddyManager()
    called = []
    monkeypatch.setattr(manager, "_resolve_caddy_exe", lambda: called.append("resolve"))

    settings = NotificationSettings(web_server_use_public_url=False, web_server_public_url="https://monitoring.mvl")
    manager.sync_from_settings(settings)

    assert called == []


def test_caddy_manager_rejects_invalid_public_url(monkeypatch):
    manager = CaddyManager()
    monkeypatch.setattr("monitoring.services.caddy_manager.os.name", "nt")
    settings = NotificationSettings(web_server_use_public_url=True, web_server_public_url="://")
    try:
        manager.sync_from_settings(settings)
        assert False, "La validation de l'URL publique devait echouer."
    except RuntimeError as exc:
        assert "URL publique" in str(exc)


def test_caddy_manager_exports_root_certificate(tmp_path):
    manager = CaddyManager()
    source = tmp_path / "root.crt"
    source.write_text("dummy-cert", encoding="ascii")
    destination = tmp_path / "export" / "monitoring-root.crt"

    manager.locate_root_certificate = lambda: source  # type: ignore[method-assign]
    exported = manager.export_root_certificate(destination)

    assert exported == destination
    assert destination.read_text(encoding="ascii") == "dummy-cert"


def test_caddy_manager_refreshes_shared_exportable_certificate(tmp_path):
    manager = CaddyManager()
    manager._program_data_dir = tmp_path / "programdata"
    manager._shared_root_cert_path = manager._program_data_dir / "certs" / "root.crt"
    source = tmp_path / "source-root.crt"
    source.write_text("shared-cert", encoding="ascii")
    manager._root_certificate_source_candidates = lambda: [source]  # type: ignore[method-assign]
    manager._ensure_shared_certificate_read_access = lambda _path: None  # type: ignore[method-assign]

    refreshed = manager._refresh_exportable_root_certificate()

    assert refreshed == manager._shared_root_cert_path
    assert manager._shared_root_cert_path.read_text(encoding="ascii") == "shared-cert"
    assert manager.locate_root_certificate() == manager._shared_root_cert_path


def test_caddy_manager_creates_windows_service_with_expected_sc_syntax(monkeypatch, tmp_path):
    manager = CaddyManager()
    manager._config_path = tmp_path / "Caddyfile"
    manager._config_path.write_text("monitoring.mvl {}", encoding="ascii")

    commands: list[list[str]] = []
    monkeypatch.setattr(manager, "_service_exists", lambda: False)
    monkeypatch.setattr(manager, "_run", lambda command, allow_failure=False: commands.append(command))

    manager._ensure_service(tmp_path / "caddy.exe")

    assert commands[0] == [
        "sc.exe",
        "create",
        "NetworkMonitoringCaddy",
        "binPath=",
        f'"{tmp_path / "caddy.exe"}" run --config "{manager._config_path}" --adapter caddyfile',
        "start=",
        "auto",
    ]
