from __future__ import annotations

import threading

import pytest

from monitoring.services.network_scan_service import NetworkScanService


def test_vlan_to_range():
    service = NetworkScanService()
    assert service.vlan_to_range(10) == ("192.168.10.1", "192.168.10.254")


def test_vlan_to_range_rejects_out_of_bounds():
    service = NetworkScanService()
    with pytest.raises(ValueError):
        service.vlan_to_range(300)


def test_normalize_range_validates_order():
    service = NetworkScanService()
    start, end = service.normalize_range("192.168.1.10", "192.168.1.20")
    assert str(start) == "192.168.1.10"
    assert str(end) == "192.168.1.20"
    with pytest.raises(ValueError):
        service.normalize_range("192.168.1.20", "192.168.1.10")


def test_parse_arp_table_extracts_mac_mapping():
    raw = """
Interface: 192.168.1.50 --- 0x9
  Internet Address      Physical Address      Type
  192.168.1.1           aa-bb-cc-dd-ee-ff     dynamic
  192.168.1.10          11:22:33:44:55:66     dynamic
"""
    parsed = NetworkScanService.parse_arp_table(raw)
    assert parsed["192.168.1.1"] == "AA:BB:CC:DD:EE:FF"
    assert parsed["192.168.1.10"] == "11:22:33:44:55:66"


def test_scan_range_returns_immediately_when_stopped(monkeypatch):
    service = NetworkScanService()
    stop_event = threading.Event()
    stop_event.set()

    def _fail_if_called(_self, _ip, _timeout_ms, _tcp_ports):
        raise AssertionError("_probe_host should not be called when stop_event is already set")

    monkeypatch.setattr(NetworkScanService, "_probe_host", _fail_if_called)

    rows = service.scan_range(start_ip="192.168.1.1", end_ip="192.168.1.3", stop_event=stop_event)
    assert rows == []


def test_scan_range_uses_arp_fallback_when_ping_fails(monkeypatch):
    service = NetworkScanService()
    service._mac_vendor_service = type(
        "VendorStub",
        (),
        {
            "resolve": staticmethod(lambda _mac, allow_network=False: ""),
            "oui_prefix": staticmethod(lambda mac: "AA:BB:CC" if str(mac).startswith("AA:BB:CC") else ""),
        },
    )()

    monkeypatch.setattr(NetworkScanService, "_probe_host", lambda *_args, **_kwargs: (False, ""))
    monkeypatch.setattr(NetworkScanService, "_arp_table", lambda *_args, **_kwargs: {"192.168.1.2": "AA:BB:CC:DD:EE:FF"})
    monkeypatch.setattr(NetworkScanService, "_hostname", lambda *_args, **_kwargs: "printer.local")

    rows = service.scan_range(start_ip="192.168.1.1", end_ip="192.168.1.3")

    assert len(rows) == 1
    assert rows[0]["ip"] == "192.168.1.2"
    assert rows[0]["hostname"] == "printer.local"
    assert rows[0]["mac"] == "AA:BB:CC:DD:EE:FF"
    assert rows[0]["vendor"] == ""
    assert rows[0]["status"] == "arp"


def test_scan_range_rejects_range_larger_than_max_hosts():
    service = NetworkScanService()
    with pytest.raises(ValueError, match="Plage trop large"):
        service.scan_range(
            start_ip="192.168.1.1",
            end_ip="192.168.1.10",
            max_hosts=5,
        )


def test_scan_range_uses_env_limit_when_max_hosts_not_provided(monkeypatch):
    service = NetworkScanService()
    monkeypatch.setenv("NMP_NETWORK_SCAN_MAX_IPS", "2")
    with pytest.raises(ValueError, match="Maximum autorise: 2"):
        service.scan_range(
            start_ip="192.168.1.1",
            end_ip="192.168.1.3",
        )
