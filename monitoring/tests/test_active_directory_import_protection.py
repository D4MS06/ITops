from types import SimpleNamespace

from monitoring.api.app import (
    _active_directory_managed_record_field_keys,
    _active_directory_search_base_for_target,
    _sync_active_directory_technical_accounts,
)


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


def test_technical_accounts_use_the_dedicated_active_directory_ou() -> None:
    settings = SimpleNamespace(active_directory_base_dn="DC=example,DC=local")

    assert _active_directory_search_base_for_target(settings, "technical_accounts") == (
        "OU=Comptes de service,OU=Informatique,DC=example,DC=local"
    )
    assert _active_directory_search_base_for_target(settings, "users") == "DC=example,DC=local"


def test_technical_account_sync_preserves_the_stored_password() -> None:
    fields = [
        {"field_key": key, "field_kind": "text", "required": key in {"ad_object_guid", "account_name"}}
        for key in ("ad_object_guid", "account_name", "display_name", "upn", "description", "status_ad", "ou_ad_dn", "last_changed")
    ]
    fields[5].update({"field_kind": "list", "options": "Actif,Desactive", "default_value": "Actif"})

    class Logs:
        saved: list[dict] = []
        trashed: list[dict] = []

        def get_custom_service(self, **_kwargs):
            return {"code": "technical_accounts", "fields": fields}

        def list_custom_service_records(self, **_kwargs):
            return [{"id": "unrelated", "values": {"device_password": "secret"}}]

        def list_sync_source_cache_entries(self, **_kwargs):
            return [{
                "external_id": "ad-guid-1",
                "payload": {
                    "sAMAccountName": "svc_backup",
                    "displayName": "Sauvegarde",
                    "userPrincipalName": "svc_backup@example.local",
                    "description": "Compte de sauvegarde",
                    "distinguishedName": "CN=svc_backup,OU=Comptes de service,OU=Informatique,DC=example,DC=local",
                    "whenChanged": "20260918090000.0Z",
                    "userAccountControl": "2",
                },
            }]

        def save_custom_service_record(self, **kwargs):
            self.saved.append(kwargs)

        def trash_stale_synced_custom_service_records(self, **kwargs):
            self.trashed.append(kwargs)

    logs = Logs()
    summary = _sync_active_directory_technical_accounts(SimpleNamespace(logs=logs))

    assert summary == {"created": 1, "updated": 0, "skipped": 0}
    assert logs.saved[0]["values"]["account_name"] == "svc_backup"
    assert logs.saved[0]["values"]["device_login"] == "svc_backup"
    assert "device_password" not in logs.saved[0]["values"]
    assert logs.saved[0]["values"]["status_ad"] == "Desactive"
    assert logs.trashed[0]["active_external_ids"] == {"ad-guid-1"}
