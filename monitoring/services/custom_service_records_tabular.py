from __future__ import annotations

import re

from monitoring.services.tabular_io import (
    HEADER_MODE_AUTO,
    MAX_TABULAR_ROWS,
    encode_csv_bytes,
    normalize_cell,
    normalize_header_key,
    parse_tabular_file,
    rows_as_dicts,
)
from monitoring.services.tabular_mapping import IGNORE_TARGETS, MappingTarget, normalize_column_mappings, normalize_manual_column_mapping

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
_LOGIN_HEADER_TOKENS = {
    "device_login",
    "login",
    "username",
    "identifiant",
    "user",
}
_PASSWORD_HEADER_TOKENS = {
    "device_password",
    "password",
    "motdepasse",
    "mot_de_passe",
    "pass",
    "mdp",
}
_RESERVED_HEADER_TOKENS = (
    _RECORD_ID_TOKENS
    | _CHILD_NAMES_TOKENS
    | _CHILD_CODES_TOKENS
    | _CHILD_COMBINED_TOKENS
    | _LOGIN_HEADER_TOKENS
    | _PASSWORD_HEADER_TOKENS
)
_CREDENTIAL_LOGIN_KEY = "device_login"
_CREDENTIAL_PASSWORD_KEY = "device_password"


def infer_custom_service_records_from_file(
    *,
    filename: str,
    content_bytes: bytes,
    sheet_name: str = "",
    header_mode: str = HEADER_MODE_AUTO,
    header_row_number: int = 1,
    column_mappings: list[dict] | None = None,
    fields: list[dict],
    child_enabled: bool = False,
    credentials_enabled: bool = False,
    include_source_values: bool = False,
) -> tuple[list[dict], int, int, list[str]]:
    headers, rows = parse_tabular_file(
        filename=filename,
        content_bytes=content_bytes,
        max_rows=MAX_TABULAR_ROWS,
        sheet_name=sheet_name,
        header_mode=header_mode,
        header_row_number=header_row_number,
    )
    return infer_custom_service_records_from_rows(
        headers=headers,
        rows=rows,
        fields=fields,
        column_mappings=column_mappings,
        child_enabled=child_enabled,
        credentials_enabled=credentials_enabled,
        include_source_values=include_source_values,
    )


def infer_custom_service_records_from_rows(
    *,
    headers: list[str],
    rows: list[list[str]],
    fields: list[dict],
    column_mappings: list[dict] | None = None,
    child_enabled: bool = False,
    credentials_enabled: bool = False,
    include_source_values: bool = False,
) -> tuple[list[dict], int, int, list[str]]:
    row_maps = rows_as_dicts(headers=headers, rows=rows)
    header_lookup = {normalize_header_key(label): str(label or "") for label in list(headers or [])}
    issues: list[str] = []
    field_column_by_key = _resolve_field_columns(
        fields=fields,
        header_lookup=header_lookup,
        column_mappings=column_mappings,
        issues=issues,
    )
    record_id_header = _first_header_for_tokens(header_lookup, _RECORD_ID_TOKENS)
    child_names_header = _first_header_for_tokens(header_lookup, _CHILD_NAMES_TOKENS)
    child_codes_header = _first_header_for_tokens(header_lookup, _CHILD_CODES_TOKENS)
    child_combined_header = _first_header_for_tokens(header_lookup, _CHILD_COMBINED_TOKENS)
    credential_login_header = _resolve_credential_column(
        headers=headers,
        header_lookup=header_lookup,
        column_mappings=column_mappings,
        target_field=_CREDENTIAL_LOGIN_KEY,
        automatic_tokens=_LOGIN_HEADER_TOKENS,
    ) if credentials_enabled else ""
    credential_password_header = _resolve_credential_column(
        headers=headers,
        header_lookup=header_lookup,
        column_mappings=column_mappings,
        target_field=_CREDENTIAL_PASSWORD_KEY,
        automatic_tokens=_PASSWORD_HEADER_TOKENS,
    ) if credentials_enabled else ""
    credential_headers = {
        header
        for header in (credential_login_header, credential_password_header)
        if header
    }

    parsed_rows: list[dict] = []
    _apply_position_fallback_mapping(
        fields=fields,
        headers=headers,
        field_column_by_key=field_column_by_key,
        ignored_headers=set(
            row["source_column"]
            for row in normalize_column_mappings(column_mappings)
            if normalize_header_key(row.get("target_field")) in IGNORE_TARGETS
        ) | credential_headers,
        issues=issues,
    )
    for row_index, row in enumerate(row_maps, start=2):
        values: dict[str, str] = {}
        for field in list(fields or []):
            key = str(field.get("field_key") or "").strip()
            if not key:
                continue
            column = field_column_by_key.get(key, "")
            if column:
                values[key] = normalize_cell(row.get(column, ""))
        if credentials_enabled and credential_login_header:
            values[_CREDENTIAL_LOGIN_KEY] = normalize_cell(row.get(credential_login_header, ""))
        if credentials_enabled and credential_password_header:
            values[_CREDENTIAL_PASSWORD_KEY] = normalize_cell(row.get(credential_password_header, ""))

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
        parsed_row = {
            "record_id": record_id,
            "values": values,
            "children": children,
            "_row_index": row_index,
        }
        if include_source_values:
            parsed_row["source_values"] = {str(key): normalize_cell(value) for key, value in row.items()}
        parsed_rows.append(parsed_row)
    if not parsed_rows:
        matched_headers = sorted(str(value or "") for value in field_column_by_key.values() if str(value or "").strip())
        if not matched_headers:
            expected = ", ".join(
                str((field or {}).get("label") or (field or {}).get("field_key") or "").strip()
                for field in list(fields or [])
                if str((field or {}).get("label") or (field or {}).get("field_key") or "").strip()
            )
            detected = ", ".join(str(header or "").strip() for header in list(headers or []) if str(header or "").strip())
            raise ValueError(
                "Aucune ligne exploitable. Aucune colonne du fichier ne correspond aux champs du service."
                f" Champs attendus: {expected or '-'}."
                f" Entetes detectees: {detected or '-'}."
            )
        if issues:
            raise ValueError(f"Aucune ligne exploitable. {issues[0]}")
    return parsed_rows, len(rows), len(headers), issues


