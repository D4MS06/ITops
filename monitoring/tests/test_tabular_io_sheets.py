import io
import zipfile

import pytest

from monitoring.services.tabular_io import parse_tabular_file, resolve_tabular_sheet_selection


def _cell(ref: str, value: str) -> str:
    return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'


def _row(index: int, values: list[str]) -> str:
    cells = "".join(_cell(f"{chr(65 + col)}{index}", value) for col, value in enumerate(values))
    return f'<row r="{index}">{cells}</row>'


def _sheet_xml(rows: list[list[str]]) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(_row(index + 1, row) for index, row in enumerate(rows))
        + "</sheetData>"
        "</worksheet>"
    )


def _build_two_sheets_xlsx() -> bytes:
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        '<sheet name="Serveurs" sheetId="1" r:id="rId1"/>'
        '<sheet name="Switches" sheetId="2" r:id="rId2"/>'
        "</sheets>"
        "</workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet2.xml"/>'
        "</Relationships>"
    )
    sheet1_xml = _sheet_xml(
        [
            ["type", "name", "ip"],
            ["server", "srv-01", "10.0.0.10"],
        ]
    )
    sheet2_xml = _sheet_xml(
        [
            ["type", "name", "ip"],
            ["switch", "sw-core", "10.0.1.1"],
        ]
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet1_xml)
        archive.writestr("xl/worksheets/sheet2.xml", sheet2_xml)
    return buffer.getvalue()


def test_parse_tabular_file_uses_first_sheet_by_default():
    content = _build_two_sheets_xlsx()
    headers, rows = parse_tabular_file(filename="devices.xlsx", content_bytes=content)
    assert headers == ["type", "name", "ip"]
    assert rows == [["server", "srv-01", "10.0.0.10"]]


def test_parse_tabular_file_can_target_sheet_name():
    content = _build_two_sheets_xlsx()
    headers, rows = parse_tabular_file(
        filename="devices.xlsx",
        content_bytes=content,
        sheet_name="Switches",
    )
    assert headers == ["type", "name", "ip"]
    assert rows == [["switch", "sw-core", "10.0.1.1"]]


def test_resolve_tabular_sheet_selection_returns_available_sheets():
    content = _build_two_sheets_xlsx()
    selected, available = resolve_tabular_sheet_selection(
        filename="devices.xlsx",
        content_bytes=content,
        sheet_name="switches",
    )
    assert selected == "Switches"
    assert available == ["Serveurs", "Switches"]


def test_parse_tabular_file_rejects_unknown_sheet_name():
    content = _build_two_sheets_xlsx()
    with pytest.raises(ValueError):
        parse_tabular_file(
            filename="devices.xlsx",
            content_bytes=content,
            sheet_name="Inconnue",
        )


def test_parse_tabular_file_auto_detects_header_line_after_title():
    content = (
        "Inventaire serveurs\n"
        "type;name;ip\n"
        "server;srv-01;10.0.0.10\n"
    ).encode("utf-8")
    headers, rows = parse_tabular_file(
        filename="devices.csv",
        content_bytes=content,
        header_mode="auto",
    )
    assert headers == ["type", "name", "ip"]
    assert rows == [["server", "srv-01", "10.0.0.10"]]


def test_parse_tabular_file_manual_header_line():
    content = (
        "Export des equipements\n"
        "type;name;ip\n"
        "switch;sw-core;10.0.1.1\n"
    ).encode("utf-8")
    headers, rows = parse_tabular_file(
        filename="devices.csv",
        content_bytes=content,
        header_mode="manual",
        header_row_number=2,
    )
    assert headers == ["type", "name", "ip"]
    assert rows == [["switch", "sw-core", "10.0.1.1"]]


def test_parse_tabular_file_manual_header_line_out_of_range_raises():
    content = (
        "type;name;ip\n"
        "switch;sw-core;10.0.1.1\n"
    ).encode("utf-8")
    with pytest.raises(ValueError):
        parse_tabular_file(
            filename="devices.csv",
            content_bytes=content,
            header_mode="manual",
            header_row_number=8,
        )
