from types import SimpleNamespace

from monitoring.api.app import _apply_engagement_data_migration


def test_engagement_migration_promotes_cardinality_and_reuses_existing_links():
    class Logs:
        def __init__(self):
            self.relations = [
                {
                    "id": 39,
                    "source_service_code": "commandes_informatiques",
                    "target_service_code": "engagements",
                    "cardinality": "one_to_many",
                    "direction": "out",
                    "verb": "est rattache a",
                    "display_label": "Engagements",
                },
                {
                    "id": 32,
                    "source_service_code": "commandes_informatiques",
                    "target_service_code": "fournisseurs",
                    "cardinality": "many_to_one",
                    "direction": "out",
                },
            ]
            self.replacements = []
            self.records = []
            self.links = []

        def list_custom_services(self):
            return [{"code": "commandes_informatiques"}, {"code": "engagements"}]

        def list_custom_service_relations(self, *, service_code=None):
            assert service_code in {None, "commandes_informatiques"}
            return [dict(relation) for relation in self.relations]

        def replace_custom_service_relations(self, *, service_code, relations):
            assert service_code == "commandes_informatiques"
            self.replacements.append(relations)
            self.relations = [dict(relation) for relation in relations]
            return [dict(relation) for relation in self.relations]

        def save_custom_service_record(self, **kwargs):
            self.records.append(kwargs)

        def save_custom_service_record_relation_link(self, **kwargs):
            self.links.append(kwargs)

    logs = Logs()
    package = {
        "source_service_code": "commandes_informatiques",
        "target_service_code": "engagements",
        "records": [{"id": "engagement-1", "values": {"reference": "DEV-1"}}],
        "links": [
            {"source_record_id": "purchase-1", "target_record_id": "engagement-1"},
            {"source_record_id": "purchase-2", "target_record_id": "engagement-1"},
        ],
    }

    result = _apply_engagement_data_migration(
        logs,
        package,
        SimpleNamespace(include_records=True, include_relation_links=True),
        changed_by="test",
    )

    assert result["relations"] == 1
    assert result["records"] == 1
    assert result["relation_links"] == 2
    assert logs.replacements[0][0]["id"] == 39
    assert logs.replacements[0][0]["cardinality"] == "many_to_one"
    assert logs.replacements[0][1]["id"] == 32
    assert logs.replacements[0][1]["cardinality"] == "many_to_one"
    assert {link["record_id"] for link in logs.links} == {"purchase-1", "purchase-2"}
    assert {link["relation_id"] for link in logs.links} == {39}
