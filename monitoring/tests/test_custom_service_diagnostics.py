from monitoring.services.custom_service_diagnostics import build_custom_service_diagnostic


def test_custom_service_diagnostic_reports_portal_and_record_configuration_gaps():
    report = build_custom_service_diagnostic(
        services=[{
            "code": "logiciels",
            "label": "Logiciels",
            "is_active": True,
            "fields": [
                {"field_key": "nom", "required": True},
                {"field_key": "statut", "required": False},
            ],
        }],
        records_by_service={"logiciels": [{
            "id": "demo_logiciel",
            "version_token": "abc123",
            "values": {"nom": "", "obsolete": "x", "password": "secret"},
        }]},
        record_histories={
            ("logiciels", "demo_logiciel"): [{
                "id": 4,
                "field_key": "password",
                "old_value": "old-secret",
                "new_value": "new-secret",
                "changed_at": "2026-08-27 10:00:00",
                "changed_by": "admin",
                "change_source": "manual",
            }],
        },
        auth_modules=[],
        auth_roles=[],
        relations=[{"id": 9, "source_service_code": "logiciels", "target_service_code": "inconnu"}],
        relation_impacts={9: {"link_count": 0}},
    )

    service = report["services"][0]
    assert service["records"][0]["values"]["password"] == "[masque]"
    assert service["records"][0]["version_token"] == "abc123"
    assert service["records"][0]["history"][0]["old_value"] == "[masque]"
    assert report["summary"]["history_event_count"] == 1
    assert service["unknown_record_fields"] == ["obsolete", "password"]
    assert service["missing_required_values"] == [{"record_id": "demo_logiciel", "field_key": "nom"}]
    assert report["summary"]["demo_record_count"] == 1
    assert any("Tuile portail absente" in issue["message"] for issue in report["issues"])
    assert any("Cible relation inconnue" in issue["message"] for issue in report["issues"])
