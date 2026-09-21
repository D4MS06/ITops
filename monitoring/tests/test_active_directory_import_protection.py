from types import SimpleNamespace

from monitoring.api.app import (
    _active_directory_entry_is_within_search_base,
    _build_technical_accounts_sync_diagnostic,
    _active_directory_managed_record_field_keys,
    _active_directory_search_base_for_target,
    _active_directory_search_filter_for_target,
    _is_active_directory_technical_account_entry,
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


def test_technical_account_sync_uses_configured_ou_and_naming_filter() -> None:
    settings = SimpleNamespace(
        active_directory_base_dn="DC=example,DC=local",
        active_directory_technical_accounts_ou_dn="OU=Services techniques",
        active_directory_technical_accounts_filter="(&(objectClass=user)(sAMAccountName=svc-*))",
    )

    assert _active_directory_search_base_for_target(settings, "technical_accounts") == "OU=Services techniques,DC=example,DC=local"
    assert _active_directory_search_filter_for_target(settings, "technical_accounts") == "(&(objectClass=user)(sAMAccountName=svc-*))"


def test_agents_use_their_own_ldap_filter_and_exclude_technical_accounts() -> None:
    settings = SimpleNamespace(
        active_directory_base_dn="DC=example,DC=local",
        active_directory_user_filter="(&(objectClass=user)(department=IT))",
        active_directory_sync_technical_accounts=True,
        active_directory_technical_accounts_ou_dn="OU=Comptes de service,OU=Informatique",
    )

    assert _active_directory_search_filter_for_target(settings, "users") == "(&(objectClass=user)(department=IT))"
    assert _is_active_directory_technical_account_entry(
        settings,
        {"distinguishedName": "CN=svc_backup,OU=Comptes de service,OU=Informatique,DC=example,DC=local"},
    )
    assert not _is_active_directory_technical_account_entry(
        settings,
        {"distinguishedName": "CN=alice,OU=Utilisateurs,OU=Informatique,DC=example,DC=local"},
    )


def test_technical_account_entry_must_belong_to_the_configured_ou() -> None:
    base_dn = "OU=Comptes de service,OU=Informatique,DC=example,DC=local"

    assert _active_directory_entry_is_within_search_base(
        {"distinguishedName": "CN=svc_backup,OU=Comptes de service,OU=Informatique,DC=example,DC=local"},
        base_dn,
    )
    assert _active_directory_entry_is_within_search_base(
        {"distinguishedName": "['CN=svc_backup,OU=Comptes de service,OU=Informatique,DC=example,DC=local']"},
        base_dn,
    )
    assert not _active_directory_entry_is_within_search_base(
        {"distinguishedName": "CN=alice,OU=Utilisateurs,OU=DSI,DC=example,DC=local"},
        base_dn,
    )


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
            return [
                {
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
                },
                {
                    "external_id": "ad-guid-outside-scope",
                    "payload": {
                        "sAMAccountName": "alice",
                        "distinguishedName": "CN=alice,OU=Utilisateurs,DC=example,DC=local",
                    },
                },
            ]

        def save_custom_service_record(self, **kwargs):
            self.saved.append(kwargs)

        def trash_stale_synced_custom_service_records(self, **kwargs):
            self.trashed.append(kwargs)

    logs = Logs()
    summary = _sync_active_directory_technical_accounts(SimpleNamespace(
        logs=logs,
        settings_service=SimpleNamespace(get=lambda: SimpleNamespace(active_directory_base_dn="DC=example,DC=local")),
    ))

    assert summary == {"created": 1, "updated": 0, "skipped": 1}
    assert logs.saved[0]["values"]["account_name"] == "svc_backup"
    assert logs.saved[0]["values"]["device_login"] == "svc_backup"
    assert "device_password" not in logs.saved[0]["values"]
    assert logs.saved[0]["values"]["status_ad"] == "Desactive"
    assert logs.trashed[0]["active_external_ids"] == {"ad-guid-1"}


def test_technical_accounts_diagnostic_redacts_passwords_and_explains_scope() -> None:
    fields = [
        {"field_key": key, "field_kind": "text"}
        for key in ("ad_object_guid", "account_name", "display_name", "upn", "description", "status_ad", "ou_ad_dn", "last_changed")
    ]

    class Logs:
        def get_custom_service(self, **_kwargs):
            return {"code": "technical_accounts", "fields": fields}

        def list_custom_service_records(self, **_kwargs):
            return [{"id": "technical-1", "values": {"device_login": "svc_backup", "device_password": "never-export"}}]

        def list_sync_source_cache_entries(self, **_kwargs):
            return [
                {
                    "external_id": "guid-1",
                    "payload": {
                        "sAMAccountName": "svc_backup",
                        "distinguishedName": "CN=svc_backup,OU=Comptes de service,OU=Informatique,DC=example,DC=local",
                        "password": "never-export",
                    },
                },
                {
                    "external_id": "guid-2",
                    "payload": {
                        "sAMAccountName": "alice",
                        "distinguishedName": "CN=alice,OU=Utilisateurs,DC=example,DC=local",
                    },
                },
            ]

    settings = SimpleNamespace(
        active_directory_base_dn="DC=example,DC=local",
        active_directory_sync_technical_accounts=True,
        active_directory_bind_password="configured-but-never-exported",
    )
    diagnostic = _build_technical_accounts_sync_diagnostic(SimpleNamespace(
        logs=Logs(), settings_service=SimpleNamespace(get=lambda: settings),
    ))

    assert diagnostic["technical_accounts_cache"]["eligible_entry_count"] == 1
    assert diagnostic["technical_accounts_cache"]["entries"][1]["exclusion_reasons"] == ["hors_ou_technique_configuree"]
    assert diagnostic["technical_accounts_cache"]["entries"][0]["attributes"]["password"] == "[REDACTED]"
    assert "device_password" not in diagnostic["technical_accounts_module"]["records"][0]["values"]
    assert diagnostic["active_directory_configuration"]["bind_password_configured"] is True
