from monitoring.api.app import _active_directory_managed_record_field_keys


def test_email_account_sync_only_manages_address() -> None:
    assert _active_directory_managed_record_field_keys(
        record={"sync_source_kind": "active_directory", "sync_target_kind": "email_accounts"},
        profiles=[],
    ) == {"address"}


def test_profile_sync_only_manages_configured_fields() -> None:
    profiles = [{
        "id": "profile-1",
        "is_active": True,
        "options": {
            "field_mappings": [
                {"attribute": "mail", "field_key": "address"},
                {"attribute": "proxyAddresses", "field_key": "alias", "target": "ignore"},
            ],
            "dn_ou_field_mappings": [{"field_key": "site"}],
        },
    }]

    assert _active_directory_managed_record_field_keys(
        record={"sync_source_kind": "active_directory", "sync_target_kind": "profile:profile-1"},
        profiles=profiles,
    ) == {"address", "site"}
