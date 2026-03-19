from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable


class SQLiteRepository:
    def __init__(
        self,
        *,
        connect: Callable[[], sqlite3.Connection],
        ensure_database: Callable[[], None],
        lock: threading.Lock,
    ) -> None:
        self._connect = connect
        self._ensure_database = ensure_database
        self._lock = lock
