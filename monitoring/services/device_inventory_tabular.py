from __future__ import annotations

from monitoring.services.tabular_io import (
    MAX_TABULAR_ROWS,
    encode_csv_bytes,
    normalize_cell,
    normalize_header_key,
    parse_tabular_file,
)

_BASE_EXPORT_HEADERS = [
    "device_type",
    "name",
    "ip",
    "description",
    "id_Teamviewer",
    "device_subtype",
    "action_double_click",
    "web_url",
    "ssh_user",
    "device_login",
    "notify",
]

_HEADER_ALIASES = {
    "device_type": {
        "device_type",
        "device type",
        "type_equipement",
        "type equipement",
        "equipement_type",
        "type",
        "categorie",
    },
    "name": {
        "name",
        "nom",
        "hostname",
        "device_name",
        "nom_equipement",
    },
    "ip": {
        "ip",
        "adresse ip",
        "adresse_ip",
        "ip_address",
        "ip address",
    },
    "description": {
        "description",
        "desc",
        "commentaire",
        "notes",
    },
    "id_Teamviewer": {
        "id_teamviewer",
        "teamviewer",
        "teamviewer_id",
        "id teamviewer",
    },
    "device_subtype": {
        "device_subtype",
        "sous_type",
        "sous-type",
        "sous type",
        "subtype",
        "os",
    },
    "action_double_click": {
        "action_double_click",
        "action_double_clic",
        "action_defaut",
        "remote_action",
    },
    "web_url": {
        "web_url",
        "url",
        "web",
        "http_url",
    },
    "ssh_user": {
        "ssh_user",
        "ssh",
        "ssh_login",
        "ssh username",
    },
    "device_login": {
        "device_login",
        "login",
        "username",
        "identifiant",
    },
    "device_password": {
        "device_password",
        "password",
        "motdepasse",
        "mot_de_passe",
    },
    "notify": {
        "notify",
        "notification",
        "notifications",
        "alerte",
    },
}


def infer_devices_from_file(
    *,
    filename: str,
    content_bytes: bytes,
    default_device_type: str = "",
    allowed_device_types: set[str] | None = None,
    column_mappings: list[dict] | None = None,
    fail_on_empty: bool = True,
) -> tuple[list[dict], int, int, list[str]]:
    headers, raw_rows = parse_tabular_file(filename=filename, content_bytes=content_bytes, max_rows=MAX_TABULAR_ROWS)
    normalized_default_type = normalize_cell(default_device_type).lower()
    allowed_types = {str(item or "").strip().lower() for item in (allowed_device_types or set()) if str(item or "").strip()}
    mapping = _resolve_column_mapping(headers, column_mappings=column_mappings)
    rows: list[dict] = []
    issues: list[str] = []
    for row_index, row in enumerate(list(raw_rows or []), start=2):
        parsed = _parse_single_device_row(
            row=row,
            headers=headers,
            mapping=mapping,
            default_device_type=normalized_default_type,
            allowed_device_types=allowed_types,
        )
        if parsed is None:
            issues.append(f"Ligne {row_index}: donnees insuffisantes ou type invalide.")
            continue
        rows.append(parsed)
    if fail_on_empty and not rows and issues:
        raise ValueError(f"Aucune ligne exploitable. {issues[0]}")
    return rows, len(raw_rows), len(headers), issues


def export_devices_to_csv(*, rows: list[dict]) -> bytes:
    custom_keys: set[str] = set()
    for row in list(rows or []):
        custom_data = dict((row or {}).get("custom_data") or {})
        for key in custom_data.keys():
            normalized = normalize_cell(key)
            if normalized:
                custom_keys.add(normalized)
    custom_headers = [f"custom:{key}" for key in sorted(custom_keys, key=lambda item: item.lower())]
    headers = [*_BASE_EXPORT_HEADERS, *custom_headers]
    export_rows: list[dict[str, object]] = []
    for row in list(rows or []):
        payload = dict(row or {})
        custom_data = {
            normalize_cell(key): normalize_cell(value)
            for key, value in dict(payload.get("custom_data") or {}).items()
            if normalize_cell(key)
        }
        export_rows.append(
            {
                "device_type": normalize_cell(payload.get("device_type") or payload.get("type")),
                "name": normalize_cell(payload.get("name")),
                "ip": normalize_cell(payload.get("ip")),
                "description": normalize_cell(payload.get("description")),
                "id_Teamviewer": normalize_cell(payload.get("id_Teamviewer")),
                "device_subtype": normalize_cell(payload.get("device_subtype")),
                "action_double_click": normalize_cell(payload.get("action_double_click")),
                "web_url": normalize_cell(payload.get("web_url")),
                "ssh_user": normalize_cell(payload.get("ssh_user")),
                "device_login": normalize_cell(payload.get("device_login")),
                "notify": "1" if bool(payload.get("notify", True)) else "0",
                **{f"custom:{key}": value for key, value in custom_data.items()},
            }
        )
    return encode_csv_bytes(headers=headers, rows=export_rows)


