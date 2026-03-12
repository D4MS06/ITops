from __future__ import annotations

import threading
import time
import webbrowser
from dataclasses import dataclass
from typing import Callable
from urllib.request import urlopen

import uvicorn


@dataclass(frozen=True)
class WebServerState:
    running: bool
    host: str
    port: int
    url: str
    pid: int | None


class WebServerManager:
    def __init__(self, *, app_factory: Callable[[], object] | None = None) -> None:
        self._app_factory = app_factory
        self._host = "127.0.0.1"
        self._port = 8000
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._startup_error: Exception | None = None

    def state(self) -> WebServerState:
        running = self._server is not None and self._server_thread is not None and self._server_thread.is_alive()
        return WebServerState(
            running=running,
            host=self._host,
            port=self._port,
            url=f"http://{self._host}:{self._port}/",
            pid=None,
        )

    def start(self, *, host: str, port: int, open_browser: bool = False) -> WebServerState:
        normalized_host = str(host or "127.0.0.1").strip() or "127.0.0.1"
        normalized_port = max(1, int(port or 8000))
        self._host = normalized_host
        self._port = normalized_port

        with self._lock:
            if self.state().running:
                return self.state()

            if self._app_factory is None:
                raise RuntimeError("Aucune fabrique ASGI configuree pour le serveur web.")

            app = self._app_factory()
            self._startup_error = None
            config = uvicorn.Config(
                app=app,
                host=normalized_host,
                port=normalized_port,
                reload=False,
                log_level="info",
                access_log=False,
                log_config=None,
            )
            self._server = uvicorn.Server(config)

            def _run_server() -> None:
                try:
                    assert self._server is not None
                    self._server.run()
                except Exception as exc:
                    self._startup_error = exc

            self._server_thread = threading.Thread(
                target=_run_server,
                daemon=True,
                name="EmbeddedWebServer",
            )
            self._server_thread.start()

        self._wait_until_ready(timeout_seconds=8.0)
        if open_browser:
            try:
                webbrowser.open(self.state().url)
            except Exception:
                pass
        return self.state()

    def stop(self) -> WebServerState:
        with self._lock:
            server = self._server
            thread = self._server_thread
            self._server = None
            self._server_thread = None
            self._startup_error = None

        if server is not None:
            server.should_exit = True
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)
        return self.state()

    def restart(self, *, host: str, port: int, open_browser: bool = False) -> WebServerState:
        self.stop()
        return self.start(host=host, port=port, open_browser=open_browser)

    def _wait_until_ready(self, *, timeout_seconds: float) -> None:
        deadline = time.time() + max(1.0, timeout_seconds)
        probe_host = "127.0.0.1" if self._host in {"0.0.0.0", "::"} else self._host
        url = f"http://{probe_host}:{self._port}/health"
        while time.time() < deadline:
            if self._startup_error is not None:
                raise RuntimeError(f"Echec de demarrage du serveur web: {self._startup_error}")
            if self._server is not None and getattr(self._server, "started", False):
                try:
                    with urlopen(url, timeout=0.75) as response:
                        if int(getattr(response, "status", 500)) < 500:
                            return
                except Exception:
                    pass
            if self._server_thread is not None and not self._server_thread.is_alive():
                if self._startup_error is not None:
                    raise RuntimeError(f"Echec de demarrage du serveur web: {self._startup_error}")
                raise RuntimeError("Le serveur web s'est arrete pendant le demarrage.")
            time.sleep(0.2)
        raise RuntimeError(f"Le serveur web ne repond pas sur {url}.")
