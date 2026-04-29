from __future__ import annotations

import datetime as _dt
import ipaddress
from urllib.parse import urlparse

from monitoring.services.custom_service_schema import normalize_field_key, normalize_service_code, normalize_service_fields
from monitoring.services.tabular_io import parse_tabular_file, normalize_cell

_MAX_IMPORT_ROWS = 5000
_MAX_LIST_OPTIONS = 120


def infer_service_fields_from_file(*, filename: str, content_bytes: bytes) -> tuple[list[dict], int, int]:
    labels, rows = parse_tabular_file(filename=filename, content_bytes=content_bytes, max_rows=_MAX_IMPORT_ROWS)
    inferred = _infer_fields(labels=labels, rows=rows)
    return normalize_service_fields(inferred), len(rows), len(labels)


def infer_shared_list_items_from_file(*, filename: str, content_bytes: bytes) -> tuple[list[dict], int, int]:
    labels, rows = parse_tabular_file(filename=filename, content_bytes=content_bytes, max_rows=_MAX_IMPORT_ROWS)
    items = _infer_shared_list_items(labels=labels, rows=rows)
    if not items:
        raise ValueError("Aucune valeur exploitable detectee.")
    return items, len(rows), len(labels)


def _infer_fields(*, labels: list[str], rows: list[list[str]]) -> list[dict]:
    inferred: list[dict] = []
    seen_keys: set[str] = set()
    for index, label in enumerate(labels):
        values = []
        for row in rows:
            value = normalize_cell(row[index] if index < len(row) else "")
            if value:
                values.append(value)
        field_kind, options = _infer_kind_and_options(values)
        field_key = normalize_field_key(field_key="", label=label, index=index)
        if field_key in seen_keys:
            suffix = 2
            candidate = f"{field_key}_{suffix}"
            while candidate in seen_keys:
                suffix += 1
                candidate = f"{field_key}_{suffix}"
            field_key = candidate
        seen_keys.add(field_key)
        inferred.append(
            {
                "field_key": field_key,
                "label": label,
                "field_kind": field_kind,
                "required": False,
                "options": ",".join(options),
                "default_value": "",
                "sort_order": (index + 1) * 10,
            }
        )
    return inferred


def _infer_shared_list_items(*, labels: list[str], rows: list[list[str]]) -> list[dict]:
    normalized_labels = [str(label or "").strip().lower() for label in (labels or [])]
    code_index = next(
        (
            index
            for index, label in enumerate(normalized_labels)
            if any(token in label for token in ("code", "id", "key", "cle"))
        ),
        -1,
    )
    label_index = next(
        (
            index
            for index, label in enumerate(normalized_labels)
            if any(token in label for token in ("lib", "label", "nom", "valeur", "value", "designation"))
        ),
        -1,
    )
    if label_index < 0:
        label_index = 0
    if code_index == label_index:
        code_index = -1
    used_codes: set[str] = set()
    items: list[dict] = []
    for row_index, row in enumerate(rows or []):
        label_value = normalize_cell(row[label_index] if label_index < len(row or []) else "")
        code_value = normalize_cell(row[code_index] if code_index >= 0 and code_index < len(row or []) else "")
        if not label_value and not code_value:
            continue
        label = label_value or code_value
        code = normalize_service_code(code=code_value, label=label)
        if code in used_codes:
            suffix = 2
            candidate = f"{code}_{suffix}"
            while candidate in used_codes:
                suffix += 1
                candidate = f"{code}_{suffix}"
            code = candidate
        used_codes.add(code)
        items.append(
            {
                "code": code,
                "label": label,
                "is_active": True,
                "sort_order": (len(items) + 1) * 10,
            }
        )
        if row_index >= _MAX_IMPORT_ROWS:
            break
    return items


def _infer_kind_and_options(values: list[str]) -> tuple[str, list[str]]:
    if not values:
        return "text", []
    unique_values: list[str] = []
    seen_values: set[str] = set()
    for value in values:
        key = value.lower()
        if key in seen_values:
            continue
        seen_values.add(key)
        unique_values.append(value)
    has_duplicates = len(unique_values) < len(values)
    if has_duplicates and 2 <= len(unique_values) <= _MAX_LIST_OPTIONS:
        return "list", unique_values
    if all(_is_ip(value) for value in values):
        return "ip", []
    if all(_is_iso_date(value) for value in values):
        return "date", []
    if all(_is_url(value) for value in values):
        return "url", []
    return "text", []


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(str(value or "").strip())
        return True
    except ValueError:
        return False


def _is_iso_date(value: str) -> bool:
    try:
        _dt.date.fromisoformat(str(value or "").strip())
        return True
    except ValueError:
        return False


def _is_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    return bool(parsed.scheme and parsed.netloc)
