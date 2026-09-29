from monitoring.services.module_permissions import (
    MODULE_PERMISSION_CODES,
    custom_service_module_code,
    normalize_module_permissions,
)


def test_legacy_module_grant_keeps_full_access_during_migration():
    assert normalize_module_permissions([], legacy_grant=True) == list(MODULE_PERMISSION_CODES)


def test_module_permissions_require_read_and_credential_view_for_management():
    assert normalize_module_permissions(["credentials_manage", "update"]) == [
        "read",
        "update",
        "credentials_view",
        "credentials_manage",
    ]


def test_custom_service_module_code_matches_the_rbac_catalogue_contract():
    assert custom_service_module_code("emails") == "service_emails"
    assert custom_service_module_code("marches") == "service_marches_ffbc0b30"
