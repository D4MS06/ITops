"""Generic, side-effect free automation rule evaluator.

The API owns persistence and delivery.  Keeping the evaluator here makes the
rule contract usable by scheduled jobs, imports and the interactive portal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable


TRIGGER_ALIASES = {
    "creation": "record_created", "record_create": "record_created",
    "modification": "record_updated", "field_change": "field_changed",
    "relation_added": "relation_created", "relation_removed": "relation_deleted",
    "import": "import_completed", "sync": "synchronization_completed",
}
TRIGGER_TYPES = frozenset({
    "date", "record_created", "record_updated", "field_changed",
    "relation_created", "relation_deleted", "import_completed",
    "synchronization_completed", "inactivity", "threshold", "document_linked",
})
ACTION_TYPES = frozenset({"set_field", "set_field_from_event", "notify", "email", "create_task", "add_relation", "remove_relation"})


def _text(value: object) -> str:
    return str(value or "").strip()


def _number(value: object) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def normalize_rule(row: dict, fields_by_key: dict[str, dict] | None = None) -> dict:
    """Validate the portable trigger / conditions / actions format.

    Legacy ``date_field_key`` rules are deliberately accepted and converted at
    the boundary, so old module definitions keep working during migration.
    """
    source = dict(row or {})
    raw_trigger = dict(source.get("trigger") or {})
    trigger_type = _text(raw_trigger.get("type") or ("date" if source.get("date_field_key") else "")).lower()
    trigger_type = TRIGGER_ALIASES.get(trigger_type, trigger_type)
    if trigger_type not in TRIGGER_TYPES:
        raise ValueError("Type de declencheur d'automatisation inconnu.")
    field_key = _text(raw_trigger.get("field_key") or source.get("date_field_key"))
    if trigger_type in {"date", "field_changed", "threshold", "document_linked"} and not field_key:
        raise ValueError("Ce declencheur doit cibler un champ.")
    if fields_by_key and field_key and field_key not in fields_by_key:
        raise ValueError("Le declencheur doit cibler un champ du module.")
    offset_days = int(raw_trigger.get("offset_days", source.get("offset_days", 0)) or 0)
    if offset_days < -730 or offset_days > 730:
        raise ValueError("Le decalage d'automatisation doit etre compris entre -730 et 730 jours.")
    trigger = {"type": trigger_type, "field_key": field_key, "offset_days": offset_days}
    for key in ("value", "operator", "relation_id", "days"):
        if key in raw_trigger and _text(raw_trigger.get(key)):
            trigger[key] = raw_trigger[key]

    actions = list(source.get("actions") or [])
    if not actions and source.get("target_field_key"):
        actions = [{"type": "set_field", "field_key": source.get("target_field_key"), "value": source.get("target_value", "")}]
    normalized_actions = []
    for action in actions:
        item = dict(action or {})
        kind = _text(item.get("type")).lower()
        if kind not in ACTION_TYPES:
            raise ValueError("Type d'action d'automatisation inconnu.")
        if kind in {"set_field", "set_field_from_event"}:
            key = _text(item.get("field_key"))
            if not key or (fields_by_key and key not in fields_by_key):
                raise ValueError("L'action de mise a jour doit cibler un champ du module.")
            item["field_key"] = key
            if kind == "set_field_from_event":
                item["event_value_key"] = _text(item.get("event_value_key")) or "linked_at"
                item["only_if_empty"] = bool(item.get("only_if_empty", True))
        if kind in {"add_relation", "remove_relation"} and not _text(item.get("relation_id")):
            raise ValueError("L'action relationnelle doit indiquer la relation cible.")
        normalized_actions.append({key: value for key, value in item.items() if value is not None})
    if not normalized_actions:
        raise ValueError("Une automatisation doit contenir au moins une action.")
    conditions = []
    for condition in list(source.get("conditions") or []):
        item = dict(condition or {})
        key = _text(item.get("field_key"))
        operator = _text(item.get("operator") or "equals").lower()
        if not key or operator not in {"equals", "not_equals", "greater_than", "greater_or_equal", "less_than", "less_or_equal", "contains", "is_empty", "not_empty", "changed"}:
            raise ValueError("Condition d'automatisation invalide.")
        if fields_by_key and key not in fields_by_key:
            raise ValueError("Une condition doit cibler un champ du module.")
        conditions.append({"field_key": key, "operator": operator, "value": item.get("value", "")})
    return {"id": _text(source.get("id")), "enabled": bool(source.get("enabled", True)), "trigger": trigger, "conditions": conditions, "actions": normalized_actions}


def normalize_validation_rules(rows: list[dict] | None, fields: list[dict] | None = None) -> list[dict]:
    """Validate portable conditional required-field rules for custom records."""
    fields_by_key = {_text(field.get("field_key")): dict(field) for field in list(fields or []) if _text(field.get("field_key"))}
    output = []
    for index, row in enumerate(list(rows or [])):
        source = dict(row or {})
        condition = dict(source.get("condition") or {})
        field_key = _text(condition.get("field_key"))
        operator = _text(condition.get("operator") or "equals").lower()
        if not field_key or field_key not in fields_by_key:
            raise ValueError("La condition de validation doit cibler un champ du module.")
        if operator not in {"equals", "not_equals", "not_empty", "is_empty"}:
            raise ValueError("Operateur de validation conditionnelle invalide.")
        required_field_keys = list(dict.fromkeys(
            _text(value) for value in list(source.get("required_field_keys") or []) if _text(value)
        ))
        if not required_field_keys or any(key not in fields_by_key for key in required_field_keys):
            raise ValueError("Une validation conditionnelle doit exiger au moins un champ du module.")
        output.append({
            "id": _text(source.get("id")) or str(index + 1),
            "enabled": bool(source.get("enabled", True)),
            "condition": {"field_key": field_key, "operator": operator, "value": source.get("condition", {}).get("value", "")},
            "required_field_keys": required_field_keys,
            "message": _text(source.get("message")),
        })
    return output


def validate_conditional_rules(rules: list[dict] | None, values: dict) -> list[str]:
    errors = []
    for rule in list(rules or []):
        if not bool(rule.get("enabled", True)):
            continue
        condition = dict(rule.get("condition") or {})
        if not condition_matches(condition, values, {}):
            continue
        missing = [key for key in list(rule.get("required_field_keys") or []) if not _text(values.get(key))]
        if not missing:
            continue
        message = _text(rule.get("message"))
        errors.append(message or f"Champs requis selon la condition: {', '.join(missing)}.")
    return errors


def normalize_rules(rows: list[dict] | None, fields: list[dict] | None = None) -> list[dict]:
    fields_by_key = {_text(field.get("field_key")): dict(field) for field in list(fields or []) if _text(field.get("field_key"))}
    return [normalize_rule(dict(row or {}), fields_by_key) for row in list(rows or [])]


def condition_matches(condition: dict, values: dict, old_values: dict) -> bool:
    key, operator = _text(condition.get("field_key")), _text(condition.get("operator")).lower()
    current, expected = _text(values.get(key)), _text(condition.get("value"))
    if operator == "equals": return current == expected
    if operator == "not_equals": return current != expected
    if operator == "contains": return expected.lower() in current.lower()
    if operator == "is_empty": return not current
    if operator == "not_empty": return bool(current)
    if operator == "changed": return _text(old_values.get(key)) != current
    left, right = _number(current), _number(expected)
    if left is None or right is None: return False
    return {"greater_than": left > right, "greater_or_equal": left >= right, "less_than": left < right, "less_or_equal": left <= right}[operator]


def trigger_matches(trigger: dict, event: dict, values: dict, old_values: dict, today: date | None = None) -> bool:
    kind = _text(trigger.get("type")).lower()
    event_type = TRIGGER_ALIASES.get(_text(event.get("type")).lower(), _text(event.get("type")).lower())
    if kind in {"record_created", "record_updated", "field_changed", "relation_created", "relation_deleted", "import_completed", "synchronization_completed", "document_linked"}:
        if event_type != kind: return False
        field_key = _text(trigger.get("field_key"))
        relation_id = _text(trigger.get("relation_id"))
        return (not field_key or _text(event.get("field_key")) == field_key) and (not relation_id or relation_id == _text(event.get("relation_id")))
    if kind == "threshold":
        if event_type not in {"record_created", "record_updated", "field_changed", "import_completed", "synchronization_completed"}: return False
        left, right = _number(values.get(_text(trigger.get("field_key")))), _number(trigger.get("value"))
        if left is None or right is None: return False
        return {"greater_than": left > right, "greater_or_equal": left >= right, "less_than": left < right, "less_or_equal": left <= right}.get(_text(trigger.get("operator") or "greater_than"), False)
    now = today or date.today()
    if kind == "date":
        if event_type != "scheduled":
            return False
        try: return now >= datetime.strptime(_text(values.get(_text(trigger.get("field_key")))), "%Y-%m-%d").date() + timedelta(days=int(trigger.get("offset_days") or 0))
        except ValueError: return False
    if kind == "inactivity":
        try: changed = datetime.fromisoformat(_text(event.get("updated_at") or event.get("created_at"))).date()
        except ValueError: return False
        return now >= changed + timedelta(days=int(trigger.get("days") or trigger.get("offset_days") or 0))
    return False


@dataclass
class AutomationResult:
    rule_id: str
    matched: bool
    actions: list[dict] = field(default_factory=list)
    error: str = ""


def execute_rules(rules: list[dict], *, event: dict, values: dict, old_values: dict | None = None, apply_action: Callable[[dict], None] | None = None, today: date | None = None) -> list[AutomationResult]:
    """Evaluate rules once. Callers persist mutations and own transaction scope.

    Events emitted by an automation are ignored: this is the loop guard shared
    by interactive writes and scheduled runs.
    """
    if _text(event.get("source")).lower() == "automation": return []
    previous = dict(old_values or {})
    results = []
    for index, rule in enumerate(rules):
        item = normalize_rule(rule)
        rule_id = item["id"] or str(index + 1)
        matched = bool(item["enabled"]) and trigger_matches(item["trigger"], event, values, previous, today) and all(condition_matches(condition, values, previous) for condition in item["conditions"])
        result = AutomationResult(rule_id=rule_id, matched=matched)
        if matched:
            for action in item["actions"]:
                try:
                    if apply_action: apply_action(action)
                    result.actions.append(dict(action))
                except Exception as exc:  # action failures are journaled, not hidden
                    result.error = str(exc)
                    break
        results.append(result)
    return results
