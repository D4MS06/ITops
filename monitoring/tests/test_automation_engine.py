from datetime import date

import pytest

from monitoring.services.automation_engine import (
    execute_rules,
    normalize_rules,
    normalize_validation_rules,
    validate_conditional_rules,
)


def test_creation_rule_runs_and_modifies_a_field():
    values = {"statut": "Nouveau"}
    actions = []
    results = execute_rules(
        normalize_rules([{"id": "creation", "trigger": {"type": "record_created"}, "actions": [{"type": "set_field", "field_key": "statut", "value": "En cours"}]}], [{"field_key": "statut"}]),
        event={"type": "record_created", "source": "manual"}, values=values,
        apply_action=lambda action: (values.update({action["field_key"]: action["value"]}) if action["type"] == "set_field" else None, actions.append(action)),
    )
    assert results[0].matched and values["statut"] == "En cours"


def test_field_change_conditions_and_email_keep_accents():
    delivered = []
    rules = normalize_rules([{
        "trigger": {"type": "field_changed", "field_key": "statut"},
        "conditions": [{"field_key": "montant", "operator": "greater_than", "value": "100"}],
        "actions": [{"type": "notify"}, {"type": "email", "template_type": "échéance"}],
    }], [{"field_key": "statut"}, {"field_key": "montant"}])
    results = execute_rules(rules, event={"type": "field_changed", "field_key": "statut"}, values={"statut": "Validé", "montant": "125"}, old_values={"statut": "Brouillon", "montant": "125"}, apply_action=delivered.append)
    assert results[0].matched and delivered[-1]["template_type"] == "échéance"


def test_unsatisfied_condition_and_automation_loop_do_not_run():
    rules = [{"trigger": {"type": "record_updated"}, "conditions": [{"field_key": "montant", "operator": "greater_than", "value": "10"}], "actions": [{"type": "notify"}]}]
    assert not execute_rules(rules, event={"type": "record_updated"}, values={"montant": "9"})[0].matched
    assert execute_rules(rules, event={"type": "record_updated", "source": "automation"}, values={"montant": "99"}) == []


def test_date_relation_and_threshold_triggers_are_supported():
    rules = normalize_rules([
        {"trigger": {"type": "date", "field_key": "echeance", "offset_days": -30}, "actions": [{"type": "notify"}]},
        {"trigger": {"type": "relation_created"}, "actions": [{"type": "add_relation", "relation_id": "2", "linked_record_id": "abc"}]},
        {"trigger": {"type": "threshold", "field_key": "montant", "operator": "greater_or_equal", "value": "10"}, "actions": [{"type": "notify"}]},
    ], [{"field_key": "echeance"}, {"field_key": "montant"}])
    assert execute_rules(rules[:1], event={"type": "scheduled"}, values={"echeance": "2026-09-19"}, today=date(2026, 8, 20))[0].matched
    assert execute_rules(rules[1:2], event={"type": "relation_created"}, values={})[0].matched
    assert execute_rules(rules[2:], event={"type": "record_updated"}, values={"montant": "10"})[0].matched


def test_date_trigger_does_not_overwrite_a_manual_record_update():
    rules = normalize_rules([{
        "trigger": {"type": "date", "field_key": "echeance", "offset_days": -30},
        "actions": [{"type": "set_field", "field_key": "statut", "value": "A renouveler"}],
    }], [{"field_key": "echeance"}, {"field_key": "statut"}])
    result = execute_rules(
        rules,
        event={"type": "field_changed", "field_key": "statut", "source": "manual"},
        values={"echeance": "2026-09-30", "statut": "Devis en attente"},
        old_values={"echeance": "2026-09-30", "statut": "A renouveler"},
        today=date(2026, 9, 3),
    )
    assert not result[0].matched


def test_document_linked_trigger_can_prepopulate_an_empty_date():
    rules = normalize_rules([{
        "trigger": {"type": "document_linked", "field_key": "devis"},
        "actions": [{"type": "set_field_from_event", "field_key": "date_reception_devis"}],
    }], [{"field_key": "devis"}, {"field_key": "date_reception_devis"}])
    values = {"date_reception_devis": ""}
    actions = []
    result = execute_rules(
        rules,
        event={"type": "document_linked", "field_key": "devis", "linked_at": "2026-09-03"},
        values=values,
        apply_action=actions.append,
    )
    assert result[0].matched
    assert actions == [{"type": "set_field_from_event", "field_key": "date_reception_devis", "event_value_key": "linked_at", "only_if_empty": True}]


def test_document_linked_trigger_requires_a_document_field():
    with pytest.raises(ValueError, match="cibler un champ"):
        normalize_rules(
            [{"trigger": {"type": "document_linked"}, "actions": [{"type": "notify"}]}],
            [{"field_key": "devis"}],
        )


def test_conditional_validation_requires_configured_field_only_when_matched():
    rules = normalize_validation_rules([{
        "condition": {"field_key": "mode_achat", "operator": "equals", "value": "Hors marché"},
        "required_field_keys": ["fournisseur_hors_marche"],
    }], [{"field_key": "mode_achat"}, {"field_key": "fournisseur_hors_marche"}])
    assert validate_conditional_rules(rules, {"mode_achat": "Via un marché"}) == []
    assert validate_conditional_rules(rules, {"mode_achat": "Hors marché"})
    assert validate_conditional_rules(rules, {"mode_achat": "Hors marché", "fournisseur_hors_marche": "Entreprise X"}) == []
