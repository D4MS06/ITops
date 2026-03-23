from __future__ import annotations

import base64
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from monitoring.config.settings import NotificationSettings


class CaddyManager:
    SERVICE_NAME = "NetworkMonitoringCaddy"
    FIREWALL_RULE_NAME = "NetworkMonitoring HTTPS"

    def __init__(self) -> None:
        self._program_data_dir = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "NetworkMonitoringProject" / "caddy"
        self._config_path = self._program_data_dir / "Caddyfile"
        self._shared_root_cert_path = self._program_data_dir / "certs" / "root.crt"

    def sync_from_settings(self, settings: NotificationSettings) -> None:
        public_url = str(getattr(settings, "web_server_public_url", "") or "").strip()
        use_public_url = bool(getattr(settings, "web_server_use_public_url", False))
        backend_host = str(getattr(settings, "web_server_host", "127.0.0.1") or "127.0.0.1").strip() or "127.0.0.1"
        backend_port = max(1, int(getattr(settings, "web_server_port", 8000) or 8000))

        if not use_public_url or not public_url:
            return

        if os.name != "nt":
            raise RuntimeError("La gestion automatique du proxy Caddy est actuellement disponible sur Windows uniquement.")

        parsed = urlparse(public_url if "://" in public_url else f"https://{public_url}")
        hostname = str(parsed.hostname or "").strip()
        if not hostname:
            raise RuntimeError("L'URL publique du serveur web est invalide.")

        caddy_exe = self._resolve_caddy_exe()
        self._program_data_dir.mkdir(parents=True, exist_ok=True)
        self._write_caddyfile(hostname=hostname, backend_host=backend_host, backend_port=backend_port)
        self._validate_config(caddy_exe)
        self._ensure_service(caddy_exe)
        self._ensure_firewall_rule()
        self._reload_or_restart(caddy_exe)
        try:
            self._refresh_exportable_root_certificate()
        except Exception:
            pass

    def locate_root_certificate(self) -> Path:
        candidates = [self._shared_root_cert_path, *self._root_certificate_source_candidates()]
        unreadable: list[Path] = []
        for candidate in candidates:
            if not candidate.is_file():
                continue
            try:
                with candidate.open("rb") as handle:
                    handle.read(1)
                return candidate
            except PermissionError:
                unreadable.append(candidate)
                continue
        if unreadable:
            raise PermissionError(
                "Le certificat racine Caddy existe mais n'est pas lisible depuis ce compte: "
                f"{unreadable[0]}"
            )
        raise RuntimeError("Le certificat racine Caddy est introuvable. Demarre d'abord le proxy HTTPS.")

    def export_root_certificate(self, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._refresh_exportable_root_certificate()
        except Exception:
            pass
        try:
            source = self.locate_root_certificate()
        except PermissionError as exc:
            try:
                refreshed = self._refresh_exportable_root_certificate()
                destination.write_bytes(refreshed.read_bytes())
                return destination
            except Exception:
                pass
            if self._export_root_certificate_from_windows_store(destination):
                return destination
            raise exc
        try:
            destination.write_bytes(source.read_bytes())
            return destination
        except PermissionError as exc:
            try:
                refreshed = self._refresh_exportable_root_certificate()
                destination.write_bytes(refreshed.read_bytes())
                return destination
            except Exception:
                pass
            if self._export_root_certificate_from_windows_store(destination):
                return destination
            raise exc
        return destination

    def _root_certificate_source_candidates(self) -> list[Path]:
        return [
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Caddy" / "pki" / "authorities" / "local" / "root.crt",
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "NetworkMonitoringProject" / "caddy" / "pki" / "authorities" / "local" / "root.crt",
            Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "config" / "systemprofile" / "AppData" / "Roaming" / "Caddy" / "pki" / "authorities" / "local" / "root.crt",
            Path.home() / "AppData" / "Roaming" / "Caddy" / "pki" / "authorities" / "local" / "root.crt",
        ]

    def _refresh_exportable_root_certificate(self) -> Path:
        target = self._shared_root_cert_path
        for source in self._root_certificate_source_candidates():
            if not source.is_file():
                continue
            try:
                raw = source.read_bytes()
            except PermissionError:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            self._ensure_shared_certificate_read_access(target)
            return target
        raise RuntimeError("Aucun certificat racine lisible n'a ete trouve pour l'export.")

    def _export_root_certificate_from_windows_store(self, destination: Path) -> bool:
        if os.name != "nt":
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination_literal = str(destination).replace("'", "''")
        script = "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                f"$dest = '{destination_literal}'",
                "$stores = @('Cert:\\LocalMachine\\Root', 'Cert:\\LocalMachine\\CA', 'Cert:\\CurrentUser\\Root')",
                "$cert = $null",
                "foreach ($store in $stores) {",
                "  try {",
                "    $candidate = Get-ChildItem -Path $store | Where-Object {",
                "      $_.Subject -like '*Caddy Local Authority*' -or $_.Issuer -like '*Caddy Local Authority*'",
                "    } | Sort-Object NotAfter -Descending | Select-Object -First 1",
                "    if ($candidate) {",
                "      $cert = $candidate",
                "      break",
                "    }",
                "  } catch { }",
                "}",
                "if (-not $cert) { exit 3 }",
                "[System.IO.File]::WriteAllBytes($dest, $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))",
            ]
        )
        encoded_script = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded_script,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return result.returncode == 0 and destination.is_file() and destination.stat().st_size > 0

    @staticmethod
    def _ensure_shared_certificate_read_access(path: Path) -> None:
        if os.name != "nt":
            return
        try:
            subprocess.run(
                ["icacls", str(path), "/grant", "*S-1-5-32-545:R", "/C"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except Exception:
            pass

    def _resolve_caddy_exe(self) -> Path:
        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            app_dir = Path(sys.executable).resolve().parent
            meipass = Path(getattr(sys, "_MEIPASS", app_dir))
            candidates.extend(
                [
                    app_dir / "_internal" / "tools" / "caddy" / "windows-amd64" / "caddy.exe",
                    meipass / "tools" / "caddy" / "windows-amd64" / "caddy.exe",
                ]
            )
        project_root = Path(__file__).resolve().parents[2]
        candidates.extend(
            [
                project_root / "tools" / "caddy-local" / "caddy.exe",
                project_root / "build_support" / "caddy" / "windows-amd64" / "caddy.exe",
            ]
        )

        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise RuntimeError("Le binaire Caddy est introuvable dans l'installation.")

    def _write_caddyfile(self, *, hostname: str, backend_host: str, backend_port: int) -> None:
        content = "\n".join(
            [
                f"{hostname} {{",
                "    encode gzip zstd",
                "    tls internal",
                f"    reverse_proxy {backend_host}:{backend_port}",
                "}",
                "",
            ]
        )
        self._config_path.write_text(content, encoding="ascii")

    def _validate_config(self, caddy_exe: Path) -> None:
        result = subprocess.run(
            [str(caddy_exe), "validate", "--config", str(self._config_path), "--adapter", "caddyfile"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"Configuration Caddy invalide: {stderr or 'validation impossible.'}")

    def _ensure_service(self, caddy_exe: Path) -> None:
        if self._service_exists():
            return
        bin_path = f'"{caddy_exe}" run --config "{self._config_path}" --adapter caddyfile'
        self._run(["sc.exe", "create", self.SERVICE_NAME, "binPath=", bin_path, "start=", "auto"])
        self._run(["sc.exe", "description", self.SERVICE_NAME, "Reverse proxy HTTPS NetworkMonitoringProject"])

    def _ensure_firewall_rule(self) -> None:
        check = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={self.FIREWALL_RULE_NAME}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if check.returncode == 0 and "Aucune règle ne correspond" not in (check.stdout or ""):
            return
        self._run(
            [
                "netsh",
                "advfirewall",
                "firewall",
                "add",
                "rule",
                f"name={self.FIREWALL_RULE_NAME}",
                "dir=in",
                "action=allow",
                "protocol=TCP",
                "localport=443",
            ]
        )

    def _reload_or_restart(self, caddy_exe: Path) -> None:
        reload_result = subprocess.run(
            [str(caddy_exe), "reload", "--config", str(self._config_path), "--adapter", "caddyfile"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if reload_result.returncode == 0:
            return

        self._run(["sc.exe", "stop", self.SERVICE_NAME], allow_failure=True)
        time.sleep(1.5)
        self._run(["sc.exe", "start", self.SERVICE_NAME])

    def _service_exists(self) -> bool:
        result = subprocess.run(
            ["sc.exe", "query", self.SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return result.returncode == 0

    @staticmethod
    def _run(command: list[str], *, allow_failure: bool = False) -> None:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        if allow_failure:
            return
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(stderr or f"Echec de la commande: {' '.join(command)}")
