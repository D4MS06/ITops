from monitoring.api.app import _reverse_proxy_runtime_changed
from monitoring.config.settings import NotificationSettings


def test_reverse_proxy_runtime_unchanged_for_notification_only_update():
    current = NotificationSettings(
        web_server_port=8080,
        web_server_public_url="https://itops.mvl",
        web_server_reverse_proxy_type="caddy",
    )

    assert not _reverse_proxy_runtime_changed(
        current_settings=current,
        reverse_proxy="caddy",
        public_url="https://itops.mvl",
        upstream_port=8080,
    )


def test_reverse_proxy_runtime_changed_when_upstream_port_changes():
    current = NotificationSettings(
        web_server_port=8080,
        web_server_public_url="https://itops.mvl",
        web_server_reverse_proxy_type="caddy",
    )

    assert _reverse_proxy_runtime_changed(
        current_settings=current,
        reverse_proxy="caddy",
        public_url="https://itops.mvl",
        upstream_port=8081,
    )


def test_reverse_proxy_runtime_changed_when_public_url_changes():
    current = NotificationSettings(
        web_server_port=8080,
        web_server_public_url="https://itops.mvl",
        web_server_reverse_proxy_type="caddy",
    )

    assert _reverse_proxy_runtime_changed(
        current_settings=current,
        reverse_proxy="caddy",
        public_url="https://itops-new.mvl",
        upstream_port=8080,
    )
