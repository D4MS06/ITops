from __future__ import annotations

from dataclasses import replace
from threading import RLock
from typing import Callable

from monitoring.config.settings import NotificationSettings


class SettingsService:
    """Cache mutable autour des settings avec persistance explicite."""

    def __init__(
        self,
        *,
        loader: Callable[[], NotificationSettings],
        saver: Callable[[NotificationSettings], None],
    ) -> None:
        self._loader = loader
        self._saver = saver
        self._lock = RLock()
        self._settings: NotificationSettings | None = None

    def load(self, *, force: bool = False) -> NotificationSettings:
        with self._lock:
            if self._settings is None or force:
                self._settings = self._loader()
            return replace(self._settings)

    def get(self) -> NotificationSettings:
        return self.load()

    def current(self) -> NotificationSettings:
        with self._lock:
            if self._settings is None:
                self._settings = self._loader()
            return self._settings

    def save(self, settings: NotificationSettings) -> NotificationSettings:
        updated = replace(settings)
        with self._lock:
            self._saver(updated)
            self._settings = updated
            return replace(updated)

    def update(self, **changes) -> NotificationSettings:
        with self._lock:
            current = self.current()
            updated = replace(current, **changes)
            self._saver(updated)
            self._settings = updated
            return replace(updated)
