from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import shutil
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

from monitoring.config.settings import NotificationSettings

GITHUB_API_BASE = "https://api.github.com"
GITHUB_OWNER = "D4MS06"
GITHUB_REPO = "NetworkMonitoringProject"


@dataclass
class UpdateInfo:
    version: str
    release_name: str
    release_notes: str
    asset_name: str
    asset_api_url: str


@dataclass
class ReleaseEntry:
    tag_name: str
    release_name: str
    prerelease: bool
    asset_name: str
    asset_api_url: str


def _version_key(version: str) -> tuple:
    clean = version.strip().lower().lstrip("v")
    parts = re.split(r"[.\-+_]", clean)
    out = []
    for p in parts:
        if p.isdigit():
            out.append((0, int(p)))
        else:
            out.append((1, p))
    return tuple(out)


def is_newer_version(current_version: str, candidate_version: str) -> bool:
    return _version_key(candidate_version) > _version_key(current_version)


def _github_headers(token: str, *, accept_json: bool = True) -> dict[str, str]:
    headers = {"User-Agent": "NetworkMonitoringProject-Updater"}
    headers["Accept"] = "application/vnd.github+json" if accept_json else "application/octet-stream"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _build_ssl_context_candidates() -> list[ssl.SSLContext]:
    """Retourne des contextes SSL compatibles (systeme, puis certifi si dispo)."""
    contexts: list[ssl.SSLContext] = []

    custom_cafile = (os.environ.get("SSL_CERT_FILE") or "").strip()
    if custom_cafile and os.path.isfile(custom_cafile):
        try:
            contexts.append(ssl.create_default_context(cafile=custom_cafile))
        except Exception:
            pass

    try:
        contexts.append(ssl.create_default_context())
    except Exception:
        pass

    try:
        import certifi  # type: ignore

        certifi_ctx = ssl.create_default_context(cafile=certifi.where())
        contexts.append(certifi_ctx)
    except Exception:
        pass

    # Evite les doublons de contexte.
    uniq: list[ssl.SSLContext] = []
    seen: set[int] = set()
    for ctx in contexts:
        key = id(ctx)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(ctx)
    return uniq


def _urlopen_with_ssl(req: urllib.request.Request, timeout: int):
    last_ssl_error: Exception | None = None
    for ctx in _build_ssl_context_candidates():
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        except ssl.SSLError as exc:
            last_ssl_error = exc
            continue
    if last_ssl_error is not None:
        raise last_ssl_error
    return urllib.request.urlopen(req, timeout=timeout)


def _is_ssl_failure(exc: Exception) -> bool:
    if isinstance(exc, ssl.SSLError):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, ssl.SSLError):
            return True
        if isinstance(reason, Exception):
            return _is_ssl_failure(reason)
        return "certificate_verify_failed" in str(reason).lower()
    return False


def _powershell_exe() -> str | None:
    for candidate in ("powershell", "pwsh"):
        exe = shutil.which(candidate)
        if exe:
            return exe
    return None


def _run_powershell(script: str) -> str:
    exe = _powershell_exe()
    if not exe:
        raise RuntimeError("PowerShell indisponible sur ce poste.")
    proc = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(stderr or "Echec PowerShell.")
    return (proc.stdout or "").strip()


def _ps_escape(value: str) -> str:
    return (value or "").replace("'", "''")


def _fetch_releases_via_powershell(settings: NotificationSettings) -> list[dict]:
    token = (settings.github_token or "").strip()
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
    auth_line = ""
    if token:
        auth_line = f"$headers['Authorization']='Bearer {_ps_escape(token)}';"
    script = (
        "$ProgressPreference='SilentlyContinue';"
        "$headers=@{};"
        "$headers['User-Agent']='NetworkMonitoringProject-Updater';"
        "$headers['Accept']='application/vnd.github+json';"
        f"{auth_line}"
        f"$resp=Invoke-RestMethod -Method GET -Uri '{_ps_escape(url)}' -Headers $headers;"
        "$resp | ConvertTo-Json -Depth 100 -Compress"
    )
    raw = _run_powershell(script)
    payload = json.loads(raw) if raw else []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    return []


def _download_asset_via_powershell(update: UpdateInfo, settings: NotificationSettings, path: str) -> None:
    token = (settings.github_token or "").strip()
    auth_line = ""
    if token:
        auth_line = f"$headers['Authorization']='Bearer {_ps_escape(token)}';"
    script = (
        "$ProgressPreference='SilentlyContinue';"
        "$headers=@{};"
        "$headers['User-Agent']='NetworkMonitoringProject-Updater';"
        "$headers['Accept']='application/octet-stream';"
        f"{auth_line}"
        f"Invoke-WebRequest -Method GET -Uri '{_ps_escape(update.asset_api_url)}' -Headers $headers -OutFile '{_ps_escape(path)}';"
        "Write-Output 'OK'"
    )
    _run_powershell(script)


