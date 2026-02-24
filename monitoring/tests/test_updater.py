from monitoring.config.settings import NotificationSettings
from monitoring.utils.updater import find_available_update, is_newer_version


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
