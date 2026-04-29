from __future__ import annotations

import re

from monitoring.services.tabular_io import (
    MAX_TABULAR_ROWS,
    encode_csv_bytes,
    normalize_cell,
    normalize_header_key,
    parse_tabular_file,
    rows_as_dicts,
)

_RECORD_ID_TOKENS = {"record_id", "id", "fiche_id", "item_id"}
_CHILD_NAMES_TOKENS = {
    "children_names",
    "child_names",
    "linked_names",
    "elements_lies_noms",
    "elements_lies_names",
}
_CHILD_CODES_TOKENS = {
    "children_codes",
    "child_codes",
    "linked_codes",
    "elements_lies_codes",
}
_CHILD_COMBINED_TOKENS = {"children", "elements_lies", "linked_items"}


def infer_custom_service_records_from_file(
    *,
    filename: str,
    content_bytes: bytes,
    fields: list[dict],
    child_enabled: bool = False,
) -> tuple[list[dict], int, int, list[str]]:
    headers, rows = parse_tabular_file(filename=filename, content_bytes=content_bytes, max_rows=MAX_TABULAR_ROWS)
    row_maps = rows_as_dicts(headers=headers, rows=rows)
    header_lookup = {normalize_header_key(label): str(label or "") for label in list(headers or [])}
    field_column_by_key = _resolve_field_columns(fields=fields, header_lookup=header_lookup)
    record_id_header = _first_header_for_tokens(header_lookup, _RECORD_ID_TOKENS)
    child_names_header = _first_header_for_tokens(header_lookup, _CHILD_NAMES_TOKENS)
    child_codes_header = _first_header_for_tokens(header_lookup, _CHILD_CODES_TOKENS)
    child_combined_header = _first_header_for_tokens(header_lookup, _CHILD_COMBINED_TOKENS)

    parsed_rows: list[dict] = []
    issues: list[str] = []
    for row_index, row in enumerate(row_maps, start=2):
        values: dict[str, str] = {}
        for field in list(fields or []):
            key = str(field.get("field_key") or "").strip()
            if not key:
                continue
            column = field_column_by_key.get(key, "")
            values[key] = normalize_cell(row.get(column, "")) if column else ""

        children: list[dict] = []
        if child_enabled:
            names_raw = normalize_cell(row.get(child_names_header, "")) if child_names_header else ""
            codes_raw = normalize_cell(row.get(child_codes_header, "")) if child_codes_header else ""
            combined_raw = normalize_cell(row.get(child_combined_header, "")) if child_combined_header else ""
            if combined_raw:
                children.extend(_parse_combined_children(combined_raw))
            if names_raw or codes_raw:
                children.extend(_parse_names_codes_children(names_raw, codes_raw))

        record_id = normalize_cell(row.get(record_id_header, "")) if record_id_header else ""
        has_values = any(normalize_cell(item) for item in values.values())
        has_children = any(normalize_cell(item.get("name")) or normalize_cell(item.get("code")) for item in children)
        if not has_values and not has_children and not record_id:
            issues.append(f"Ligne {row_index}: vide, ignoree.")
            continue
        parsed_rows.append(
            {
                "record_id": record_id,
                "values": values,
                "children": children,
            }
        )
    if not parsed_rows and issues:
        raise ValueError(f"Aucune ligne exploitable. {issues[0]}")
    return parsed_rows, len(rows), len(headers), issues


def export_custom_service_records_to_csv(*, service: dict, rows: list[dict]) -> bytes:
    fields = list(service.get("fields") or [])
    field_headers = _build_export_field_headers(fields)
    child_enabled = bool(service.get("child_enabled", False))
    child_label = str(service.get("child_label") or "elements_lies").strip() or "elements_lies"
    child_base = normalize_header_key(child_label) or "elements_lies"
    child_names_header = f"{child_base}_noms"
    child_codes_header = f"{child_base}_codes"
    headers = ["record_id", *[header for _field_key, header in field_headers]]
    if child_enabled:
        headers.extend([child_names_header, child_codes_header])

    export_rows: list[dict[str, object]] = []
    for row in list(rows or []):
        values = dict(row.get("values") or {})
        payload: dict[str, object] = {
            "record_id": str(row.get("id") or ""),
        }
        for field_key, header in field_headers:
            payload[header] = normalize_cell(values.get(field_key, ""))
        if child_enabled:
            children = list(row.get("children") or [])
            payload[child_names_header] = "|".join(
                normalize_cell(child.get("name", ""))
                for child in children
                if normalize_cell(child.get("name", ""))
            )
            payload[child_codes_header] = "|".join(
                normalize_cell(child.get("code", ""))
                for child in children
                if normalize_cell(child.get("code", ""))
            )
        export_rows.append(payload)
    return encode_csv_bytes(headers=headers, rows=export_rows)


def _resolve_field_columns(*, fields: list[dict], header_lookup: dict[str, str]) -> dict[str, str]:
    by_key: dict[str, str] = {}
    for field in list(fields or []):
        field_key = str(field.get("field_key") or "").strip()
        label = str(field.get("label") or field_key).strip()
        if not field_key:
            continue
        aliases = {
            normalize_header_key(field_key),
            normalize_header_key(label),
        }
        aliases = {item for item in aliases if item}
        matched = ""
        for alias in aliases:
            if alias in header_lookup:
                matched = header_lookup[alias]
                break
        by_key[field_key] = matched
    return by_key


def _first_header_for_tokens(header_lookup: dict[str, str], tokens: set[str]) -> str:
    for token in list(tokens or []):
        if token in header_lookup:
            return header_lookup[token]
    return ""


def _build_export_field_headers(fields: list[dict]) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    seen_headers: set[str] = set()
    for field in list(fields or []):
        field_key = str(field.get("field_key") or "").strip()
        label = normalize_cell(field.get("label") or field_key)
        if not field_key:
            continue
        base = label or field_key
        candidate = base
        suffix = 2
        lowered = candidate.lower()
        while lowered in seen_headers:
            candidate = f"{base}_{suffix}"
            lowered = candidate.lower()
            suffix += 1
        seen_headers.add(lowered)
        output.append((field_key, candidate))
    return output


def _split_collection(value: str) -> list[str]:
    parts = [normalize_cell(item) for item in re.split(r"[|\n\r;,]+", str(value or ""))]
    return [item for item in parts if item]


def _parse_names_codes_children(names_raw: str, codes_raw: str) -> list[dict]:
    names = _split_collection(names_raw)
    codes = _split_collection(codes_raw)
    if not names and not codes:
        return []
    size = max(len(names), len(codes))
    rows: list[dict] = []
    for index in range(size):
        name = names[index] if index < len(names) else ""
        code = codes[index] if index < len(codes) else ""
        if not name and not code:
            continue
        rows.append(
            {
                "name": name,
                "code": code,
                "sort_order": (index + 1) * 10,
            }
        )
    return rows


def _parse_combined_children(raw: str) -> list[dict]:
    output: list[dict] = []
    chunks = _split_collection(raw)
    for index, chunk in enumerate(chunks):
        text = normalize_cell(chunk)
        if not text:
            continue
        if ":" in text:
            left, right = text.split(":", 1)
        elif "=" in text:
            left, right = text.split("=", 1)
        elif "/" in text:
            left, right = text.split("/", 1)
        else:
            left, right = text, ""
        name = normalize_cell(left)
        code = normalize_cell(right)
        if not name and not code:
            continue
        output.append(
            {
                "name": name,
                "code": code,
                "sort_order": (index + 1) * 10,
            }
        )
    return output
