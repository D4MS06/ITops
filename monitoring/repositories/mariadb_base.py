from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


class MariaDBRepository:
    def __init__(
        self,
        *,
        connect: Callable[[], Any],
        ensure_database: Callable[[], None],
        lock: threading.Lock,
    ) -> None:
        self._connect = connect
        self._ensure_database = ensure_database
        self._lock = lock
