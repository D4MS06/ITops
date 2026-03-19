from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DashboardMixinContract(Protocol):
    """Shared structural contract expected by dashboard mixins."""

    root: Any
    theme: Any
    model: Any
    controller: Any
    logger: Any
    notification_settings: Any
    web_server_manager: Any

    def _ordered_type_codes(self) -> list[str]: ...
    def _monitored_type_codes(self) -> list[str]: ...
    def _apply_theme(self) -> None: ...
    def _show_dashboard(self) -> None: ...
    def _apply_active_tree_filter(self) -> None: ...
