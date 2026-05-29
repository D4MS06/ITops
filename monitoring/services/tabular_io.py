from __future__ import annotations

import csv
import io
import posixpath
import re
from dataclasses import dataclass
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

MAX_TABULAR_ROWS = 5000
HEADER_MODE_AUTO = "auto"
HEADER_MODE_FIRST = "first"
HEADER_MODE_MANUAL = "manual"
_VALID_HEADER_MODES = {HEADER_MODE_AUTO, HEADER_MODE_FIRST, HEADER_MODE_MANUAL}
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_WORKBOOK_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


@dataclass(slots=True)
class TabularParseMetadata:
    headers: list[str]
    rows: list[list[str]]
    source_rows: list[list[str]]
    detected_header_row_number: int = 1
    effective_header_mode: str = HEADER_MODE_AUTO


def parse_tabular_file(
    *,
    filename: str,
    content_bytes: bytes,
    max_rows: int = MAX_TABULAR_ROWS,
    sheet_name: str = "",
    header_mode: str = HEADER_MODE_AUTO,
    header_row_number: int = 1,
) -> tuple[list[str], list[list[str]]]:
    parsed = parse_tabular_file_with_metadata(
        filename=filename,
        content_bytes=content_bytes,
        max_rows=max_rows,
        sheet_name=sheet_name,
        header_mode=header_mode,
        header_row_number=header_row_number,
    )
    return parsed.headers, parsed.rows


def parse_tabular_file_with_metadata(
    *,
    filename: str,
    content_bytes: bytes,
    max_rows: int = MAX_TABULAR_ROWS,
    sheet_name: str = "",
    header_mode: str = HEADER_MODE_AUTO,
    header_row_number: int = 1,
) -> TabularParseMetadata:
    suffix = str(filename or "").strip().lower()
    effective_mode = normalize_header_mode(header_mode)
    if suffix.endswith(".xls"):
        raise ValueError("Format .xls non supporte. Enregistre le fichier en .xlsx ou .csv.")
    if suffix.endswith(".xlsx"):
        source_rows = _parse_xlsx_rows(content_bytes, max_rows=max_rows, sheet_name=sheet_name)
    elif suffix.endswith(".csv") or suffix.endswith(".txt") or suffix.endswith(".tsv"):
        source_rows = _parse_csv_rows(content_bytes, max_rows=max_rows)
    else:
        if _looks_like_xlsx_bytes(content_bytes):
            source_rows = _parse_xlsx_rows(content_bytes, max_rows=max_rows, sheet_name=sheet_name)
        elif _looks_like_legacy_xls_bytes(content_bytes):
            raise ValueError("Format .xls non supporte. Enregistre le fichier en .xlsx ou .csv.")
        else:
            source_rows = _parse_csv_rows(content_bytes, max_rows=max_rows)
    headers, rows, detected_row = _extract_headers_and_rows(
        source_rows=source_rows,
        header_mode=effective_mode,
        header_row_number=header_row_number,
    )
    labels = normalize_headers(headers, rows)
    if not labels:
        raise ValueError("Aucune colonne detectee dans le fichier.")
    return TabularParseMetadata(
        headers=labels,
        rows=rows,
        source_rows=source_rows,
        detected_header_row_number=detected_row,
        effective_header_mode=effective_mode,
    )


def resolve_tabular_sheet_selection(
    *,
    filename: str,
    content_bytes: bytes,
    sheet_name: str = "",
) -> tuple[str, list[str]]:
    if not _is_xlsx_input(filename=filename, content_bytes=content_bytes):
        return "", []
    try:
        with zipfile.ZipFile(io.BytesIO(content_bytes)) as workbook:
            sheet_refs = _read_sheet_refs(workbook)
    except zipfile.BadZipFile as exc:
        raise ValueError("Fichier Excel invalide.") from exc
    except KeyError as exc:
        raise ValueError("Structure Excel invalide (feuille introuvable).") from exc
    available = [name for name, _path in sheet_refs]
    if not available:
        raise ValueError("Structure Excel invalide (feuille introuvable).")
    requested = normalize_cell(sheet_name)
    if not requested:
        return available[0], available
    requested_key = _normalize_sheet_lookup_key(requested)
    for name in available:
        if _normalize_sheet_lookup_key(name) == requested_key:
            return name, available
    raise ValueError(f"Feuille Excel introuvable: {requested}.")


