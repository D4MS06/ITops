import os
import ssl
import urllib.error
import json

from monitoring.config.settings import NotificationSettings
from monitoring.utils.updater import (
    UpdateInfo,
    _fetch_releases,
    find_available_update,
    is_newer_version,
    list_installable_releases,
)


def test_is_newer_version():
    assert is_newer_version("1.0.2", "1.0.3") is True
    assert is_newer_version("1.0.2", "1.0.2") is False
    assert is_newer_version("1.0.10", "1.0.2") is False
    assert is_newer_version("1.0.4-pre-release", "1.0.4") is True
    assert is_newer_version("unknown", "1.0.5-pre-release") is True


def test_fetch_releases_uses_owner_repo_from_settings(monkeypatch):
    settings = NotificationSettings(
        updates_enabled=True,
        github_owner="my-org",
        github_repo="my-repo",
        github_token="token",
    )
    captured = {}

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps([]).encode("utf-8")

    def _fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        return _FakeResp()

    monkeypatch.setattr("monitoring.utils.updater._urlopen_with_ssl", _fake_urlopen)
    releases = _fetch_releases(settings)
    assert releases == []
    assert captured["timeout"] == 15
    assert captured["url"] == "https://api.github.com/repos/my-org/my-repo/releases"


def test_find_available_update_from_releases(monkeypatch):
    settings = NotificationSettings(
        updates_enabled=True,
        github_owner="org",
        github_repo="repo",
        github_token="token",
        include_prerelease=False,
    )

    fake_releases = [
        {
            "tag_name": "v1.0.3",
            "name": "Release 1.0.3",
            "body": "notes",
            "draft": False,
            "prerelease": False,
            "assets": [
                {
                    "name": "NetworkMonitoringProject-Setup-1.0.3.exe",
                    "url": "https://api.github.com/assets/42",
                }
            ],
        }
    ]

    monkeypatch.setattr(
        "monitoring.utils.updater._fetch_releases",
        lambda _settings: fake_releases,
    )

    info = find_available_update("1.0.2", settings)
    assert info is not None
    assert info.version == "1.0.3"
    assert info.asset_name.endswith(".exe")


def test_find_available_update_selects_latest_newer_release(monkeypatch):
    settings = NotificationSettings(
        updates_enabled=True,
        github_owner="org",
        github_repo="repo",
        github_token="token",
        include_prerelease=True,
    )

    fake_releases = [
        {
            "tag_name": "v1.0.2",
            "name": "Release 1.0.2",
            "body": "stable",
            "draft": False,
            "prerelease": False,
            "assets": [
                {
                    "name": "NetworkMonitoringProject-Setup-1.0.2.exe",
                    "url": "https://api.github.com/assets/10",
                }
            ],
        },
        {
            "tag_name": "v1.0.3",
            "name": "Release 1.0.3 pre-release",
            "body": "prerelease",
            "draft": False,
            "prerelease": True,
            "assets": [
                {
                    "name": "NetworkMonitoringProject-Setup-1.0.3-pre-release.exe",
                    "url": "https://api.github.com/assets/11",
                }
            ],
        },
    ]

    monkeypatch.setattr(
        "monitoring.utils.updater._fetch_releases",
        lambda _settings: fake_releases,
    )

    info = find_available_update("1.0.2", settings)
    assert info is not None
    assert info.version == "1.0.3"
    assert info.asset_name.endswith(".exe")


def test_list_installable_releases_includes_prereleases(monkeypatch):
    settings = NotificationSettings(
        updates_enabled=True,
        github_owner="org",
        github_repo="repo",
        github_token="token",
    )
    fake_releases = [
        {
            "tag_name": "v1.0.3",
            "name": "Release 1.0.3 pre-release",
            "draft": False,
            "prerelease": True,
            "assets": [{"name": "NetworkMonitoringProject-Setup-1.0.3-pre-release.exe", "url": "u1"}],
        },
        {
            "tag_name": "v1.0.2",
            "name": "Release 1.0.2",
            "draft": False,
            "prerelease": False,
            "assets": [{"name": "NetworkMonitoringProject-Setup-1.0.2.exe", "url": "u2"}],
        },
    ]
    monkeypatch.setattr("monitoring.utils.updater._fetch_releases", lambda _settings: fake_releases)
    releases = list_installable_releases(settings)
    assert len(releases) == 2
    assert releases[0].tag_name in {"v1.0.3", "1.0.3"}


def test_find_available_update_with_explicit_target_tag(monkeypatch):
    settings = NotificationSettings(
        updates_enabled=True,
        github_owner="org",
        github_repo="repo",
        github_token="token",
        include_prerelease=False,
        update_target_tag="v1.0.3",
    )
    fake_releases = [
        {
            "tag_name": "v1.0.3",
            "name": "Release 1.0.3 pre-release",
            "draft": False,
            "prerelease": True,
            "assets": [{"name": "NetworkMonitoringProject-Setup-1.0.3-pre-release.exe", "url": "u3"}],
        }
    ]
    monkeypatch.setattr("monitoring.utils.updater._fetch_releases", lambda _settings: fake_releases)
    info = find_available_update("1.0.2", settings)
    assert info is not None
    assert info.version == "1.0.3"


