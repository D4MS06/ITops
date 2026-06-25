from __future__ import annotations

import datetime as _dt
import ipaddress
import re
from urllib.parse import urlparse


ALLOWED_FIELD_KINDS = {"text", "ip", "url", "date", "list"}


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_kind(value: object) -> str:
    raw = _normalize_text(value).lower()
    if raw in {"choice", "select", "dropdown", "liste"}:
        return "list"
    return raw if raw in ALLOWED_FIELD_KINDS else "text"


def _normalize_list_source_kind(value: object) -> str:
    raw = _normalize_text(value).lower()
    return raw if raw in {"local", "shared"} else "local"


def _slugify_identifier(value: object, *, fallback: str) -> str:
    normalized = _normalize_text(value).lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        return fallback
    if normalized[0].isdigit():
        normalized = f"{fallback}_{normalized}"
    return normalized


def normalize_service_code(*, code: object, label: object) -> str:
    return _slugify_identifier(code or label, fallback="service")


def normalize_field_key(*, field_key: object, label: object, index: int) -> str:
    return _slugify_identifier(field_key or label, fallback=f"field_{index + 1}")


def parse_list_options(raw: object) -> list[str]:
    if isinstance(raw, list):
        parts = [str(item or "").strip() for item in raw]
    else:
        parts = [part.strip() for part in re.split(r"[,;\r\n]+", str(raw or ""))]
    options: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        options.append(part)
    return options


def normalize_service_fields(rows: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    seen_keys: set[str] = set()
    for index, row in enumerate(rows or []):
        label = _normalize_text((row or {}).get("label"))
        if not label:
            raise ValueError("Chaque champ doit avoir un libelle.")
        key = normalize_field_key(field_key=(row or {}).get("field_key"), label=label, index=index)
        if key in seen_keys:
            raise ValueError(f"Champ en doublon: {key}")
        seen_keys.add(key)
        field_kind = _normalize_kind((row or {}).get("field_kind"))
        options_values = parse_list_options((row or {}).get("options"))
        list_source_kind = _normalize_list_source_kind((row or {}).get("list_source_kind"))
        shared_list_code = _slugify_identifier((row or {}).get("shared_list_code"), fallback="").strip("_")
        if field_kind == "list" and list_source_kind == "local" and not options_values:
            raise ValueError(f"Le champ '{label}' doit contenir des options de liste locale.")
        if field_kind == "list" and list_source_kind == "shared" and not shared_list_code:
            raise ValueError(f"Le champ '{label}' doit referencer une liste commune.")
        default_value = _normalize_text((row or {}).get("default_value"))
        if field_kind == "list" and list_source_kind == "local" and default_value:
            allowed = {item.lower() for item in options_values}
            if default_value.lower() not in allowed:
                raise ValueError(f"La valeur par defaut du champ '{label}' doit etre presente dans la liste.")
            # Conserve la casse configuree dans la liste.
            default_value = next((item for item in options_values if item.lower() == default_value.lower()), default_value)
        if field_kind != "list":
            list_source_kind = "local"
            shared_list_code = ""
        cleaned.append(
            {
                "field_key": key,
                "label": label,
                "field_kind": field_kind,
                "required": bool((row or {}).get("required", False)),
                "options": ",".join(options_values),
                "default_value": default_value,
                "sort_order": int((row or {}).get("sort_order") or ((index + 1) * 10)),
                "list_source_kind": list_source_kind,
                "shared_list_code": shared_list_code,
                "track_history": bool((row or {}).get("track_history", False)),
                "inline_editable": bool((row or {}).get("inline_editable", False)),
                "quick_filter": bool((row or {}).get("quick_filter", False)),
            }
        )
    return cleaned


def validate_record_values(*, fields: list[dict], values: dict[str, object], fill_defaults: bool) -> dict[str, str]:
    source = values if isinstance(values, dict) else {}
    cleaned: dict[str, str] = {}
    for field in fields or []:
        field_key = _normalize_text(field.get("field_key"))
        if not field_key:
            continue
        label = _normalize_text(field.get("label")) or field_key
        field_kind = _normalize_kind(field.get("field_kind"))
        required = bool(field.get("required", False))
        raw_value = source.get(field_key, "")
        value = _normalize_text(raw_value)
        if fill_defaults and not value:
            value = _normalize_text(field.get("default_value"))
        if field_kind == "date" and value:
            value = _normalize_date_value(value)
        if required and not value:
            raise ValueError(f"Le champ '{label}' est obligatoire.")
        if value:
            _validate_single_value(field_kind=field_kind, label=label, value=value, options=_normalize_text(field.get("options")))
        cleaned[field_key] = value
    return cleaned


def _normalize_date_value(value: object) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    numeric = text.replace(",", ".")
    if re.fullmatch(r"\d+(\.\d+)?", numeric):
        try:
            serial = float(numeric)
            if 1 <= serial <= 100000:
                base = _dt.date(1899, 12, 30)
                return (base + _dt.timedelta(days=int(serial))).isoformat()
        except (OverflowError, ValueError):
            pass
    for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return _dt.datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    return text


def _validate_single_value(*, field_kind: str, label: str, value: str, options: str) -> None:
    if field_kind == "ip":
        try:
            ipaddress.ip_address(value)
        except ValueError as exc:
            raise ValueError(f"Le champ '{label}' doit contenir une IP valide.") from exc
        return
    if field_kind == "url":
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Le champ '{label}' doit contenir une URL valide.")
        return
    if field_kind == "date":
        try:
            _dt.date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Le champ '{label}' doit utiliser le format date YYYY-MM-DD.") from exc
        return
    if field_kind == "list":
        options_values = parse_list_options(options)
        allowed = {item.lower() for item in options_values}
        if value.lower() not in allowed:
            raise ValueError(f"Le champ '{label}' doit utiliser une valeur de la liste.")


def normalize_child_rows(rows: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for index, row in enumerate(rows or []):
        name = _normalize_text((row or {}).get("name"))
        code = _normalize_text((row or {}).get("code"))
        if not name and not code:
            continue
        if not name or not code:
            raise ValueError("Chaque ligne liee doit contenir un nom et un code.")
        cleaned.append(
            {
                "name": name,
                "code": code,
                "sort_order": int((row or {}).get("sort_order") or ((index + 1) * 10)),
            }
        )
    return cleaned
