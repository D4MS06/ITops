"""Install the approved quote workflow on its No-Code definition (python -m scripts.configure_devis_automations)."""

import json

from monitoring.services.automation_engine import normalize_rules, normalize_validation_rules
from monitoring.storage.mariadb_manager import MariaDBFileManager


def quote_rules(relation_id):
    def rule(key, event, conditions, actions):
        trigger = {"type": event}
        if event == "document_linked":
            trigger["field_key"] = "reference_devis"
        return {"id": key, "enabled": True, "trigger": trigger, "conditions": conditions, "actions": actions}

    def condition(field, value, operator="equals"):
        return {"field_key": field, "operator": operator, "value": value}

    def status(value):
        return {"type": "set_field", "field_key": "statut", "value": value}

    def date(field, event_key):
        return {"type": "set_field_from_event", "field_key": field, "event_value_key": event_key, "only_if_empty": True}

    def order(create, states, mapping):
        return {"type": "write_linked_record", "relation_id": str(relation_id), "create_if_missing": create,
                "existing_field": "statut", "existing_values": states, "mapping": mapping}

    sent = {"date_demande_devis": {"source": "date_envoi", "existing": "empty"},
            "statut": {"constant": "Demande de devis", "existing": "replace"}}
    received = {key: {"source": key} for key in ("objet", "categorie", "priorite", "mode_achat")}
    received.update(date_demande_devis={"source": "date_envoi", "existing": "empty"},
                    date_reception_devis={"source": "date_reception_devis", "existing": "empty"},
                    statut={"constant": "Devis reçu", "existing": "replace"})
    active = [condition("statut", "Annulée", "not_equals")]
    return [
        rule("devis_brouillon", "mail_prepared", [condition("statut", "Brouillon")], [status("À valider")]),
        rule("devis_date_envoi", "mail_sent", active, [date("date_envoi", "sent_at")]),
        rule("devis_en_attente", "mail_sent", active + [condition("statut", "Devis reçu", "not_equals")],
             [status("En attente du devis"), order(False, ["Brouillon"], sent)]),
        rule("reception_devis_date", "document_linked", active, [date("date_reception_devis", "linked_at"), status("Devis reçu")]),
        rule("devis_commande", "document_linked", active + [condition("suite_demande", "Circuit d'achat")],
             [order(True, ["Brouillon", "Demande de devis"], received)]),
        rule("devis_information_suivi", "document_linked", active + [condition("suite_demande", "Suivi uniquement")],
             [{"type": "show_information", "value": "Le devis a été enregistré. Cette demande est en « Suivi uniquement ». Aucune commande ne sera créée à la réception de ce devis."}]),
    ]


def quote_validation_rules():
    message = "Envoyez la demande de devis avant d’enregistrer sa réception ou de rattacher le devis. La date d’envoi doit être renseignée."
    return [
        {"id": "devis_reception_apres_envoi", "enabled": True,
         "condition": {"field_key": "date_reception_devis", "operator": "not_empty"},
         "required_field_keys": ["date_envoi"], "message": message},
        {"id": "devis_statut_recu_apres_envoi", "enabled": True,
         "condition": {"field_key": "statut", "operator": "equals", "value": "Devis reçu"},
         "required_field_keys": ["date_envoi"], "message": message},
    ]


def install():
    manager = MariaDBFileManager()
    code = "demandes_de_devis"
    service = manager.get_custom_service(code=code)
    relations = [r for r in manager.list_custom_service_relations(service_code=code)
                 if r["source_service_code"] == code and r["target_service_code"] == "commandes_informatiques"
                 and r["cardinality"] == "one_to_one" and r["is_active"]]
    if not service or len(relations) != 1:
        raise ValueError("La demande et sa relation unique vers Commandes doivent être configurées.")
    rules = normalize_rules(quote_rules(relations[0]["id"]), service["fields"])
    managed = {rule["id"] for rule in rules}
    validation_rules = normalize_validation_rules(quote_validation_rules(), service["fields"])
    managed_validations = {rule["id"] for rule in validation_rules}
    with manager._connect() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT treeview_config FROM custom_services WHERE code=%s FOR UPDATE", (code,))
        config = json.loads(cursor.fetchone()[0] or "{}")
        previous = config.get("automation_rules", [])
        config["automation_rules"] = [rule for rule in previous if rule.get("id") not in managed] + rules
        previous_validations = config.get("validation_rules", [])
        config["validation_rules"] = [rule for rule in previous_validations if rule.get("id") not in managed_validations] + validation_rules
        if config["automation_rules"] != previous or config["validation_rules"] != previous_validations:
            cursor.execute("UPDATE custom_services SET treeview_config=%s, updated_at=UTC_TIMESTAMP() WHERE code=%s",
                           (json.dumps(config, ensure_ascii=False), code))
        conn.commit()
    print(f"{len(rules)} règles configurées pour {code}.")


if __name__ == "__main__":
    install()