def test_find_available_update_with_explicit_target_tag_allows_same_numeric_version(monkeypatch):
    settings = NotificationSettings(
        updates_enabled=True,
        github_owner="org",
        github_repo="repo",
        github_token="token",
        include_prerelease=True,
        update_target_tag="v1.0.8-pre-release",
    )
    fake_releases = [
        {
            "tag_name": "v1.0.8-pre-release",
            "name": "Release 1.0.8 pre-release",
            "draft": False,
            "prerelease": True,
            "assets": [{"name": "NetworkMonitoringProject-Setup-1.0.8.exe", "url": "u8"}],
        }
    ]
    monkeypatch.setattr("monitoring.utils.updater._fetch_releases", lambda _settings: fake_releases)
    monkeypatch.setattr("monitoring.utils.updater._collect_branch_release_candidates", lambda *_args, **_kwargs: [])
    info = find_available_update("1.0.8", settings)
    assert info is not None
    assert info.version == "1.0.8-pre-release"


def test_find_available_update_with_explicit_target_tag_skips_same_exact_prerelease(monkeypatch):
    settings = NotificationSettings(
        updates_enabled=True,
        github_owner="org",
        github_repo="repo",
        github_token="token",
        include_prerelease=True,
        update_target_tag="v1.0.8-pre-release",
    )
    fake_releases = [
        {
            "tag_name": "v1.0.8-pre-release",
            "name": "Release 1.0.8 pre-release",
            "draft": False,
            "prerelease": True,
            "assets": [{"name": "NetworkMonitoringProject-Setup-1.0.8-pre-release.exe", "url": "u8"}],
        }
    ]
    monkeypatch.setattr("monitoring.utils.updater._fetch_releases", lambda _settings: fake_releases)
    monkeypatch.setattr("monitoring.utils.updater._collect_branch_release_candidates", lambda *_args, **_kwargs: [])
    info = find_available_update("1.0.8-pre-release", settings)
    assert info is None


def test_list_installable_releases_falls_back_on_wrapped_ssl_error_windows(monkeypatch):
    settings = NotificationSettings(
        updates_enabled=True,
        github_owner="org",
        github_repo="repo",
        github_token="token",
    )

    def _raise_wrapped_ssl(*_args, **_kwargs):
        raise urllib.error.URLError(ssl.SSLError("CERTIFICATE_VERIFY_FAILED"))

    monkeypatch.setattr("monitoring.utils.updater._urlopen_with_ssl", _raise_wrapped_ssl)
    monkeypatch.setattr("monitoring.utils.updater.os.name", "nt", raising=False)
    monkeypatch.setattr(
        "monitoring.utils.updater._fetch_releases_via_powershell",
        lambda _settings: [
            {
                "tag_name": "v1.0.4",
                "name": "Release 1.0.4",
                "draft": False,
                "prerelease": False,
                "assets": [{"name": "NetworkMonitoringProject-Setup-1.0.4.exe", "url": "u4"}],
            }
        ],
    )

    releases = list_installable_releases(settings)
    assert len(releases) == 1
    assert releases[0].tag_name == "v1.0.4"


def test_download_update_asset_falls_back_on_wrapped_ssl_error_windows(monkeypatch):
    settings = NotificationSettings(
        updates_enabled=True,
        github_owner="org",
        github_repo="repo",
        github_token="token",
    )
    update = UpdateInfo(
        version="1.0.4",
        release_name="Release 1.0.4",
        release_notes="",
        asset_name="NetworkMonitoringProject-Setup-1.0.4.exe",
        asset_api_url="https://api.github.com/assets/44",
    )

    def _raise_wrapped_ssl(*_args, **_kwargs):
        raise urllib.error.URLError(ssl.SSLError("CERTIFICATE_VERIFY_FAILED"))

    def _fake_ps_download(_update, _settings, path):
        with open(path, "wb") as f:
            f.write(b"ok")

    monkeypatch.setattr("monitoring.utils.updater._urlopen_with_ssl", _raise_wrapped_ssl)
    monkeypatch.setattr("monitoring.utils.updater.os.name", "nt", raising=False)
    monkeypatch.setattr("monitoring.utils.updater._download_asset_via_powershell", _fake_ps_download)

    from monitoring.utils.updater import download_update_asset

    path = download_update_asset(update, settings)
    try:
        with open(path, "rb") as f:
            assert f.read() == b"ok"
    finally:
        if os.path.exists(path):
            os.remove(path)
