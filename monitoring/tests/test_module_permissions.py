from monitoring.services.module_permissions import MODULE_PERMISSION_CODES, normalize_module_permissions


def test_legacy_module_grant_keeps_full_access_during_migration():
    assert normalize_module_permissions([], legacy_grant=True) == list(MODULE_PERMISSION_CODES)


def test_module_permissions_require_read_and_credential_view_for_management():
    assert normalize_module_permissions(["credentials_manage", "update"]) == [
        "read",
        "update",
        "credentials_view",
        "credentials_manage",
    ]
