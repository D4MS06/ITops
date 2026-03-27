from __future__ import annotations

import ipaddress
import platform
import re
import socket
import subprocess
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Callable

from monitoring.services.mac_vendor_service import MacVendorService


class L3RouterScanService:
    """Collecte d'hotes via table ARP d'un equipement L3 (routeur/switch)."""

    def __init__(self, *, mac_vendor_service: MacVendorService | None = None) -> None:
        self._mac_vendor_service = mac_vendor_service or MacVendorService()

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
    def _normalize_mac(raw: str) -> str:
        text = str(raw or "").strip().lower().replace("-", "").replace(":", "").replace(".", "")
        if len(text) != 12 or not all(ch in "0123456789abcdef" for ch in text):
            return ""
        groups = [text[i : i + 2].upper() for i in range(0, 12, 2)]
        return ":".join(groups)

    @classmethod
    def parse_arp_output(cls, raw_text: str) -> list[dict]:
        rows: list[dict] = []
        seen: set[str] = set()
        pattern = re.compile(
            r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).{0,80}?(?P<mac>(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})"
        )
        for line in str(raw_text or "").splitlines():
            m = pattern.search(line)
            if not m:
                continue
            ip = str(m.group("ip") or "").strip()
            mac = cls._normalize_mac(m.group("mac") or "")
            if not ip or not mac:
                continue
            try:
                ipaddress.ip_address(ip)
            except Exception:
                continue
            if ip in seen:
                continue
            seen.add(ip)
            iface_match = re.search(
                r"\b(Vlan-?interface\d+|Vlan\d+|VLAN\d+|br\d+|bond\d+|eth\d+|XGE\d+/\d+/\d+|GE\d+/\d+/\d+)\b",
                line,
                re.IGNORECASE,
            )
            rows.append(
                {
                    "ip": ip,
                    "mac": mac,
                    "iface": str(iface_match.group(1) if iface_match else "").strip(),
                }
            )
        return rows

    @classmethod
    def _fetch_arp_text(cls, *, host: str, ssh_user: str, command: str, timeout_s: int = 20) -> str:
        target = f"{str(ssh_user).strip()}@{str(host).strip()}" if str(ssh_user).strip() else str(host).strip()
        if not target:
            raise ValueError("Equipement L3 manquant.")
        cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=8",
            target,
            str(command or "show ip arp"),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(8, int(timeout_s)),
            check=False,
            **cls._windows_no_window_kwargs(),
        )
        stdout = str(proc.stdout or "")
        stderr = str(proc.stderr or "")
        if int(proc.returncode) != 0 and not stdout.strip():
            if "Permission denied" in stderr:
                raise RuntimeError("Echec SSH: auth refusee. Configurez une cle SSH.")
            raise RuntimeError(f"Echec SSH ({proc.returncode}): {stderr.strip() or 'commande impossible'}")
        return stdout + ("\n" + stderr if stderr.strip() else "")

    @staticmethod
    def _hostname(ip: str) -> str:
        try:
            host, _aliases, _ips = socket.gethostbyaddr(str(ip))
            return str(host or "").strip()
        except Exception:
            return ""

    @staticmethod
    def _in_range(ip: str, start_ip: str | None, end_ip: str | None) -> bool:
        if not start_ip or not end_ip:
            return True
        try:
            value = int(ipaddress.ip_address(str(ip)))
            start = int(ipaddress.ip_address(str(start_ip)))
            end = int(ipaddress.ip_address(str(end_ip)))
            return start <= value <= end
        except Exception:
            return False

    def scan_router_arp(
        self,
        *,
        host: str,
        ssh_user: str,
        command: str = "show ip arp",
        start_ip: str | None = None,
        end_ip: str | None = None,
        allow_vendor_network: bool = False,
        stop_event=None,
        progress_cb: Callable[[int, int], None] | None = None,
        report_cb: Callable[[dict], None] | None = None,
    ) -> list[dict]:
        if stop_event is not None and stop_event.is_set():
            return []
        raw = self._fetch_arp_text(host=host, ssh_user=ssh_user, command=command)
        rows = self.parse_arp_output(raw)
        if start_ip and end_ip:
            rows = [row for row in rows if self._in_range(str(row.get("ip", "")), start_ip, end_ip)]
        total = len(rows)
        if callable(progress_cb):
            progress_cb(0, max(1, total))

        def _emit(row: dict) -> None:
            if callable(report_cb):
                report_cb(dict(row))

        result: list[dict] = []
        if total == 0:
            if callable(progress_cb):
                progress_cb(1, 1)
            return result

        def _enrich(base: dict) -> dict:
            ip = str(base.get("ip", ""))
            mac = str(base.get("mac", ""))
            return {
                "ip": ip,
                "hostname": self._hostname(ip),
                "vendor": self._mac_vendor_service.resolve(mac, allow_network=bool(allow_vendor_network)) if mac else "",
                "mac": mac,
                "iface": str(base.get("iface", "")),
                "status": "l3-arp",
            }

        done = 0
        executor = ThreadPoolExecutor(max_workers=min(16, max(2, total)))
        try:
            futures = {executor.submit(_enrich, base): dict(base) for base in rows}
            pending = set(futures.keys())
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
                    base = futures[future]
                    try:
                        row = dict(future.result())
                    except Exception:
                        row = {
                            "ip": str(base.get("ip", "")),
                            "hostname": "",
                            "vendor": "",
                            "mac": str(base.get("mac", "")),
                            "iface": str(base.get("iface", "")),
                            "status": "l3-arp",
                        }
                    result.append(row)
                    _emit(row)
                    done += 1
                    if callable(progress_cb):
                        progress_cb(done, max(1, total))
        finally:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
        result.sort(key=lambda item: tuple(int(part) for part in str(item.get("ip", "")).split(".")))
        return result
