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
