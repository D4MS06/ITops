from __future__ import annotations


def build_field_history_events(
    *,
    fields: list[dict],
    old_values: dict[str, object] | None,
    new_values: dict[str, object] | None,
) -> list[dict[str, str]]:
    old_source = old_values if isinstance(old_values, dict) else {}
    new_source = new_values if isinstance(new_values, dict) else {}
    events: list[dict[str, str]] = []
    for field in list(fields or []):
        if not bool((field or {}).get("track_history", False)):
            continue
        field_key = str((field or {}).get("field_key") or "").strip()
        if not field_key:
            continue
        old_value = str(old_source.get(field_key) or "")
        new_value = str(new_source.get(field_key) or "")
        if old_value == new_value:
            continue
        events.append(
            {
                "field_key": field_key,
                "old_value": old_value,
                "new_value": new_value,
            }
        )
    return events
