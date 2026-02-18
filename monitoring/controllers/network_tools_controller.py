from __future__ import annotations

import platform
import os
import shutil
import socket
import ssl
import subprocess
import urllib.parse
import urllib.request
from typing import Tuple


class NetworkToolsController:
    """Execute des diagnostics reseau pour une IP/URL."""

    @staticmethod
    def _windows_no_window_kwargs() -> dict:
        if not platform.system().lower().startswith("win"):
            return {}
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = 0  # SW_HIDE
        return {
            "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
            "startupinfo": startup_info,
        }

    @staticmethod
    def _resolve_system_command(cmd_name: str) -> str:
        """Retourne un chemin absolu de commande quand possible (fiable en exe)."""
        if not platform.system().lower().startswith("win"):
            return cmd_name

        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        candidates = [
            os.path.join(system_root, "System32", f"{cmd_name}.exe"),
            os.path.join(system_root, "Sysnative", f"{cmd_name}.exe"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return shutil.which(cmd_name) or cmd_name

    @staticmethod
    def _decode_bytes(raw: bytes) -> str:
        for encoding in ("utf-8", "cp850", "cp1252", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("latin-1", errors="replace")

    @classmethod
    def _run_command(cls, args: list[str], timeout: int = 20) -> Tuple[bool, str]:
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=False,
                timeout=timeout,
                check=False,
                **cls._windows_no_window_kwargs(),
            )
            raw = proc.stdout or proc.stderr or b""
            output = cls._decode_bytes(raw).strip()
            if not output:
                output = "Aucune sortie."
            return proc.returncode == 0, output
        except Exception as exc:
            return False, f"Erreur execution commande: {exc}"

    @classmethod
    def _run_command_stream(
        cls,
        args: list[str],
        on_line,
        timeout: int = 90,
        stop_event=None,
        on_start=None,
    ) -> bool:
        """Execute une commande et pousse la sortie ligne a ligne via callback."""
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                **cls._windows_no_window_kwargs(),
            )
            if on_start is not None:
                on_start(proc)
            assert proc.stdout is not None
            while True:
                if stop_event is not None and stop_event.is_set():
                    if proc.poll() is None:
                        proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except Exception:
                        if proc.poll() is None:
                            proc.kill()
                    return False

                raw = proc.stdout.readline()
                if not raw:
                    if proc.poll() is not None:
                        break
                    break
                line = cls._decode_bytes(raw).rstrip("\r\n")
                if line:
                    on_line(line)
            proc.wait(timeout=timeout)
            return proc.returncode == 0
        except Exception as exc:
            on_line(f"Erreur execution commande: {exc}")
            return False

    def ping(self, ip: str) -> Tuple[bool, str]:
        count_flag = "-n" if platform.system().lower().startswith("win") else "-c"
        cmd = self._resolve_system_command("ping")
        return self._run_command([cmd, count_flag, "4", ip], timeout=25)

    def stream_ping(self, ip: str, on_line, continuous: bool = False, stop_event=None, on_start=None) -> bool:
        is_win = platform.system().lower().startswith("win")
        ping_cmd = self._resolve_system_command("ping")
        if continuous:
            args = [ping_cmd, "-t", ip] if is_win else [ping_cmd, ip]
            timeout = 86400
        else:
            args = [ping_cmd, "-n", "4", ip] if is_win else [ping_cmd, "-c", "4", ip]
            timeout = 35
        return self._run_command_stream(
            args,
            on_line,
            timeout=timeout,
            stop_event=stop_event,
            on_start=on_start,
        )

    def traceroute(self, ip: str) -> Tuple[bool, str]:
        cmd = self._resolve_system_command("tracert") if platform.system().lower().startswith("win") else "traceroute"
        return self._run_command([cmd, ip], timeout=60)

    def stream_traceroute(self, ip: str, on_line) -> bool:
        cmd = self._resolve_system_command("tracert") if platform.system().lower().startswith("win") else "traceroute"
        return self._run_command_stream([cmd, ip], on_line, timeout=120)

    def dns_lookup(self, target: str) -> Tuple[bool, str]:
        cmd = self._resolve_system_command("nslookup")
        return self._run_command([cmd, target], timeout=20)

    def stream_dns_lookup(self, target: str, on_line) -> bool:
        cmd = self._resolve_system_command("nslookup")
        return self._run_command_stream([cmd, target], on_line, timeout=30)

    @staticmethod
    def port_check(ip: str, port: int, timeout: float = 2.0) -> Tuple[bool, str]:
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True, f"Port {port} ouvert sur {ip}."
        except Exception as exc:
            return False, f"Port {port} ferme/injoignable sur {ip}: {exc}"

    @staticmethod
    def http_check(url: str, timeout: int = 8) -> Tuple[bool, str]:
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme:
            url = f"http://{url}"
            parsed = urllib.parse.urlparse(url)

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                lines = [f"URL: {url}", f"Code HTTP: {resp.status}", f"Reason: {resp.reason}"]
                if parsed.scheme.lower() == "https":
                    host = parsed.hostname or ""
                    port = parsed.port or 443
                    ctx = ssl.create_default_context()
                    with socket.create_connection((host, port), timeout=timeout) as sock:
                        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                            cert = ssock.getpeercert()
                    subject = cert.get("subject", "")
                    issuer = cert.get("issuer", "")
                    not_after = cert.get("notAfter", "")
                    lines.extend(
                        [
                            "Certificat TLS:",
                            f"- Subject: {subject}",
                            f"- Issuer: {issuer}",
                            f"- Expiration: {not_after}",
                        ]
                    )
                return True, "\n".join(lines)
        except Exception as exc:
            return False, f"Echec HTTP(S) check pour {url}: {exc}"

    def snmp_check(self, ip: str, community: str, oid: str) -> Tuple[bool, str]:
        if shutil.which("snmpget"):
            return self._run_command(
                ["snmpget", "-v2c", "-c", community, ip, oid],
                timeout=20,
            )
        return (
            False,
            "SNMP indisponible: commande 'snmpget' introuvable. "
            "Installez net-snmp ou adaptez l'environnement.",
        )
