from __future__ import annotations

import csv
import io
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

MAX_TABULAR_ROWS = 5000
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_WORKBOOK_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def parse_tabular_file(*, filename: str, content_bytes: bytes, max_rows: int = MAX_TABULAR_ROWS) -> tuple[list[str], list[list[str]]]:
    suffix = str(filename or "").strip().lower()
    if suffix.endswith(".xls"):
        raise ValueError("Format .xls non supporte. Enregistre le fichier en .xlsx ou .csv.")
    if suffix.endswith(".xlsx"):
        headers, rows = _parse_xlsx_bytes(content_bytes, max_rows=max_rows)
    elif suffix.endswith(".csv") or suffix.endswith(".txt") or suffix.endswith(".tsv"):
        headers, rows = _parse_csv_bytes(content_bytes, max_rows=max_rows)
    else:
        if _looks_like_xlsx_bytes(content_bytes):
            headers, rows = _parse_xlsx_bytes(content_bytes, max_rows=max_rows)
        elif _looks_like_legacy_xls_bytes(content_bytes):
            raise ValueError("Format .xls non supporte. Enregistre le fichier en .xlsx ou .csv.")
        else:
            headers, rows = _parse_csv_bytes(content_bytes, max_rows=max_rows)
    labels = normalize_headers(headers, rows)
    if not labels:
        raise ValueError("Aucune colonne detectee dans le fichier.")
    return labels, rows


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


def _parse_csv_bytes(content_bytes: bytes, *, max_rows: int) -> tuple[list[str], list[list[str]]]:
    text = decode_text_bytes(content_bytes)
    stream = io.StringIO(text, newline="")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        reader = csv.reader(stream, dialect)
    except csv.Error:
        delimiter = _guess_delimiter(sample)
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
    return rows[0], rows[1:]


def _parse_xlsx_bytes(content_bytes: bytes, *, max_rows: int) -> tuple[list[str], list[list[str]]]:
    try:
        with zipfile.ZipFile(io.BytesIO(content_bytes)) as workbook:
            sheet_path = _resolve_first_sheet_path(workbook)
            shared_strings = _read_shared_strings(workbook)
            rows = _read_sheet_rows(workbook.read(sheet_path), shared_strings, max_rows=max_rows)
    except zipfile.BadZipFile as exc:
        raise ValueError("Fichier Excel invalide.") from exc
    except KeyError as exc:
        raise ValueError("Structure Excel invalide (feuille introuvable).") from exc
    if not rows:
        raise ValueError("Le fichier Excel ne contient aucune ligne exploitable.")
    return rows[0], rows[1:]


def _resolve_first_sheet_path(workbook: zipfile.ZipFile) -> str:
    try:
        workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
        rels_xml = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        first_sheet = workbook_xml.find(f"{{{_WORKBOOK_NS}}}sheets/{{{_WORKBOOK_NS}}}sheet")
        if first_sheet is not None:
            rel_id = str(first_sheet.attrib.get(f"{{{_REL_NS}}}id") or "").strip()
            for rel in rels_xml.findall("{*}Relationship"):
                if str(rel.attrib.get("Id") or "").strip() != rel_id:
                    continue
                target = str(rel.attrib.get("Target") or "").strip().replace("\\", "/")
                if not target:
                    break
                if target.startswith("/"):
                    return target.lstrip("/")
                if target.startswith("xl/"):
                    return target
                return f"xl/{target.lstrip('./')}"
    except Exception:
        pass
    candidates = sorted(
        name for name in workbook.namelist()
        if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
    )
    if not candidates:
        raise KeyError("xl/worksheets/sheet1.xml")
    return candidates[0]


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
    first_line = str(sample or "").splitlines()[0] if str(sample or "").splitlines() else ""
    candidates = [",", ";", "\t", "|"]
    scored = sorted(((first_line.count(delim), delim) for delim in candidates), reverse=True)
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
