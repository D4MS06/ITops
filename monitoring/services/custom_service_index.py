from __future__ import annotations

from typing import Iterable


SENSITIVE_RECORD_KEYS = frozenset({"device_login", "device_password"})


def _clean_text(value: object, *, max_length: int | None = None) -> str:
    text = " ".join(str(value or "").strip().split())
    if max_length is not None and len(text) > max_length:
        return text[:max_length]
    return text


def _field_key(field: dict) -> str:
    return str((field or {}).get("field_key") or "").strip()


def _field_is_enabled(field: dict, flag_name: str) -> bool:
    return bool((field or {}).get(flag_name, True))


def _iter_field_values(*, fields: Iterable[dict], values: dict[str, object], flag_name: str) -> Iterable[tuple[str, str, str]]:
    seen: set[str] = set()
    for field in fields or []:
        key = _field_key(field)
        lowered_key = key.lower()
        if not key or lowered_key in seen or lowered_key in SENSITIVE_RECORD_KEYS:
            continue
        seen.add(lowered_key)
        if not _field_is_enabled(field, flag_name):
            continue
        value = _clean_text(values.get(key, ""))
        if value:
            yield key, _clean_text((field or {}).get("label") or key), value
    for key in sorted(str(raw_key or "") for raw_key in values.keys()):
        lowered_key = key.lower()
        if not key or lowered_key in seen or lowered_key in SENSITIVE_RECORD_KEYS:
            continue
        value = _clean_text(values.get(key, ""))
        if value:
            yield key, key, value


def build_record_index_payload(*, service: dict, record: dict) -> dict:
    values = dict((record or {}).get("values") or {})
    fields = list((service or {}).get("fields") or [])
    record_id = _clean_text((record or {}).get("id"))
    service_code = _clean_text((record or {}).get("service_code") or (service or {}).get("code"))

    label_value = ""
    for _key, _label, value in _iter_field_values(fields=fields, values=values, flag_name="show_in_list"):
        label_value = value
        break
    if not label_value:
        label_value = record_id

    blob_parts: list[str] = [_clean_text((service or {}).get("label") or service_code), label_value]
    for _key, label, value in _iter_field_values(fields=fields, values=values, flag_name="searchable"):
        blob_parts.extend([label, value])
    for child in list((record or {}).get("children") or []):
        child_name = _clean_text((child or {}).get("name"))
        child_code = _clean_text((child or {}).get("code"))
        if child_name:
            blob_parts.append(child_name)
        if child_code:
            blob_parts.append(child_code)

    return {
        "record_id": record_id,
        "service_code": service_code,
        "label_value": _clean_text(label_value, max_length=500),
        "search_blob": _clean_text(" ".join(part for part in blob_parts if part)),
    }


def upsert_record_index(*, manager, service: dict, record: dict) -> None:
    payload = build_record_index_payload(service=service, record=record)
    if not payload["record_id"] or not payload["service_code"]:
        return
    manager.upsert_custom_service_record_index(**payload)


def delete_record_index(*, manager, record_id: str) -> None:
    normalized = _clean_text(record_id)
    if normalized:
        manager.delete_custom_service_record_index(record_id=normalized)


def backfill_record_index(*, manager, batch_size: int = 100) -> int:
    safe_batch_size = max(1, int(batch_size or 100))
    indexed_count = 0
    while True:
        rows = list(manager.list_custom_service_records_missing_index(limit=safe_batch_size) or [])
        if not rows:
            return indexed_count
        services_by_code = {
            str(service.get("code") or "").strip().lower(): service
            for service in list(manager.list_custom_services() or [])
        }
        for row in rows:
            service_code = str(row.get("service_code") or "").strip().lower()
            service = services_by_code.get(service_code)
            if service is None:
                continue
            upsert_record_index(manager=manager, service=service, record=row)
            indexed_count += 1
        if len(rows) < safe_batch_size:
            return indexed_count
