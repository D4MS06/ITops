import io
import zipfile

from monitoring.services.service_fields_import import infer_service_fields_from_file


def _build_minimal_xlsx_bytes() -> bytes:
    shared_strings = [
        "Marque",
        "Modele",
        "Adresse IP",
        "Date installation",
        "HP",
        "LaserJet 4100",
        "10.20.30.40",
        "2026-04-01",
        "OfficeJet 9010",
        "10.20.30.41",
        "2026-04-02",
        "Canon",
        "ImageRunner C3326",
        "10.20.30.42",
        "2026-04-03",
    ]
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">'
        + "".join(f"<si><t>{value}</t></si>" for value in shared_strings)
        + "</sst>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets><sheet name=\"Feuille1\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
        "</workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        "<row r=\"1\"><c r=\"A1\" t=\"s\"><v>0</v></c><c r=\"B1\" t=\"s\"><v>1</v></c><c r=\"C1\" t=\"s\"><v>2</v></c><c r=\"D1\" t=\"s\"><v>3</v></c></row>"
        "<row r=\"2\"><c r=\"A2\" t=\"s\"><v>4</v></c><c r=\"B2\" t=\"s\"><v>5</v></c><c r=\"C2\" t=\"s\"><v>6</v></c><c r=\"D2\" t=\"s\"><v>7</v></c></row>"
        "<row r=\"3\"><c r=\"A3\" t=\"s\"><v>4</v></c><c r=\"B3\" t=\"s\"><v>8</v></c><c r=\"C3\" t=\"s\"><v>9</v></c><c r=\"D3\" t=\"s\"><v>10</v></c></row>"
        "<row r=\"4\"><c r=\"A4\" t=\"s\"><v>11</v></c><c r=\"B4\" t=\"s\"><v>12</v></c><c r=\"C4\" t=\"s\"><v>13</v></c><c r=\"D4\" t=\"s\"><v>14</v></c></row>"
        "</sheetData>"
        "</worksheet>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        archive.writestr("xl/sharedStrings.xml", shared_xml)
    return buffer.getvalue()


def test_infer_service_fields_from_xlsx_detects_list_ip_date():
    content = _build_minimal_xlsx_bytes()
    fields, detected_rows, detected_columns = infer_service_fields_from_file(
        filename="import.xlsx",
        content_bytes=content,
    )
    assert detected_rows == 3
    assert detected_columns == 4
    by_key = {str(row.get("field_key") or ""): row for row in fields}
    assert by_key["marque"]["field_kind"] == "list"
    assert by_key["marque"]["options"] == "HP,Canon"
    assert by_key["adresse_ip"]["field_kind"] == "ip"
    assert by_key["date_installation"]["field_kind"] == "date"


def test_infer_service_fields_detects_xlsx_even_without_extension():
    content = _build_minimal_xlsx_bytes()
    fields, detected_rows, detected_columns = infer_service_fields_from_file(
        filename="import.bin",
        content_bytes=content,
    )
    assert detected_rows == 3
    assert detected_columns == 4
    assert fields


def test_infer_service_fields_honors_column_mapping_ignore():
    content = _build_minimal_xlsx_bytes()
    fields, detected_rows, detected_columns = infer_service_fields_from_file(
        filename="import.xlsx",
        content_bytes=content,
        column_mappings=[
            {"source_column": "Marque", "target_field": "__create_field__"},
            {"source_column": "Modele", "target_field": "__ignore__"},
            {"source_column": "Adresse IP", "target_field": "__create_field__"},
            {"source_column": "Date installation", "target_field": "__ignore__"},
        ],
    )
    assert detected_rows == 3
    assert detected_columns == 4
    keys = [str(row.get("field_key") or "") for row in fields]
    assert keys == ["marque", "adresse_ip"]


def test_infer_service_fields_uses_custom_label_for_created_field():
    content = _build_minimal_xlsx_bytes()
    fields, _detected_rows, _detected_columns = infer_service_fields_from_file(
        filename="import.xlsx",
        content_bytes=content,
        column_mappings=[
            {"source_column": "Marque", "target_field": "__create_field__", "custom_key": "Fabricant"},
            {"source_column": "Modele", "target_field": "__ignore__"},
            {"source_column": "Adresse IP", "target_field": "__ignore__"},
            {"source_column": "Date installation", "target_field": "__ignore__"},
        ],
    )
    assert len(fields) == 1
    assert fields[0]["field_key"] == "fabricant"
    assert fields[0]["label"] == "Fabricant"


def test_infer_service_fields_can_target_existing_field_key():
    content = _build_minimal_xlsx_bytes()
    fields, _detected_rows, _detected_columns = infer_service_fields_from_file(
        filename="import.xlsx",
        content_bytes=content,
        column_mappings=[
            {"source_column": "Marque", "target_field": "existing_brand"},
            {"source_column": "Modele", "target_field": "__ignore__"},
            {"source_column": "Adresse IP", "target_field": "__ignore__"},
            {"source_column": "Date installation", "target_field": "__ignore__"},
        ],
    )
    assert len(fields) == 1
    assert fields[0]["field_key"] == "existing_brand"
    assert fields[0]["label"] == "Marque"


def test_infer_service_fields_honors_manual_field_kind():
    content = _build_minimal_xlsx_bytes()
    fields, _detected_rows, _detected_columns = infer_service_fields_from_file(
        filename="import.xlsx",
        content_bytes=content,
        column_mappings=[
            {"source_column": "Marque", "target_field": "__create_field__", "field_kind": "text"},
            {"source_column": "Modele", "target_field": "__ignore__"},
            {"source_column": "Adresse IP", "target_field": "__create_field__", "field_kind": "ip"},
            {"source_column": "Date installation", "target_field": "__ignore__"},
        ],
    )
    by_key = {str(row.get("field_key") or ""): row for row in fields}
    assert by_key["marque"]["field_kind"] == "text"
    assert by_key["marque"]["options"] == ""
    assert by_key["adresse_ip"]["field_kind"] == "ip"


def test_infer_service_fields_rejects_legacy_xls_with_clear_message():
    legacy_header = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 32
    try:
        infer_service_fields_from_file(
            filename="legacy.xls",
            content_bytes=legacy_header,
        )
        assert False, "Expected ValueError for .xls"
    except ValueError as exc:
        assert ".xls" in str(exc)
