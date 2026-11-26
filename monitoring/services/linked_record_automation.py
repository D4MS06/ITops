"""Apply a declarative field mapping within the source record transaction."""

import json

from monitoring.services.automation_engine import validate_conditional_rules
from monitoring.services.custom_service_schema import CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS, validate_record_values


def write_linked_record(store, *, source, record_id, values, action, authorize, actor, validate_only=False):
    relation_id = int(action["relation_id"])
    relation = next((r for r in store.list_custom_service_relations(service_code=source["code"])
                     if r["id"] == relation_id and r["source_service_code"] == source["code"]
                     and r.get("is_active") and r["cardinality"] in {"one_to_one", "many_to_one"}), None)
    if not relation:
        raise ValueError("Choisissez une relation sortante active à cible unique (un à un ou plusieurs à un).")
    code = relation["target_service_code"]
    authorize(code, "read")
    target = store.get_custom_service(code=code)
    if not target or not target["is_active"] or target.get("is_system") or target.get("is_technical") or code == source["code"]:
        raise ValueError("La relation doit cibler un autre module personnalisé actif.")
    existing = store.locked_linked_record(relation_id=relation_id, record_id=record_id, target_code=code)
    if not existing and not action.get("create_if_missing"):
        return
    current = existing["values"] if existing else {}
    guard = action.get("existing_field")
    source_keys = {f["field_key"] for f in source["fields"]} - set(CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS)
    target_keys = {f["field_key"] for f in target["fields"]} - set(CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS)
    if guard and guard not in target_keys:
        raise ValueError("Champ de condition cible indisponible.")
    if existing and guard and current.get(guard) not in action.get("existing_values", []):
        return
    changes = {}
    for key, spec in action["mapping"].items():
        if key not in target_keys or ("source" in spec and spec["source"] not in source_keys):
            raise ValueError("Le mappage contient un champ indisponible.")
        policy = spec.get("existing", "skip")
        if existing and (policy == "skip" or (policy == "empty" and current.get(key))):
            continue
        value = values.get(spec["source"], "") if "source" in spec else spec["constant"]
        if value != current.get(key):
            changes[key] = value
    if existing and not changes:
        return
    authorize(code, "update" if existing else "create")
    if not existing and any(r.get("required") and r.get("is_active") and r["source_service_code"] == code
                            for r in store.list_custom_service_relations(service_code=code)):
        raise ValueError("La fiche cible nécessite une autre relation obligatoire.")
    cleaned = validate_record_values(fields=target["fields"], values={**current, **changes}, fill_defaults=not existing)
    rules = target.get("validation_rules")
    if rules is None:
        rules = json.loads(target.get("treeview_config") or "{}").get("validation_rules", [])
    errors = validate_conditional_rules(rules, cleaned)
    if errors:
        raise ValueError(" ".join(errors))
    if validate_only:
        return
    updated = {**current, **{key: cleaned[key] for key in changes}} if existing else cleaned
    row = store.save_custom_service_record(service_code=code, record_id=existing["id"] if existing else "",
        values=updated, children=None, change_source="automation", changed_by=actor,
        sync_status=existing["sync_status"] if existing else "active")
    if not existing:
        store.save_custom_service_record_relation_link(service_code=source["code"], record_id=record_id,
            relation_id=relation_id, linked_record_id=row["id"], changed_by=actor)
