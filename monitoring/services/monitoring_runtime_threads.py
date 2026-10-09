from __future__ import annotations

import threading
from collections.abc import Callable


class MonitoringRuntimeThreads:
    def __init__(self) -> None:
        self._threads: dict[str, threading.Thread] = {}

    def get(self, dtype: str) -> threading.Thread | None:
        return self._threads.get(dtype)

    def ensure_started(self, dtype: str, target: Callable[[], None]) -> bool:
        thread = self._threads.get(dtype)
        if thread is not None and thread.is_alive():
            return False
        thread = threading.Thread(target=target, daemon=True, name=f"ApiMon-{dtype}")
        thread.start()
        self._threads[dtype] = thread
        return True

    def join(self, dtype: str, timeout: float) -> None:
        thread = self._threads.get(dtype)
        if thread is not None:
            thread.join(timeout=timeout)
