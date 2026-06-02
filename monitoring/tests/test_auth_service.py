from monitoring.services.auth_service import AuthService


def test_auth_service_uses_configured_session_ttl(tmp_path):
    service = AuthService(
        session_ttl_seconds=900,
        password_store_path=tmp_path / "auth.json",
    )

    assert service.session_ttl_seconds == 900


def test_auth_service_clamps_session_ttl_to_five_minutes(tmp_path):
    service = AuthService(
        session_ttl_seconds=30,
        password_store_path=tmp_path / "auth.json",
    )

    assert service.session_ttl_seconds == 300


def test_auth_service_updates_session_ttl_at_runtime(tmp_path):
    service = AuthService(
        session_ttl_seconds=900,
        password_store_path=tmp_path / "auth.json",
    )

    service.set_session_ttl_seconds(1800)

    assert service.session_ttl_seconds == 1800
