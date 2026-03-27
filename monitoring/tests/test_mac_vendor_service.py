from __future__ import annotations

from pathlib import Path

from monitoring.services.mac_vendor_service import MacVendorService


def test_oui_prefix_normalization():
    assert MacVendorService._oui_prefix("aa-bb-cc-dd-ee-ff") == "AA:BB:CC"
    assert MacVendorService._oui_prefix("11:22:33:44:55:66") == "11:22:33"
    assert MacVendorService._oui_prefix("invalid") == ""


def test_resolve_uses_cache_without_network(monkeypatch, tmp_path: Path):
    cache_path = tmp_path / "mac_vendor_cache.json"
    cache_path.write_text('{"AA:BB:CC": "Acme Corp"}', encoding="utf-8")
    svc = MacVendorService(cache_path=cache_path)

    def _fail_fetch(_self, _mac):
        raise AssertionError("_fetch_vendor should not be called on cache hit")

    monkeypatch.setattr(MacVendorService, "_fetch_vendor", _fail_fetch)
    assert svc.resolve("AA:BB:CC:DD:EE:FF") == "Acme Corp"


def test_resolve_cache_only_skips_network_on_miss(monkeypatch, tmp_path: Path):
    svc = MacVendorService(cache_path=tmp_path / "mac_vendor_cache.json")

    def _fail_fetch(_self, _mac):
        raise AssertionError("_fetch_vendor should not be called when allow_network=False")

    monkeypatch.setattr(MacVendorService, "_fetch_vendor", _fail_fetch)
    assert svc.resolve("AA:BB:CC:DD:EE:FF", allow_network=False) == ""


def test_resolve_does_not_cache_rate_limited_result(monkeypatch, tmp_path: Path):
    svc = MacVendorService(cache_path=tmp_path / "mac_vendor_cache.json")
    calls = {"count": 0}

    def _rate_limited(_self, _mac):
        calls["count"] += 1
        return "", False

    monkeypatch.setattr(MacVendorService, "_fetch_vendor", _rate_limited)
    assert svc.resolve("AA:BB:CC:DD:EE:FF", allow_network=True) == ""
    assert svc.resolve("AA:BB:CC:11:22:33", allow_network=True) == ""
    assert calls["count"] == 2


def test_resolve_retries_when_cached_value_is_empty(monkeypatch, tmp_path: Path):
    cache_path = tmp_path / "mac_vendor_cache.json"
    cache_path.write_text('{"AA:BB:CC": ""}', encoding="utf-8")
    svc = MacVendorService(cache_path=cache_path)

    def _fetch_ok(_self, _mac):
        return "Acme Corp", True

    monkeypatch.setattr(MacVendorService, "_fetch_vendor", _fetch_ok)
    assert svc.resolve("AA:BB:CC:DD:EE:FF", allow_network=True) == "Acme Corp"
