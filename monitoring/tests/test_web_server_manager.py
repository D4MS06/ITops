import threading
import time

from monitoring.services.web_server_manager import WebServerManager


class _DummyResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConfig:
    def __init__(self, *, app, host, port, reload, log_level, access_log, log_config=None):
        self.app = app
        self.host = host
        self.port = port
        self.reload = reload
        self.log_level = log_level
        self.access_log = access_log
        self.log_config = log_config


class _FakeServer:
    def __init__(self, config):
        self.config = config
        self.started = False
        self.should_exit = False

    def run(self):
        self.started = True
        while not self.should_exit:
            time.sleep(0.01)


class _ExplodingServer:
    def __init__(self, config):
        self.config = config
        self.started = False
        self.should_exit = False

    def run(self):
        raise OSError("bind failed")


def test_web_server_manager_runs_embedded_server(monkeypatch):
    calls = []

    def fake_factory():
        calls.append("factory")
        return object()

    monkeypatch.setattr("monitoring.services.web_server_manager.uvicorn.Config", _FakeConfig)
    monkeypatch.setattr("monitoring.services.web_server_manager.uvicorn.Server", _FakeServer)
    monkeypatch.setattr("monitoring.services.web_server_manager.urlopen", lambda *_args, **_kwargs: _DummyResponse())

    manager = WebServerManager(app_factory=fake_factory)
    state = manager.start(host="127.0.0.1", port=8123)

    assert calls == ["factory"]
    assert state.running is True
    assert state.url == "http://127.0.0.1:8123/"

    stopped = manager.stop()
    assert stopped.running is False


def test_web_server_manager_surfaces_startup_errors(monkeypatch):
    monkeypatch.setattr("monitoring.services.web_server_manager.uvicorn.Config", _FakeConfig)
    monkeypatch.setattr("monitoring.services.web_server_manager.uvicorn.Server", _ExplodingServer)

    manager = WebServerManager(app_factory=lambda: object())

    try:
        manager.start(host="127.0.0.1", port=8123)
        assert False, "Le demarrage devait echouer."
    except RuntimeError as exc:
        assert "bind failed" in str(exc)


def test_web_server_manager_formats_packaged_logging_error():
    message = WebServerManager._format_startup_error(RuntimeError("Unable to configure formatter 'default'"))
    assert "configuration de journalisation invalide" in message


def test_web_server_manager_formats_port_in_use_error():
    message = WebServerManager._format_startup_error(OSError("[WinError 10048] Only one usage of each socket address"))
    assert "port est deja utilise" in message


def test_web_server_manager_formats_missing_resource_error():
    message = WebServerManager._format_startup_error(FileNotFoundError("Directory 'C:/app/_internal/monitoring/web' does not exist"))
    assert "ressource du serveur web est absente" in message
