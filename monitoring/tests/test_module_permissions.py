from monitoring.services.module_permissions import (
    MODULE_PERMISSION_CODES,
    can_manage_owned_custom_service,
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


def test_module_definition_management_is_limited_to_eligible_owner_or_admin():
    allowed = dict(subject="alice", owner_subject="alice", is_admin=False, granted_permissions=["create", "update"])
    assert can_manage_owned_custom_service(**allowed, permission="update")
    assert not can_manage_owned_custom_service(**allowed, permission="delete")
    assert not can_manage_owned_custom_service(**{**allowed, "subject": "bob"}, permission="update")
    assert not can_manage_owned_custom_service(**{**allowed, "owner_subject": ""}, permission="update")
    assert not can_manage_owned_custom_service(**{**allowed, "granted_permissions": ["update"]}, permission="update")
    assert can_manage_owned_custom_service(**{**allowed, "subject": "admin-user", "is_admin": True}, permission="delete")
    assert can_manage_owned_custom_service(subject="sa", owner_subject="", is_admin=False, granted_permissions=[], permission="delete")
