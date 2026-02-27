from monitoring.config.settings import NotificationSettings
from monitoring.utils.updater import find_available_update, is_newer_version, list_installable_releases


def test_is_newer_version():
    assert is_newer_version("1.0.2", "1.0.3") is True
    assert is_newer_version("1.0.2", "1.0.2") is False
    assert is_newer_version("1.0.10", "1.0.2") is False


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
