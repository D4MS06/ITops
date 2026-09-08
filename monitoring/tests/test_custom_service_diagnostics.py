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
    assert report["format"] == "itops-custom-services-diagnostic-v4"
    assert service["records"][0]["values"]["password"] == "[masque]"
    assert service["records"][0]["version_token"] == "abc123"
    assert service["records"][0]["history"][0]["old_value"] == "[masque]"
    assert report["summary"]["history_event_count"] == 1
    assert service["unknown_record_fields"] == ["obsolete", "password"]
    assert service["missing_required_values"] == [{"record_id": "demo_logiciel", "field_key": "nom"}]
    assert report["summary"]["demo_record_count"] == 1
    assert report["summary"]["relation_link_count"] == 1
    assert report["summary"]["orphan_relation_link_count"] == 1
    assert report["summary"]["relation_integrity_issue_count"] == 0
    assert report["relations"][0]["links"][0]["target_record_id"] == "user-1"
    assert report["orphan_relation_links"][0]["relation_id"] == 99
    assert any("Tuile portail absente" in issue["message"] for issue in report["issues"])
    assert any("Cible relation inconnue" in issue["message"] for issue in report["issues"])


def test_custom_service_diagnostic_detects_historical_relation_integrity_gaps():
    report = build_custom_service_diagnostic(
        services=[
            {"code": "postes", "fields": []},
            {"code": "logiciels", "fields": []},
        ],
        records_by_service={
            "postes": [{"id": "poste-1"}, {"id": "poste-2"}],
            "logiciels": [{"id": "logiciel-1"}],
        },
        auth_modules=[],
        auth_roles=[],
        relations=[{
            "id": 9,
            "source_service_code": "postes",
            "target_service_code": "logiciels",
            "cardinality": "many_to_one",
            "required": True,
        }],
        relation_impacts={},
        relation_links=[
            {"id": 1, "relation_id": 9, "source_record_id": "poste-1", "target_record_id": "logiciel-1"},
            {"id": 2, "relation_id": 9, "source_record_id": "poste-1", "target_record_id": "logiciel-supprime"},
            {"id": 3, "relation_id": 9, "source_record_id": "poste-supprime", "target_record_id": "logiciel-1"},
        ],
    )

    integrity = report["relation_integrity"][0]
    assert integrity["missing_source_record_ids"] == ["poste-supprime"]
    assert integrity["missing_target_record_ids"] == ["logiciel-supprime"]
    assert integrity["cardinality_violations"] == ["source:poste-1"]
    assert integrity["missing_required_source_record_ids"] == ["poste-2"]
    assert report["summary"]["relation_integrity_issue_count"] == 4


def test_custom_service_diagnostic_materializes_inherited_agent_paths():
    report = build_custom_service_diagnostic(
        services=[{
            "code": "copieurs",
            "label": "Copieurs",
            "fields": [],
            "treeview_config": (
                '{"relationship_inheritance":{"enabled":true,"relation_id":10,'
                '"operational_filter":{"field_key":"status","visible_values":["En service"]}}}'
            ),
        }],
        records_by_service={"copieurs": [{"id": "copieur-1", "values": {"status": "En service"}}]},
        auth_modules=[],
        auth_roles=[],
        relations=[
            {"id": 10, "source_service_code": "copieurs", "target_service_code": "services", "is_active": True},
            {"id": 11, "source_service_code": "utilisateurs", "target_service_code": "services", "is_active": True},
        ],
        relation_impacts={},
        relation_links=[
            {"relation_id": 10, "source_record_id": "copieur-1", "target_record_id": "service-culture"},
            {"relation_id": 11, "source_record_id": "agent-meurice", "target_record_id": "service-culture"},
        ],
        system_records_by_entity={
            "utilisateurs": [{"id": "agent-meurice", "label": "I.MEURICE", "status": "Actif"}],
            "services": [{"id": "service-culture", "label": "Culture"}],
        },
    )

    path = report["relation_inheritance_paths"][0]
    assert path["module_code"] == "copieurs"
    assert path["operational_filter"]["visible_values"] == ["En service"]
    assert path["record_paths"][0]["linked_services"] == [{"id": "service-culture", "label": "Culture", "status": "", "source": "", "synced_at": ""}]
    assert path["record_paths"][0]["inherited_agents"] == [{"id": "agent-meurice", "label": "I.MEURICE", "status": "Actif", "source": "", "synced_at": ""}]
