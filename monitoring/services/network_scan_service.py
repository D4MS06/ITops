from __future__ import annotations

import ipaddress
import platform
import re
import socket
import subprocess
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Callable

from monitoring.services.mac_vendor_service import MacVendorService


class NetworkScanService:
    """Simple IPv4 LAN scanner for desktop workflows."""
    DEFAULT_TCP_PORTS = (22, 80, 443, 445, 3389)

    def __init__(self, *, mac_vendor_service: MacVendorService | None = None) -> None:
        self._mac_vendor_service = mac_vendor_service or MacVendorService()

    @staticmethod
    def vlan_to_range(vlan_id: int) -> tuple[str, str]:
        vlan = int(vlan_id)
        if vlan < 0 or vlan > 255:
            raise ValueError("VLAN invalide: attendu 0..255")
        return f"192.168.{vlan}.1", f"192.168.{vlan}.254"

    @staticmethod
    def normalize_range(start_ip: str, end_ip: str) -> tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]:
        start = ipaddress.ip_address(str(start_ip).strip())
        end = ipaddress.ip_address(str(end_ip).strip())
        if not isinstance(start, ipaddress.IPv4Address) or not isinstance(end, ipaddress.IPv4Address):
            raise ValueError("Plage IPv4 uniquement.")
        if int(start) > int(end):
            raise ValueError("Plage invalide: debut > fin.")
        return start, end

    @staticmethod
    def _windows_no_window_kwargs() -> dict:
        if not platform.system().lower().startswith("win"):
            return {}
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = 0
        return {
            "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
            "startupinfo": startup_info,
        }

    @staticmethod
    def _ping_args(ip: str, timeout_ms: int) -> list[str]:
        if platform.system().lower().startswith("win"):
            return ["ping", "-n", "1", "-w", str(max(100, int(timeout_ms))), str(ip)]
        timeout_s = max(1, int(round(float(timeout_ms) / 1000.0)))
        return ["ping", "-c", "1", "-W", str(timeout_s), str(ip)]

    @classmethod
    def _ping_host(cls, ip: str, timeout_ms: int) -> bool:
        try:
            proc = subprocess.run(
                cls._ping_args(ip, timeout_ms),
                capture_output=True,
                text=False,
                timeout=max(2.0, float(timeout_ms) / 1000.0 + 1.5),
                check=False,
                **cls._windows_no_window_kwargs(),
            )
            return proc.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _tcp_probe(ip: str, port: int, timeout_ms: int) -> bool:
        timeout_s = max(0.15, float(timeout_ms) / 1000.0)
        try:
            with socket.create_connection((str(ip), int(port)), timeout=timeout_s):
                return True
        except Exception:
            return False

    @classmethod
    def _probe_host(cls, ip: str, timeout_ms: int, tcp_ports: tuple[int, ...]) -> tuple[bool, str]:
        if cls._ping_host(ip, timeout_ms):
            return True, "icmp"
        for port in tcp_ports:
            if cls._tcp_probe(ip, int(port), timeout_ms):
                return True, f"tcp:{int(port)}"
        return False, ""

    @staticmethod
    def _normalize_mac(raw: str) -> str:
        text = str(raw or "").strip().replace("-", ":").upper()
        if not text:
            return ""
        parts = [part.zfill(2) for part in text.split(":") if part]
        if len(parts) != 6:
            return ""
        return ":".join(parts)

    @classmethod
    def parse_arp_table(cls, raw_text: str) -> dict[str, str]:
        mapping: dict[str, str] = {}
        pattern = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9A-Fa-f:-]{11,17})")
        for match in pattern.finditer(str(raw_text or "")):
            ip = str(match.group(1))
            mac = cls._normalize_mac(match.group(2))
            if mac:
                mapping[ip] = mac
        return mapping

    @classmethod
    def _arp_table(cls) -> dict[str, str]:
        try:
            proc = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
                **cls._windows_no_window_kwargs(),
            )
        except Exception:
            return {}
        output = str(proc.stdout or "") + "\n" + str(proc.stderr or "")
        return cls.parse_arp_table(output)

    @staticmethod
    def _netbios_name(ip: str) -> str:
        try:
            proc = subprocess.run(
                ["nbtstat", "-A", str(ip)],
                capture_output=True,
                text=True,
                timeout=1.8,
                check=False,
                **NetworkScanService._windows_no_window_kwargs(),
            )
        except Exception:
            return ""
        output = str(proc.stdout or "") + "\n" + str(proc.stderr or "")
        # Example line:
        # MYPC            <00>  UNIQUE      Registered
        pattern = re.compile(r"^\s*([^\s<][^<\r\n]{0,63})\s+<00>\s+UNIQUE", re.IGNORECASE | re.MULTILINE)
        m = pattern.search(output)
        return str(m.group(1)).strip() if m else ""

    @classmethod
    def _ping_name(cls, ip: str) -> str:
        if not platform.system().lower().startswith("win"):
            return ""
        try:
            proc = subprocess.run(
                ["ping", "-a", "-n", "1", "-w", "700", str(ip)],
                capture_output=True,
                text=True,
                timeout=2.2,
                check=False,
                **cls._windows_no_window_kwargs(),
            )
        except Exception:
            return ""
        output = str(proc.stdout or "")
        # Example: Envoi d'une requete 'ping' sur MYPC [192.168.1.10] ...
        pattern = re.compile(r"ping(?:\s+sur)?\s+([^\[\r\n]+)\s*\[", re.IGNORECASE)
        m = pattern.search(output)
        if not m:
            return ""
        candidate = str(m.group(1) or "").strip()
        if not candidate or candidate == str(ip):
            return ""
        return candidate

    @staticmethod
    def _hostname(ip: str, timeout_ms: int = 450) -> str:
        result: dict[str, str] = {"host": ""}

        def _lookup() -> None:
            try:
                host, _aliases, _ips = socket.gethostbyaddr(str(ip))
                result["host"] = str(host or "").strip()
            except Exception:
                result["host"] = ""

        t = threading.Thread(target=_lookup, daemon=True)
        t.start()
        t.join(timeout=max(0.15, float(timeout_ms) / 1000.0))
        host = str(result.get("host", "") or "")
        if host:
            return host
        ping_name = NetworkScanService._ping_name(ip)
        if ping_name:
            return ping_name
        return NetworkScanService._netbios_name(ip)

    @classmethod
    def _arp_entry_for_ip(cls, ip: str) -> str:
        try:
            proc = subprocess.run(
                ["arp", "-a", str(ip)],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
                **cls._windows_no_window_kwargs(),
            )
        except Exception:
            return ""
        output = str(proc.stdout or "") + "\n" + str(proc.stderr or "")
        return str(cls.parse_arp_table(output).get(str(ip), ""))

    def scan_range(
        self,
        *,
        start_ip: str,
        end_ip: str,
        timeout_ms: int = 800,
        max_workers: int = 16,
        tcp_ports: tuple[int, ...] | None = None,
        allow_vendor_network: bool = False,
        stop_event=None,
        progress_cb: Callable[[int, int], None] | None = None,
        report_cb: Callable[[dict], None] | None = None,
    ) -> list[dict]:
        if stop_event is not None and stop_event.is_set():
            return []

        start, end = self.normalize_range(start_ip, end_ip)
        ips = [str(ipaddress.IPv4Address(value)) for value in range(int(start), int(end) + 1)]
        ip_set = set(ips)
        total = len(ips)
        done = 0
        alive_set: set[str] = set()
        detected_by: dict[str, str] = {}
        workers = max(4, min(int(max_workers), 256))
        ports = tuple(int(p) for p in (tcp_ports or self.DEFAULT_TCP_PORTS))
        arp_map = self._arp_table()
        emitted: set[str] = set()

        def _emit(ip: str, *, status: str, host: str = "", mac: str = "", vendor: str = "") -> None:
            if not callable(report_cb):
                return
            row = {
                "ip": str(ip),
                "hostname": str(host or ""),
                "mac": str(mac or ""),
                "vendor": str(vendor or ""),
                "status": str(status or "up"),
            }
            report_cb(row)

        executor = ThreadPoolExecutor(max_workers=workers)
        try:
            futures_to_ip = {executor.submit(self._probe_host, ip, int(timeout_ms), ports): ip for ip in ips}
            pending = set(futures_to_ip.keys())
            while pending:
                if stop_event is not None and stop_event.is_set():
                    for future in pending:
                        future.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)
                    return []
                done_set, pending = wait(pending, timeout=0.15, return_when=FIRST_COMPLETED)
                if not done_set:
                    continue
                for future in done_set:
                    ip = futures_to_ip[future]
                    ok = False
                    reason = ""
                    try:
                        ok, reason = future.result()
                    except Exception:
                        ok = False
                        reason = ""
                    if ok:
                        alive_set.add(ip)
                        detected_by[ip] = reason or "up"
                        if ip not in emitted:
                            emitted.add(ip)
                            _emit(ip, status=detected_by[ip], mac=arp_map.get(ip, ""))
                    done += 1
                    if callable(progress_cb):
                        progress_cb(done, total)
        finally:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

        if stop_event is not None and stop_event.is_set():
            return []

        for _ in range(3):
            if stop_event is not None and stop_event.is_set():
                return []
            arp_map.update(self._arp_table())
            if all((ip in arp_map) for ip in alive_set):
                break
            time.sleep(0.15)
        for ip in ip_set.intersection(arp_map.keys()):
            if ip not in alive_set:
                alive_set.add(ip)
                detected_by[ip] = "arp"
            if ip not in emitted:
                emitted.add(ip)
                _emit(ip, status=detected_by.get(ip, "arp"), mac=arp_map.get(ip, ""))

        rows: list[dict] = []
        alive_sorted = sorted(alive_set, key=lambda item: tuple(int(part) for part in item.split(".")))
        enrich_total = total + len(alive_sorted)
        if callable(progress_cb):
            progress_cb(done, max(1, enrich_total))

        def _enrich(ip: str) -> dict:
            mac = str(arp_map.get(ip, ""))
            if not mac:
                mac = self._arp_entry_for_ip(ip)
                if mac:
                    arp_map[ip] = mac
            hostname = self._hostname(ip)
            return {
                "ip": ip,
                "hostname": hostname,
                "mac": mac,
                "vendor": "",
                "status": detected_by.get(ip, "up"),
            }

        enrich_done = 0
        enrich_workers = max(2, min(24, workers))
        enrich_executor = ThreadPoolExecutor(max_workers=enrich_workers)
        try:
            futures_to_ip = {enrich_executor.submit(_enrich, ip): ip for ip in alive_sorted}
            pending = set(futures_to_ip.keys())
            while pending:
                if stop_event is not None and stop_event.is_set():
                    for future in pending:
                        future.cancel()
                    enrich_executor.shutdown(wait=False, cancel_futures=True)
                    return []
                done_set, pending = wait(pending, timeout=0.15, return_when=FIRST_COMPLETED)
                if not done_set:
                    continue
                for future in done_set:
                    ip = futures_to_ip[future]
                    try:
                        row = dict(future.result())
                    except Exception:
                        row = {
                            "ip": ip,
                            "hostname": "",
                            "mac": str(arp_map.get(ip, "")),
                            "vendor": "",
                            "status": detected_by.get(ip, "up"),
                        }
                    rows.append(row)
                    _emit(
                        ip,
                        status=str(row.get("status", "up")),
                        host=str(row.get("hostname", "")),
                        mac=str(row.get("mac", "")),
                        vendor=str(row.get("vendor", "")),
                    )
                    enrich_done += 1
                    if callable(progress_cb):
                        progress_cb(total + enrich_done, max(1, enrich_total))
        finally:
            try:
                enrich_executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

        # Vendor enrichment by unique OUI prefix to avoid redundant online calls.
        prefix_to_rows: dict[str, list[int]] = {}
        prefix_to_mac: dict[str, str] = {}
        for index, row in enumerate(rows):
            mac = str(row.get("mac", ""))
            prefix = self._mac_vendor_service.oui_prefix(mac)
            if not prefix:
                continue
            prefix_to_rows.setdefault(prefix, []).append(index)
            prefix_to_mac.setdefault(prefix, mac)
        prefixes = list(prefix_to_rows.keys())
        if prefixes:
            base_done = total + enrich_done
            final_total = enrich_total + len(prefixes)
            if callable(progress_cb):
                progress_cb(base_done, max(1, final_total))
            vendor_workers = 1
            vendor_executor = ThreadPoolExecutor(max_workers=vendor_workers)
            try:
                futures_to_prefix = {
                    vendor_executor.submit(
                        self._mac_vendor_service.resolve,
                        prefix_to_mac.get(prefix, ""),
                        allow_network=bool(allow_vendor_network),
                    ): prefix
                    for prefix in prefixes
                }
                pending = set(futures_to_prefix.keys())
                vendor_done = 0
                while pending:
                    if stop_event is not None and stop_event.is_set():
                        for future in pending:
                            future.cancel()
                        vendor_executor.shutdown(wait=False, cancel_futures=True)
                        return []
                    done_set, pending = wait(pending, timeout=0.15, return_when=FIRST_COMPLETED)
                    if not done_set:
                        continue
                    for future in done_set:
                        prefix = futures_to_prefix[future]
                        try:
                            vendor = str(future.result() or "")
                        except Exception:
                            vendor = ""
                        for idx in prefix_to_rows.get(prefix, []):
                            rows[idx]["vendor"] = vendor
                            row = rows[idx]
                            _emit(
                                str(row.get("ip", "")),
                                status=str(row.get("status", "up")),
                                host=str(row.get("hostname", "")),
                                mac=str(row.get("mac", "")),
                                vendor=vendor,
                            )
                        vendor_done += 1
                        if callable(progress_cb):
                            progress_cb(base_done + vendor_done, max(1, final_total))
            finally:
                try:
                    vendor_executor.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
        rows.sort(key=lambda item: tuple(int(part) for part in str(item.get("ip", "")).split(".")))
        return rows