def _fetch_releases(settings: NotificationSettings) -> list[dict]:
    token = (settings.github_token or "").strip()
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
    req = urllib.request.Request(url, headers=_github_headers(token, accept_json=True))
    try:
        with _urlopen_with_ssl(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        if os.name != "nt" or not _is_ssl_failure(exc):
            raise
        payload = _fetch_releases_via_powershell(settings)
    if not isinstance(payload, list):
        return []
    return payload


def _find_setup_asset(release_obj: dict) -> Optional[dict]:
    assets = release_obj.get("assets") or []
    for it in assets:
        name = str(it.get("name") or "")
        if name.lower().endswith(".exe") and "setup" in name.lower():
            return it
    return None


def list_installable_releases(settings: NotificationSettings) -> list[ReleaseEntry]:
    releases = _fetch_releases(settings)
    out: list[ReleaseEntry] = []
    for rel in releases:
        if not isinstance(rel, dict):
            continue
        if rel.get("draft", False):
            continue
        version = str(rel.get("tag_name") or "").strip()
        if not version:
            continue
        asset = _find_setup_asset(rel)
        if asset is None:
            continue
        out.append(
            ReleaseEntry(
                tag_name=version,
                release_name=str(rel.get("name") or version),
                prerelease=bool(rel.get("prerelease", False)),
                asset_name=str(asset.get("name") or ""),
                asset_api_url=str(asset.get("url") or ""),
            )
        )
    out.sort(key=lambda r: _version_key(r.tag_name), reverse=True)
    return out


def find_available_update(current_version: str, settings: NotificationSettings) -> Optional[UpdateInfo]:
    if not settings.updates_enabled:
        return None

    releases = _fetch_releases(settings)
    include_prerelease = bool(settings.include_prerelease)
    target_tag = str(getattr(settings, "update_target_tag", "latest") or "latest").strip()
    candidates: list[dict] = []

    if target_tag and target_tag.lower() != "latest":
        normalized_target = target_tag.lower().lstrip("v")
        for rel in releases:
            if not isinstance(rel, dict):
                continue
            if rel.get("draft", False):
                continue
            rel_tag = str(rel.get("tag_name") or "").strip()
            if not rel_tag:
                continue
            if rel_tag.lower().lstrip("v") != normalized_target:
                continue
            if rel.get("prerelease", False) and not include_prerelease:
                # Explicit target tag wins over prerelease toggle.
                pass
            version = rel_tag.lstrip("v")
            if not is_newer_version(current_version, version):
                return None
            asset = _find_setup_asset(rel)
            if asset is None:
                return None
            return UpdateInfo(
                version=version,
                release_name=str(rel.get("name") or rel.get("tag_name") or f"v{version}"),
                release_notes=str(rel.get("body") or "").strip(),
                asset_name=str(asset.get("name") or ""),
                asset_api_url=str(asset.get("url") or ""),
            )
        return None

    for rel in releases:
        if not isinstance(rel, dict):
            continue
        if rel.get("draft", False):
            continue
        if rel.get("prerelease", False) and not include_prerelease:
            continue
        version = str(rel.get("tag_name") or "").strip().lstrip("v")
        if not version:
            continue
        if not is_newer_version(current_version, version):
            continue
        candidates.append(rel)

    if not candidates:
        return None

    chosen = max(
        candidates,
        key=lambda r: _version_key(str(r.get("tag_name") or "").strip().lstrip("v")),
    )

    version = str(chosen.get("tag_name") or "").strip().lstrip("v")
    if not version:
        return None

    asset = _find_setup_asset(chosen)
    if asset is None:
        return None

    return UpdateInfo(
        version=version,
        release_name=str(chosen.get("name") or chosen.get("tag_name") or f"v{version}"),
        release_notes=str(chosen.get("body") or "").strip(),
        asset_name=str(asset.get("name") or ""),
        asset_api_url=str(asset.get("url") or ""),
    )


def download_update_asset(update: UpdateInfo, settings: NotificationSettings) -> str:
    token = (settings.github_token or "").strip()
    if not token:
        raise RuntimeError("Token GitHub manquant.")
    req = urllib.request.Request(
        update.asset_api_url,
        headers=_github_headers(token, accept_json=False),
    )
    fd, path = tempfile.mkstemp(prefix="nmp-update-", suffix=".exe")
    os.close(fd)
    try:
        with _urlopen_with_ssl(req, timeout=60) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
    except Exception as exc:
        if os.name != "nt" or not _is_ssl_failure(exc):
            raise
        _download_asset_via_powershell(update, settings, path)
    return path


def file_sha256(path: str) -> str:
    h = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
