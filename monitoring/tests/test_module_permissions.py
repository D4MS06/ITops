from monitoring.services.module_permissions import (
    MODULE_PERMISSION_CODES,
    can_manage_owned_custom_service,
    custom_service_module_code,
    decode_module_permissions,
    effective_module_permissions,
    normalize_module_permissions,
)


def test_legacy_module_grant_keeps_full_access_during_migration():
    assert normalize_module_permissions([], legacy_grant=True) == list(MODULE_PERMISSION_CODES)
    assert decode_module_permissions("{}") == list(MODULE_PERMISSION_CODES)
    assert decode_module_permissions("[]") == []
    assert decode_module_permissions("invalid") == []
    assert decode_module_permissions(0) == []


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


def test_module_definition_management_follows_ownership_not_builder_grants():
    allowed = dict(subject="alice", owner_subject="alice", is_admin=False, granted_permissions=[])
    assert can_manage_owned_custom_service(**allowed, permission="update")
    assert can_manage_owned_custom_service(**allowed, permission="delete")
    assert not can_manage_owned_custom_service(**{**allowed, "subject": "bob"}, permission="update")
    assert not can_manage_owned_custom_service(**{**allowed, "owner_subject": ""}, permission="update")
    assert can_manage_owned_custom_service(**{**allowed, "subject": "admin-user", "is_admin": True}, permission="delete")
    assert can_manage_owned_custom_service(subject="sa", owner_subject="", is_admin=False, granted_permissions=[], permission="delete")


def test_effective_permissions_are_role_rights_plus_personal_ownership_or_admin():
    assert effective_module_permissions(["read"]) == ["read"]
    assert effective_module_permissions(["read"], is_owner=True) == list(MODULE_PERMISSION_CODES)
    assert effective_module_permissions([], is_admin=True) == list(MODULE_PERMISSION_CODES)
