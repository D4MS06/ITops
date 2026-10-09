from __future__ import annotations

from monitoring.services.l3_router_scan_service import L3RouterScanService


def test_parse_arp_output_supports_common_formats():
    raw = """
Internet  192.168.11.7              2   0017.5577.f9f8  ARPA   Vlan11
192.168.11.8 dev br0 lladdr 00:08:5d:ac:d4:62 REACHABLE
192.168.11.9 00-08-5D-69-E7-A7 dynamic
"""
    rows = L3RouterScanService.parse_arp_output(raw)
    assert any(row["ip"] == "192.168.11.7" and row["mac"] == "00:17:55:77:F9:F8" for row in rows)
    assert any(row["ip"] == "192.168.11.8" and row["mac"] == "00:08:5D:AC:D4:62" for row in rows)
    assert any(row["ip"] == "192.168.11.9" and row["mac"] == "00:08:5D:69:E7:A7" for row in rows)
    assert any(str(row.get("iface", "")).lower().startswith("vlan") for row in rows)


def test_scan_router_arp_applies_range_filter(monkeypatch):
    service = L3RouterScanService()
    monkeypatch.setattr(
        L3RouterScanService,
        "_fetch_arp_text",
        lambda *_args, **_kwargs: "192.168.11.9 00:08:5D:69:E7:A7 dynamic\n192.168.12.9 00:08:5D:69:E7:A8 dynamic",
    )
    monkeypatch.setattr(L3RouterScanService, "_hostname", lambda _ip: "")
    service._mac_vendor_service = type(
        "VendorStub",
        (),
        {
            "resolve": staticmethod(lambda _mac, allow_network=False: ""),
        },
    )()

    rows = service.scan_router_arp(
        host="192.168.11.1",
        ssh_user="admin",
        start_ip="192.168.11.1",
        end_ip="192.168.11.254",
    )

    assert len(rows) == 1
    assert rows[0]["ip"] == "192.168.11.9"
