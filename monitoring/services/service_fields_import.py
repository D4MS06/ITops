from __future__ import annotations

import datetime as _dt
import ipaddress
from urllib.parse import urlparse

from monitoring.services.custom_service_schema import normalize_field_key, normalize_service_code, normalize_service_fields
from monitoring.services.tabular_mapping import normalize_column_mappings
from monitoring.services.tabular_io import HEADER_MODE_AUTO, parse_tabular_file, normalize_cell

_MAX_IMPORT_ROWS = 5000
_MAX_LIST_OPTIONS = 120
_FIELD_KIND_AUTO = "auto"
_SUPPORTED_FIELD_KINDS = frozenset({"text", "ip", "url", "date", "list"})


def infer_service_fields_from_file(
    *,
    filename: str,
    content_bytes: bytes,
    sheet_name: str = "",
    header_mode: str = HEADER_MODE_AUTO,
    header_row_number: int = 1,
    column_mappings: list[dict] | None = None,
) -> tuple[list[dict], int, int]:
    labels, rows = parse_tabular_file(
        filename=filename,
        content_bytes=content_bytes,
        max_rows=_MAX_IMPORT_ROWS,
        sheet_name=sheet_name,
        header_mode=header_mode,
        header_row_number=header_row_number,
    )
    return infer_service_fields_from_rows(labels=labels, rows=rows, column_mappings=column_mappings)


def infer_shared_list_items_from_file(
    *,
    filename: str,
    content_bytes: bytes,
    sheet_name: str = "",
    header_mode: str = HEADER_MODE_AUTO,
    header_row_number: int = 1,
) -> tuple[list[dict], int, int]:
    labels, rows = parse_tabular_file(
        filename=filename,
        content_bytes=content_bytes,
        max_rows=_MAX_IMPORT_ROWS,
        sheet_name=sheet_name,
        header_mode=header_mode,
        header_row_number=header_row_number,
    )
    return infer_shared_list_items_from_rows(labels=labels, rows=rows)


def infer_service_fields_from_rows(
    *,
    labels: list[str],
    rows: list[list[str]],
    column_mappings: list[dict] | None = None,
) -> tuple[list[dict], int, int]:
    inferred = _infer_fields(labels=labels, rows=rows, column_mappings=column_mappings)
    return normalize_service_fields(inferred), len(rows), len(labels)


def infer_shared_list_items_from_rows(*, labels: list[str], rows: list[list[str]]) -> tuple[list[dict], int, int]:
    items = _infer_shared_list_items(labels=labels, rows=rows)
    if not items:
        raise ValueError("Aucune valeur exploitable detectee.")
    return items, len(rows), len(labels)


def resolve_service_field_import_mapping(labels: list[str], column_mappings: list[dict] | None = None) -> list[dict[str, str]]:
    headers = [str(label or "").strip() for label in list(labels or [])]
    manual_by_source = {str(row.get("source_column") or "").strip(): row for row in normalize_column_mappings(column_mappings)}
    effective: list[dict[str, str]] = []
    for label in headers:
        manual = manual_by_source.get(label) or {}
        target = str(manual.get("target_field") or "").strip() or "__create_field__"
        custom_key = str(manual.get("custom_key") or "").strip()
        if target.lower() in {"ignore", "none", "__ignore__"}:
            target = "__ignore__"
        if target == "__auto__":
            target = "__create_field__"
        field_kind = _normalize_requested_field_kind(str(manual.get("field_kind") or ""))
        effective.append({"source_column": label, "target_field": target, "custom_key": custom_key, "field_kind": field_kind})
    return effective


def _infer_fields(*, labels: list[str], rows: list[list[str]], column_mappings: list[dict] | None = None) -> list[dict]:
    inferred: list[dict] = []
    seen_keys: set[str] = set()
    effective_mapping = resolve_service_field_import_mapping(labels, column_mappings)
    mapping_by_label = {str(row.get("source_column") or "").strip(): row for row in effective_mapping}
    for index, label in enumerate(labels):
        source_label = str(label or "").strip()
        mapping_row = mapping_by_label.get(source_label) or {}
        target_field = str(mapping_row.get("target_field") or "").strip()
        if target_field == "__ignore__":
            continue
        label_override = str(mapping_row.get("custom_key") or "").strip()
        values = []
        for row in rows:
            value = normalize_cell(row[index] if index < len(row) else "")
            if value:
                values.append(value)
        requested_kind = _normalize_requested_field_kind(str(mapping_row.get("field_kind") or ""))
        inferred_kind, inferred_options = _infer_kind_and_options(values)
        field_kind = inferred_kind if requested_kind == _FIELD_KIND_AUTO else requested_kind
        options = inferred_options if field_kind == "list" else []
        mapped_field_key = "" if target_field in {"", "__create_field__"} else target_field
        field_key = normalize_field_key(field_key=mapped_field_key, label=label_override or label, index=index)
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
                "label": label_override or label,
                "field_kind": field_kind,
                "required": False,
                "options": ",".join(options),
                "default_value": "",
                "sort_order": (index + 1) * 10,
            }
        )
    return inferred


def _normalize_requested_field_kind(value: str) -> str:
    kind = str(value or "").strip().lower()
    if not kind or kind in {"__auto__", "auto"}:
        return _FIELD_KIND_AUTO
    return kind if kind in _SUPPORTED_FIELD_KINDS else _FIELD_KIND_AUTO


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