def resolve_effective_column_mapping(
    *,
    headers: list[str],
    column_mappings: list[dict] | None = None,
) -> list[dict[str, str]]:
    resolved = _resolve_column_mapping(headers, column_mappings=column_mappings)
    output: list[dict[str, str]] = []
    for index, source_column in enumerate(list(headers or [])):
        kind, key = resolved.get(index, ("ignore", ""))
        if kind == "known":
            output.append(
                {
                    "source_column": str(source_column or ""),
                    "target_field": str(key or ""),
                    "custom_key": "",
                }
            )
            continue
        if kind == "custom":
            output.append(
                {
                    "source_column": str(source_column or ""),
                    "target_field": "custom",
                    "custom_key": str(key or ""),
                }
            )
            continue
        output.append(
            {
                "source_column": str(source_column or ""),
                "target_field": "__ignore__",
                "custom_key": "",
            }
        )
    return output


def _resolve_column_mapping(headers: list[str], *, column_mappings: list[dict] | None = None) -> dict[int, tuple[str, str]]:
    manual_by_header = _normalize_manual_column_mapping(column_mappings or [])
    mapping: dict[int, tuple[str, str]] = {}
    for index, header in enumerate(list(headers or [])):
        manual = manual_by_header.get(str(header or ""))
        if manual is not None:
            mapping[index] = manual
            continue
        normalized = normalize_header_key(header)
        if not normalized:
            mapping[index] = ("ignore", "")
            continue
        if normalized.startswith("custom:"):
            custom_key = normalize_cell(str(header).split(":", 1)[1])
            mapping[index] = ("custom", custom_key or f"champ_{index + 1}")
            continue
        if normalized.startswith("custom_"):
            custom_key = normalize_cell(str(header)[len("custom_"):])
            mapping[index] = ("custom", custom_key or f"champ_{index + 1}")
            continue
        matched = _matched_known_column(normalized)
        if matched:
            mapping[index] = ("known", matched)
        else:
            mapping[index] = ("custom", normalize_cell(header) or f"champ_{index + 1}")
    return mapping


def _normalize_manual_column_mapping(column_mappings: list[dict]) -> dict[str, tuple[str, str]]:
    known_fields = set(_HEADER_ALIASES.keys())
    output: dict[str, tuple[str, str]] = {}
    for row in list(column_mappings or []):
        source_column = normalize_cell((row or {}).get("source_column"))
        if not source_column:
            continue
        target_field_raw = normalize_cell((row or {}).get("target_field")).lower()
        custom_key_raw = normalize_cell((row or {}).get("custom_key"))
        if not target_field_raw or target_field_raw in {"auto", "__auto__"}:
            continue
        if target_field_raw in {"ignore", "__ignore__", "none"}:
            output[source_column] = ("ignore", "")
            continue
        if target_field_raw in known_fields:
            output[source_column] = ("known", target_field_raw)
            continue
        if target_field_raw == "custom":
            output[source_column] = ("custom", custom_key_raw or source_column)
            continue
        if target_field_raw.startswith("custom:"):
            custom_key = normalize_cell(target_field_raw.split(":", 1)[1])
            output[source_column] = ("custom", custom_key or custom_key_raw or source_column)
            continue
        output[source_column] = ("custom", custom_key_raw or target_field_raw or source_column)
    return output


def _parse_single_device_row(
    *,
    row: list[str],
    headers: list[str],
    mapping: dict[int, tuple[str, str]],
    default_device_type: str,
    allowed_device_types: set[str],
) -> dict | None:
    values_by_key: dict[str, str] = {}
    custom_data: dict[str, str] = {}
    for index, label in enumerate(headers):
        raw_value = normalize_cell(row[index] if index < len(row) else "")
        kind, key = mapping.get(index, ("ignore", ""))
        if kind == "known":
            values_by_key[key] = raw_value
            continue
        if kind == "ignore":
            continue
        if raw_value:
            custom_data[key] = raw_value
    device_type = normalize_cell(values_by_key.get("device_type") or default_device_type).lower()
    name = normalize_cell(values_by_key.get("name"))
    ip = normalize_cell(values_by_key.get("ip"))
    if not device_type or not name or not ip:
        return None
    if allowed_device_types and device_type not in allowed_device_types:
        return None
    output = {
        "device_type": device_type,
        "name": name,
        "ip": ip,
        "description": normalize_cell(values_by_key.get("description")),
        "id_Teamviewer": normalize_cell(values_by_key.get("id_Teamviewer")),
        "device_subtype": normalize_cell(values_by_key.get("device_subtype")),
        "action_double_click": normalize_cell(values_by_key.get("action_double_click")),
        "web_url": normalize_cell(values_by_key.get("web_url")),
        "ssh_user": normalize_cell(values_by_key.get("ssh_user")),
        "notify": _parse_notify_flag(values_by_key.get("notify", "1")),
        "custom_data": custom_data,
    }
    if "device_login" in values_by_key:
        output["device_login"] = normalize_cell(values_by_key.get("device_login"))
    if "device_password" in values_by_key:
        output["device_password"] = normalize_cell(values_by_key.get("device_password"))
    return output


def _parse_notify_flag(value: str) -> bool:
    lowered = normalize_cell(value).lower()
    if lowered in {"0", "false", "faux", "no", "non", "off"}:
        return False
    return True


def _matched_known_column(normalized_header: str) -> str:
    for key, aliases in _HEADER_ALIASES.items():
        if normalized_header in aliases:
            return key
    return ""
