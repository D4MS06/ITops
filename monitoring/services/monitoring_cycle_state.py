from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MonitoringCycleState:
    failure_since: dict[str, float] = field(default_factory=dict)
    success_since: dict[str, float] = field(default_factory=dict)
    consecutive_failures: dict[str, int] = field(default_factory=dict)
    consecutive_successes: dict[str, int] = field(default_factory=dict)
    diagnostic_failure_logged: dict[str, bool] = field(default_factory=dict)

    def prune(self, known_ids: set[str], notification_state: dict[str, float]) -> None:
        self._prune_map(self.failure_since, known_ids)
        self._prune_map(self.success_since, known_ids)
        self._prune_map(self.consecutive_failures, known_ids)
        self._prune_map(self.consecutive_successes, known_ids)
        self._prune_map(self.diagnostic_failure_logged, known_ids)
        self._prune_map(notification_state, known_ids)

    @staticmethod
    def _prune_map(values: dict, known_ids: set[str]) -> None:
        for device_id in list(values):
            if device_id not in known_ids:
                values.pop(device_id, None)

    def mark_unknown(self, device_id: str) -> None:
        self.failure_since.pop(device_id, None)
        self.success_since.pop(device_id, None)
        self.consecutive_failures.pop(device_id, None)
        self.consecutive_successes.pop(device_id, None)
        self.diagnostic_failure_logged.pop(device_id, None)

    def register_success(self, device_id: str) -> int:
        self.failure_since.pop(device_id, None)
        self.consecutive_failures.pop(device_id, None)
        count = self.consecutive_successes.get(device_id, 0) + 1
        self.consecutive_successes[device_id] = count
        return count

    def register_failure(self, device_id: str) -> tuple[int, float | None]:
        self.success_since.pop(device_id, None)
        self.consecutive_successes.pop(device_id, None)
        count = self.consecutive_failures.get(device_id, 0) + 1
        self.consecutive_failures[device_id] = count
        return count, self.failure_since.get(device_id)