def export_custom_service_records_to_csv(*, service: dict, rows: list[dict]) -> bytes:
    fields = list(service.get("fields") or [])
    field_headers = _build_export_field_headers(fields)
    credentials_enabled = bool(service.get("credentials_enabled", False))
    child_enabled = bool(service.get("child_enabled", False))
    child_label = str(service.get("child_label") or "elements_lies").strip() or "elements_lies"
    child_base = normalize_header_key(child_label) or "elements_lies"
    child_names_header = f"{child_base}_noms"
    child_codes_header = f"{child_base}_codes"
    headers = ["record_id", *[header for _field_key, header in field_headers]]
    if credentials_enabled:
        headers.extend([_CREDENTIAL_LOGIN_KEY, _CREDENTIAL_PASSWORD_KEY])
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
        if credentials_enabled:
            payload[_CREDENTIAL_LOGIN_KEY] = normalize_cell(values.get(_CREDENTIAL_LOGIN_KEY, ""))
            payload[_CREDENTIAL_PASSWORD_KEY] = normalize_cell(values.get(_CREDENTIAL_PASSWORD_KEY, ""))
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


def resolve_effective_record_column_mapping(
    *,
    headers: list[str],
    fields: list[dict],
    column_mappings: list[dict] | None = None,
    credentials_enabled: bool = False,
) -> list[dict[str, str]]:
    header_lookup = {normalize_header_key(label): str(label or "") for label in list(headers or [])}
    issues: list[str] = []
    field_column_by_key = _resolve_field_columns(
        fields=fields,
        header_lookup=header_lookup,
        column_mappings=column_mappings,
        issues=issues,
    )
    credential_columns: dict[str, str] = {}
    if credentials_enabled:
        for target_field, automatic_tokens in (
            (_CREDENTIAL_LOGIN_KEY, _LOGIN_HEADER_TOKENS),
            (_CREDENTIAL_PASSWORD_KEY, _PASSWORD_HEADER_TOKENS),
        ):
            source_header = _resolve_credential_column(
                headers=headers,
                header_lookup=header_lookup,
                column_mappings=column_mappings,
                target_field=target_field,
                automatic_tokens=automatic_tokens,
            )
            if source_header:
                credential_columns[target_field] = source_header
    _apply_position_fallback_mapping(
        fields=fields,
        headers=headers,
        field_column_by_key=field_column_by_key,
        ignored_headers=set(
            row["source_column"]
            for row in normalize_column_mappings(column_mappings)
            if normalize_header_key(row.get("target_field")) in IGNORE_TARGETS
        ) | set(credential_columns.values()),
        issues=issues,
    )
    field_by_header = {
        str(column or ""): str(field_key or "")
        for field_key, column in field_column_by_key.items()
        if str(column or "").strip() and str(field_key or "").strip()
    }
    for target_field, source_header in credential_columns.items():
        field_by_header[source_header] = target_field
    output: list[dict[str, str]] = []
    for header in list(headers or []):
        source_column = str(header or "")
        output.append(
            {
                "source_column": source_column,
                "target_field": field_by_header.get(source_column, "__ignore__"),
                "custom_key": "",
            }
        )
    return output


