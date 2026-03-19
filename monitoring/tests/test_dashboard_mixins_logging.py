from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from monitoring.ui.dashboard_menu_mixin import DashboardMenuMixin
from monitoring.ui.dashboard_theme_mixin import DashboardThemeMixin


class _MenuHarness(DashboardMenuMixin):
    def __init__(self) -> None:
        self.logger = MagicMock()
        self.closed = False

    def _close_custom_menu(self) -> None:
        self.closed = True


class _MenuCloseHarness(DashboardMenuMixin):
    def __init__(self) -> None:
        self.logger = MagicMock()
        self._menu_outside_click_bind = "bind-id"
        self._menu_popups = []
        self._submenu_anchor_by_level = {}
        self.root = SimpleNamespace(unbind=self._unbind_raises)

    @staticmethod
    def _unbind_raises(*_args, **_kwargs):
        raise RuntimeError("unbind failed")


def test_menu_action_exception_is_logged_and_menu_is_closed():
    harness = _MenuHarness()

    def _action():
        raise ValueError("boom")

    DashboardMenuMixin._on_custom_menu_action(harness, _action)

    assert harness.closed is True
    assert harness.logger.debug.called


def test_close_custom_menu_logs_unbind_failures_and_resets_state():
    popup = SimpleNamespace(
        place_forget=lambda: (_ for _ in ()).throw(RuntimeError("place failed")),
        destroy=lambda: None,
    )
    harness = _MenuCloseHarness()
    harness._menu_popups = [popup]

    DashboardMenuMixin._close_custom_menu(harness)

    assert harness._menu_outside_click_bind is None
    assert harness._menu_popups == []
    assert harness.logger.debug.called


def test_theme_refresh_status_indicators_logs_and_continues_on_view_error():
    class _BadView:
        @staticmethod
        def refresh_status_icons(_style_key):
            raise RuntimeError("refresh failed")

    good_calls: list[str] = []

    class _GoodView:
        @staticmethod
        def refresh_status_icons(style_key):
            good_calls.append(str(style_key))

    fake = SimpleNamespace(
        notification_settings=SimpleNamespace(status_indicator_style="dot"),
        type_views={"bad": _BadView(), "good": _GoodView()},
        consolidated_app=None,
        logger=MagicMock(),
    )

    DashboardThemeMixin._refresh_status_indicators(fake)

    assert good_calls == ["dot"]
    assert fake.logger.debug.called
