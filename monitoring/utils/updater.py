from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

from monitoring.config.settings import NotificationSettings

GITHUB_API_BASE = "https://api.github.com"


@dataclass
class UpdateInfo:
    version: str
    release_name: str
    release_notes: str
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


def _fetch_releases(settings: NotificationSettings) -> list[dict]:
    owner = settings.github_owner.strip()
    repo = settings.github_repo.strip()
    token = (settings.github_token or "").strip()
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
    req = urllib.request.Request(url, headers=_github_headers(token, accept_json=True))
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, list):
        return []
    return payload


def find_available_update(current_version: str, settings: NotificationSettings) -> Optional[UpdateInfo]:
    if not settings.updates_enabled:
        return None
    if not settings.github_owner.strip() or not settings.github_repo.strip():
        return None

    releases = _fetch_releases(settings)
    include_prerelease = bool(settings.include_prerelease)
    chosen = None
    for rel in releases:
        if not isinstance(rel, dict):
            continue
        if rel.get("draft", False):
            continue
        if rel.get("prerelease", False) and not include_prerelease:
            continue
        chosen = rel
        break

    if not chosen:
        return None

    version = str(chosen.get("tag_name") or "").strip().lstrip("v")
    if not version or not is_newer_version(current_version, version):
        return None

    assets = chosen.get("assets") or []
    asset = None
    for it in assets:
        name = str(it.get("name") or "")
        if name.lower().endswith(".exe") and "setup" in name.lower():
            asset = it
            break
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    with open(path, "wb") as f:
        f.write(data)
    return path


def file_sha256(path: str) -> str:
    h = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