def normalize_header_mode(value: object) -> str:
    raw = normalize_cell(value).lower()
    return raw if raw in _VALID_HEADER_MODES else HEADER_MODE_AUTO


def rows_as_dicts(*, headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    labels = [normalize_cell(item) for item in list(headers or [])]
    output: list[dict[str, str]] = []
    for row in list(rows or []):
        payload: dict[str, str] = {}
        for index, label in enumerate(labels):
            if not label:
                continue
            payload[label] = normalize_cell(row[index] if index < len(row) else "")
        output.append(payload)
    return output


def encode_csv_bytes(*, headers: list[str], rows: list[dict[str, object]] | list[list[object]]) -> bytes:
    normalized_headers = [str(item or "").strip() for item in list(headers or [])]
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(normalized_headers)
    for row in list(rows or []):
        if isinstance(row, dict):
            writer.writerow([_normalize_csv_value(row.get(header, "")) for header in normalized_headers])
            continue
        values = list(row or [])
        writer.writerow([_normalize_csv_value(values[index] if index < len(values) else "") for index in range(len(normalized_headers))])
    text = output.getvalue()
    # Add BOM for direct Excel opening on Windows (UTF-8 with accents).
    return ("\ufeff" + text).encode("utf-8")


def normalize_headers(headers: list[str], rows: list[list[str]]) -> list[str]:
    max_columns = max([len(headers or [])] + [len(row or []) for row in list(rows or [])], default=0)
    labels: list[str] = []
    seen: dict[str, int] = {}
    for index in range(max_columns):
        raw_label = normalize_cell(headers[index] if index < len(headers or []) else "")
        base = raw_label or f"Colonne {index + 1}"
        key = base.lower()
        count = seen.get(key, 0) + 1
        seen[key] = count
        label = base if count == 1 else f"{base} ({count})"
        labels.append(label)
    return labels


def normalize_cell(value: object) -> str:
    return str(value or "").replace("\ufeff", "").strip()


def normalize_header_key(value: object) -> str:
    raw = normalize_cell(value).lower()
    if not raw:
        return ""
    folded = unicodedata.normalize("NFKD", raw)
    ascii_only = "".join(char for char in folded if ord(char) < 128)
    compact = ascii_only.replace("-", "_").replace(".", "_").replace("/", "_")
    compact = " ".join(compact.split())
    compact = compact.replace(" ", "_")
    while "__" in compact:
        compact = compact.replace("__", "_")
    return compact.strip("_")


def decode_text_bytes(content_bytes: bytes) -> str:
    raw = bytes(content_bytes or b"")
    if not raw:
        raise ValueError("Fichier vide.")
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Encodage texte non supporte.")


def _normalize_csv_value(value: object) -> str:
    return normalize_cell(value)


def _parse_csv_rows(content_bytes: bytes, *, max_rows: int) -> list[list[str]]:
    text = decode_text_bytes(content_bytes)
    sample = text[:8192]
    delimiter = _guess_delimiter(sample)
    stream = io.StringIO(text, newline="")
    reader = csv.reader(stream, delimiter=delimiter)
    rows: list[list[str]] = []
    for raw_row in reader:
        row = [normalize_cell(item) for item in raw_row]
        while row and not row[-1]:
            row.pop()
        if any(row):
            rows.append(row)
        if len(rows) >= (max_rows + 1):
            break
    if not rows:
        raise ValueError("Le fichier ne contient aucune ligne exploitable.")
    return rows


def _parse_csv_bytes(content_bytes: bytes, *, max_rows: int) -> tuple[list[str], list[list[str]]]:
    source_rows = _parse_csv_rows(content_bytes, max_rows=max_rows)
    return source_rows[0], source_rows[1:]


def _parse_xlsx_rows(content_bytes: bytes, *, max_rows: int, sheet_name: str = "") -> list[list[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(content_bytes)) as workbook:
            sheet_refs = _read_sheet_refs(workbook)
            sheet_path = _resolve_sheet_path(sheet_refs=sheet_refs, requested_sheet_name=sheet_name)
            shared_strings = _read_shared_strings(workbook)
            source_rows = _read_sheet_rows(workbook.read(sheet_path), shared_strings, max_rows=max_rows)
    except zipfile.BadZipFile as exc:
        raise ValueError("Fichier Excel invalide.") from exc
    except KeyError as exc:
        raise ValueError("Structure Excel invalide (feuille introuvable).") from exc
    except ValueError:
        raise
    if not source_rows:
        raise ValueError("Le fichier Excel ne contient aucune ligne exploitable.")
    return source_rows


def _parse_xlsx_bytes(content_bytes: bytes, *, max_rows: int, sheet_name: str = "") -> tuple[list[str], list[list[str]]]:
    source_rows = _parse_xlsx_rows(content_bytes, max_rows=max_rows, sheet_name=sheet_name)
    return source_rows[0], source_rows[1:]


def _extract_headers_and_rows(
    *,
    source_rows: list[list[str]],
    header_mode: str,
    header_row_number: int,
) -> tuple[list[str], list[list[str]], int]:
    if not source_rows:
        raise ValueError("Le fichier ne contient aucune ligne exploitable.")
    mode = normalize_header_mode(header_mode)
    manual_row = max(1, int(header_row_number or 1))
    if mode == HEADER_MODE_FIRST:
        detected_row = 1
    elif mode == HEADER_MODE_MANUAL:
        if manual_row > len(source_rows):
            raise ValueError(
                f"Ligne d'entete invalide ({manual_row}). Le fichier contient {len(source_rows)} ligne(s) exploitable(s)."
            )
        detected_row = manual_row
    else:
        detected_row = _detect_header_row_number(source_rows)
    header_index = max(0, detected_row - 1)
    headers = list(source_rows[header_index] or [])
    rows = [list(row or []) for row in list(source_rows[header_index + 1:] or [])]
    return headers, rows, detected_row


def _detect_header_row_number(source_rows: list[list[str]]) -> int:
    if not source_rows:
        return 1
    max_candidates = min(len(source_rows), 12)
    best_index = 0
    best_score = float("-inf")
    for index in range(max_candidates):
        row = list(source_rows[index] or [])
        next_rows = [list(item or []) for item in source_rows[index + 1:index + 5]]
        score = _score_header_candidate(row=row, next_rows=next_rows, row_index=index)
        if score > best_score:
            best_score = score
            best_index = index
    return best_index + 1


def _score_header_candidate(*, row: list[str], next_rows: list[list[str]], row_index: int) -> float:
    filled = [normalize_cell(item) for item in list(row or []) if normalize_cell(item)]
    if not filled:
        return -1000.0
    score = 0.0
    cols = len(filled)
    score += min(cols, 8) * 0.35
    if cols == 1:
        score -= 1.6
    if row_index == 0:
        score += 0.2

    lowered = [item.lower() for item in filled]
    unique = len(set(lowered))
    if unique == len(lowered):
        score += 0.45
    else:
        score -= (len(lowered) - unique) * 0.25

    alpha_count = 0
    data_like_count = 0
    for value in filled:
        if re.search(r"[A-Za-z]", value):
            alpha_count += 1
        if _looks_like_data_value(value):
            data_like_count += 1
    score += alpha_count * 0.32
    score -= data_like_count * 0.26

    if next_rows:
        next_filled_values = [
            normalize_cell(item)
            for next_row in next_rows
            for item in list(next_row or [])
            if normalize_cell(item)
        ]
        if next_filled_values:
            sample = next_filled_values[: min(40, len(next_filled_values))]
            sample_data_like = sum(1 for item in sample if _looks_like_data_value(item))
            sample_alpha = sum(1 for item in sample if re.search(r"[A-Za-z]", item))
            score += (sample_data_like * 0.08)
            score -= (sample_alpha * 0.03)
        next_first = [normalize_cell(item[0] if item else "") for item in next_rows if any(normalize_cell(x) for x in item or [])]
        if next_first and normalize_cell(row[0] if row else ""):
            if normalize_cell(row[0]) in next_first:
                score -= 0.4
    return score


def _looks_like_data_value(value: str) -> bool:
    raw = normalize_cell(value)
    if not raw:
        return False
    lowered = raw.lower()
    if lowered in {"true", "false", "yes", "no", "oui", "non"}:
        return True
    if re.fullmatch(r"[+-]?\d+([.,]\d+)?", raw):
        return True
    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", raw):
        return True
    if re.fullmatch(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", raw):
        return True
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", raw):
        return True
    if re.fullmatch(r"[0-9A-Fa-f]{2}([:-][0-9A-Fa-f]{2}){5}", raw):
        return True
    return False


def _resolve_first_sheet_path(workbook: zipfile.ZipFile) -> str:
    sheet_refs = _read_sheet_refs(workbook)
    if not sheet_refs:
        raise KeyError("xl/worksheets/sheet1.xml")
    return sheet_refs[0][1]


def _read_sheet_refs(workbook: zipfile.ZipFile) -> list[tuple[str, str]]:
    names_set = set(workbook.namelist())
    try:
        workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
        rels_xml = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        rel_targets: dict[str, str] = {}
        for rel in rels_xml.findall(f"{{{_PACKAGE_REL_NS}}}Relationship"):
            rel_id = str(rel.attrib.get("Id") or "").strip()
            target = _normalize_xlsx_target_path(rel.attrib.get("Target"))
            if rel_id and target:
                rel_targets[rel_id] = target
        if not rel_targets:
            for rel in rels_xml.findall("{*}Relationship"):
                rel_id = str(rel.attrib.get("Id") or "").strip()
                target = _normalize_xlsx_target_path(rel.attrib.get("Target"))
                if rel_id and target:
                    rel_targets[rel_id] = target
        output: list[tuple[str, str]] = []
        seen_paths: set[str] = set()
        sheets_root = workbook_xml.find(f"{{{_WORKBOOK_NS}}}sheets")
        sheet_nodes = list(sheets_root.findall(f"{{{_WORKBOOK_NS}}}sheet")) if sheets_root is not None else []
        for index, sheet_node in enumerate(sheet_nodes):
            label = normalize_cell(sheet_node.attrib.get("name"))
            rel_id = str(sheet_node.attrib.get(f"{{{_REL_NS}}}id") or "").strip()
            path = rel_targets.get(rel_id, "")
            if not path and rel_id:
                rel_by_wildcard = next(
                    (
                        _normalize_xlsx_target_path(rel.attrib.get("Target"))
                        for rel in rels_xml.findall("{*}Relationship")
                        if str(rel.attrib.get("Id") or "").strip() == rel_id
                    ),
                    "",
                )
                path = rel_by_wildcard
            if not path or path not in names_set or path in seen_paths:
                continue
            seen_paths.add(path)
            output.append((label or f"Feuille {index + 1}", path))
        if output:
            return output
    except Exception:
        pass
    candidates = sorted(
        name for name in workbook.namelist()
        if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
    )
    if not candidates:
        raise KeyError("xl/worksheets/sheet1.xml")
    return [(_fallback_sheet_label(path, index), path) for index, path in enumerate(candidates)]


def _resolve_sheet_path(*, sheet_refs: list[tuple[str, str]], requested_sheet_name: str = "") -> str:
    if not sheet_refs:
        raise KeyError("xl/worksheets/sheet1.xml")
    requested = normalize_cell(requested_sheet_name)
    if not requested:
        return sheet_refs[0][1]
    requested_key = _normalize_sheet_lookup_key(requested)
    for name, path in sheet_refs:
        if _normalize_sheet_lookup_key(name) == requested_key:
            return path
    raise ValueError(f"Feuille Excel introuvable: {requested}.")


def _normalize_xlsx_target_path(target: object) -> str:
    raw = str(target or "").strip().replace("\\", "/")
    if not raw:
        return ""
    if raw.startswith("./"):
        raw = raw[2:]
    if raw.startswith("/"):
        normalized = raw.lstrip("/")
    elif raw.startswith("xl/"):
        normalized = raw
    else:
        normalized = f"xl/{raw}"
    compact = posixpath.normpath(normalized).replace("\\", "/")
    if compact.startswith("../") or compact == "..":
        return ""
    if not compact.startswith("xl/"):
        return ""
    return compact


def _fallback_sheet_label(path: str, index: int) -> str:
    match = re.search(r"/([^/]+)\.xml$", str(path or ""))
    if not match:
        return f"Feuille {index + 1}"
    raw = normalize_cell(match.group(1))
    return raw or f"Feuille {index + 1}"


def _normalize_sheet_lookup_key(value: object) -> str:
    return normalize_cell(value).lower()


def _is_xlsx_input(*, filename: str, content_bytes: bytes) -> bool:
    suffix = str(filename or "").strip().lower()
    if suffix.endswith(".xls"):
        raise ValueError("Format .xls non supporte. Enregistre le fichier en .xlsx ou .csv.")
    if suffix.endswith(".xlsx"):
        return True
    if suffix.endswith(".csv") or suffix.endswith(".txt") or suffix.endswith(".tsv"):
        return False
    if _looks_like_xlsx_bytes(content_bytes):
        return True
    if _looks_like_legacy_xls_bytes(content_bytes):
        raise ValueError("Format .xls non supporte. Enregistre le fichier en .xlsx ou .csv.")
    return False


def _read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in set(workbook.namelist()):
        return []
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("{*}si"):
        texts = [node.text or "" for node in item.findall(".//{*}t")]
        values.append(normalize_cell("".join(texts)))
    return values


def _read_sheet_rows(sheet_xml: bytes, shared_strings: list[str], *, max_rows: int) -> list[list[str]]:
    root = ET.fromstring(sheet_xml)
    rows: list[list[str]] = []
    for row_node in root.findall(".//{*}sheetData/{*}row"):
        row_values: list[str] = []
        current_col = 0
        for cell in row_node.findall("{*}c"):
            col_index = _column_index_from_ref(str(cell.attrib.get("r") or ""), fallback=current_col)
            current_col = col_index + 1
            while len(row_values) <= col_index:
                row_values.append("")
            row_values[col_index] = _read_cell_value(cell, shared_strings)
        while row_values and not row_values[-1]:
            row_values.pop()
        if any(row_values):
            rows.append(row_values)
        if len(rows) >= (max_rows + 1):
            break
    return rows


def _read_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = str(cell.attrib.get("t") or "").strip().lower()
    if cell_type == "inlineStr".lower():
        inline = cell.find("{*}is")
        if inline is None:
            return ""
        return normalize_cell("".join(node.text or "" for node in inline.findall(".//{*}t")))
    value_node = cell.find("{*}v")
    raw_value = (value_node.text or "") if value_node is not None else ""
    if cell_type == "s":
        try:
            index = int(str(raw_value).strip())
            return shared_strings[index] if 0 <= index < len(shared_strings) else ""
        except (ValueError, TypeError):
            return ""
    if cell_type == "b":
        return "true" if str(raw_value).strip() == "1" else "false"
    return normalize_cell(raw_value)


def _column_index_from_ref(ref: str, *, fallback: int) -> int:
    match = re.match(r"^([A-Za-z]+)", str(ref or "").strip())
    if not match:
        return fallback
    letters = match.group(1).upper()
    index = 0
    for char in letters:
        index = (index * 26) + (ord(char) - 64)
    return max(0, index - 1)


def _guess_delimiter(sample: str) -> str:
    candidates = [",", ";", "\t", "|"]
    lines = [line for line in str(sample or "").splitlines() if line.strip()]
    if not lines:
        return ","
    scored: list[tuple[float, str]] = []
    for delim in candidates:
        non_zero_counts = [line.count(delim) for line in lines if line.count(delim) > 0]
        if not non_zero_counts:
            scored.append((0.0, delim))
            continue
        lines_with_delim = len(non_zero_counts)
        total = sum(non_zero_counts)
        spread = max(non_zero_counts) - min(non_zero_counts)
        # Favor delimiters that appear in several lines with stable counts.
        score = (lines_with_delim * 100.0) + total - (spread * 0.5)
        scored.append((score, delim))
    scored.sort(reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else ","


def _looks_like_xlsx_bytes(content_bytes: bytes) -> bool:
    raw = bytes(content_bytes or b"")
    if len(raw) < 4:
        return False
    return raw[:2] == b"PK"


def _looks_like_legacy_xls_bytes(content_bytes: bytes) -> bool:
    raw = bytes(content_bytes or b"")
    if len(raw) < 8:
        return False
    return raw[:8] == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
