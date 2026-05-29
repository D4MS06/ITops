from monitoring.services.import_credentials_policy import normalize_credential_import_mode, resolve_credential_import_values


def test_normalize_credential_import_mode_defaults_to_preserve():
    assert normalize_credential_import_mode(None) == "preserve_on_blank"
    assert normalize_credential_import_mode("unknown") == "preserve_on_blank"
    assert normalize_credential_import_mode("OVERWRITE") == "overwrite"


def test_resolve_credentials_preserve_on_blank_keeps_existing_on_update():
    resolved = resolve_credential_import_values(
        mode="preserve_on_blank",
        operation="update",
        login_present=True,
        login_value="",
        password_present=True,
        password_value="",
    )
    assert resolved.login is None
    assert resolved.password is None


def test_resolve_credentials_overwrite_allows_blank_on_update():
    resolved = resolve_credential_import_values(
        mode="overwrite",
        operation="update",
        login_present=True,
        login_value="",
        password_present=True,
        password_value="",
    )
    assert resolved.login == ""
    assert resolved.password == ""


def test_resolve_credentials_ignore_always_returns_none():
    resolved = resolve_credential_import_values(
        mode="ignore",
        operation="create",
        login_present=True,
        login_value="admin",
        password_present=True,
        password_value="secret",
    )
    assert resolved.login is None
    assert resolved.password is None
