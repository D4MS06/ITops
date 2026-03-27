from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class MacVendorService:
    """Resolve MAC OUI vendor names with a lightweight local cache."""

    def __init__(self, *, cache_path: Path | None = None, request_timeout_s: float = 1.2) -> None:
        self._cache_path = cache_path or Path(__file__).resolve().parents[1] / "storage" / "mac_vendor_cache.json"
        self._request_timeout_s = max(0.2, float(request_timeout_s))
        self._lock = threading.RLock()
        self._cache: dict[str, str] | None = None
        self._last_network_call_ts = 0.0

    @staticmethod
    def _oui_prefix(mac: str) -> str:
        raw = str(mac or "").strip().replace("-", ":").upper()
        if not raw:
            return ""
        parts = [part.zfill(2) for part in raw.split(":") if part]
        if len(parts) != 6:
            return ""
        if not all(len(part) == 2 and all(ch in "0123456789ABCDEF" for ch in part) for part in parts):
            return ""
        return ":".join(parts[:3])

    def oui_prefix(self, mac: str) -> str:
        return self._oui_prefix(mac)

    def _load_cache(self) -> dict[str, str]:
        if self._cache is not None:
            return self._cache
        path = self._cache_path
        if not path.exists():
            self._cache = {}
            return self._cache
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                self._cache = {str(k): str(v) for k, v in payload.items()}
            else:
                self._cache = {}
        except Exception:
            self._cache = {}
        return self._cache

    def _save_cache(self) -> None:
        if self._cache is None:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _fetch_vendor(self, mac: str) -> tuple[str, bool]:
        url = "https://api.macvendors.com/" + urllib.parse.quote(str(mac or "").strip())
        req = urllib.request.Request(url, headers={"User-Agent": "NetworkMonitoringProject/1.0.8"})
        with self._lock:
            now = time.monotonic()
            wait_s = 0.35 - (now - self._last_network_call_ts)
            if wait_s > 0:
                time.sleep(wait_s)
            self._last_network_call_ts = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self._request_timeout_s) as resp:
                body = resp.read().decode("utf-8", errors="replace").strip()
                return str(body or ""), True
        except urllib.error.HTTPError as exc:
            code = int(getattr(exc, "code", 0))
            if code == 404:
                return "", True
            if code == 429:
                return "", False
            return "", False
        except Exception:
            return "", False

    def resolve(self, mac: str, *, allow_network: bool = True) -> str:
        prefix = self._oui_prefix(mac)
        if not prefix:
            return ""
        with self._lock:
            cache = self._load_cache()
            if prefix in cache:
                cached = str(cache.get(prefix, ""))
                if cached:
                    return cached
                if not bool(allow_network):
                    return ""
        if not bool(allow_network):
            return ""
        vendor, cacheable = self._fetch_vendor(mac)
        if not cacheable:
            return str(vendor or "")
        with self._lock:
            cache = self._load_cache()
            cache[prefix] = str(vendor or "")
            self._save_cache()
        return str(vendor or "")