def _resolve_field_columns(
    *,
    fields: list[dict],
    header_lookup: dict[str, str],
    column_mappings: list[dict] | None = None,
    issues: list[str] | None = None,
) -> dict[str, str]:
    by_key: dict[str, str] = {}
    fields_by_token: dict[str, str] = {}
    for field in list(fields or []):
        field_key = str(field.get("field_key") or "").strip()
        label = str(field.get("label") or field_key).strip()
        if not field_key:
            continue
        for token in {normalize_header_key(field_key), normalize_header_key(label)}:
            if token:
                fields_by_token[token] = field_key
    manual_by_header = normalize_manual_column_mapping(
        column_mappings,
        resolve_target=lambda target_field, _custom_key: _resolve_record_manual_mapping(
            target_field=target_field,
            fields_by_token=fields_by_token,
        ),
    )
    ignored_headers = {
        header
        for header, target in manual_by_header.items()
        if target.kind == "ignore"
    }
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
            if alias in header_lookup and header_lookup[alias] not in ignored_headers:
                matched = header_lookup[alias]
                break
        by_key[field_key] = matched
    manual_count = 0
    for source_column, target in manual_by_header.items():
        if target.kind == "ignore":
            continue
        source_header = header_lookup.get(normalize_header_key(source_column), "")
        if not source_header:
            continue
        if by_key.get(target.key) != source_header:
            manual_count += 1
        by_key[target.key] = source_header
    if manual_count and issues is not None:
        issues.append("Mapping manuel applique.")
    return by_key


def _resolve_credential_column(
    *,
    headers: list[str],
    header_lookup: dict[str, str],
    column_mappings: list[dict] | None,
    target_field: str,
    automatic_tokens: set[str],
) -> str:
    """Resolve a credential column, preferring an explicit import mapping."""
    normalized_target = normalize_header_key(target_field)
    ignored_headers: set[str] = set()
    for mapping in normalize_column_mappings(column_mappings):
        source_header = header_lookup.get(normalize_header_key(mapping.get("source_column")), "")
        if not source_header:
            continue
        mapped_target = normalize_header_key(mapping.get("target_field"))
        if mapped_target == normalized_target:
            return source_header
        if mapped_target in IGNORE_TARGETS:
            ignored_headers.add(source_header)
    return next(
        (
            header_lookup[token]
            for token in automatic_tokens
            if token in header_lookup and header_lookup[token] not in ignored_headers
        ),
        "",
    )


def _resolve_record_manual_mapping(
    *,
    target_field: str,
    fields_by_token: dict[str, str],
) -> MappingTarget | None:
    field_key = fields_by_token.get(normalize_header_key(target_field), "")
    if not field_key:
        return None
    return MappingTarget("field", field_key)


def _apply_position_fallback_mapping(
    *,
    fields: list[dict],
    headers: list[str],
    field_column_by_key: dict[str, str],
    ignored_headers: set[str] | None = None,
    issues: list[str],
) -> None:
    ignored = {str(item or "").strip() for item in set(ignored_headers or set()) if str(item or "").strip()}
    already_mapped = {
        str(column or "").strip()
        for column in field_column_by_key.values()
        if str(column or "").strip()
    }
    usable_headers = [
        str(header or "").strip()
        for header in list(headers or [])
        if str(header or "").strip()
        and normalize_header_key(header) not in _RESERVED_HEADER_TOKENS
        and str(header or "").strip() not in ignored
        and str(header or "").strip() not in already_mapped
    ]
    if not usable_headers:
        return
    usable_fields = [
        field
        for field in list(fields or [])
        if str((field or {}).get("field_key") or "").strip()
        and not str(field_column_by_key.get(str((field or {}).get("field_key") or "").strip()) or "").strip()
    ]
    for field, header in zip(usable_fields, usable_headers):
        field_column_by_key[str(field.get("field_key") or "").strip()] = header
    if usable_fields:
        if already_mapped:
            issues.append("Certaines colonnes sans correspondance exacte ont ete mappees par position.")
        else:
            issues.append("Aucune correspondance exacte d'entete: colonnes mappees par position.")


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
