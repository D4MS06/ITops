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
        relation_links=[
            {"id": 3, "relation_id": 9, "source_record_id": "demo_logiciel", "target_record_id": "user-1"},
            {"id": 4, "relation_id": 99, "source_record_id": "old", "target_record_id": "missing"},
        ],
    )

    service = report["services"][0]
    assert report["format"] == "itops-custom-services-diagnostic-v3"
    assert service["records"][0]["values"]["password"] == "[masque]"
    assert service["records"][0]["version_token"] == "abc123"
    assert service["records"][0]["history"][0]["old_value"] == "[masque]"
    assert report["summary"]["history_event_count"] == 1
    assert service["unknown_record_fields"] == ["obsolete", "password"]
    assert service["missing_required_values"] == [{"record_id": "demo_logiciel", "field_key": "nom"}]
    assert report["summary"]["demo_record_count"] == 1
    assert report["summary"]["relation_link_count"] == 1
    assert report["summary"]["orphan_relation_link_count"] == 1
    assert report["relations"][0]["links"][0]["target_record_id"] == "user-1"
    assert report["orphan_relation_links"][0]["relation_id"] == 99
    assert any("Tuile portail absente" in issue["message"] for issue in report["issues"])
    assert any("Cible relation inconnue" in issue["message"] for issue in report["issues"])
