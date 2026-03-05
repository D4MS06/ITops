from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

DEFAULT_CONFIG_DIR_NAME = "switch_configs"


def default_switch_configs_dir() -> Path:
    app_data_root = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(app_data_root) / "NetworkMonitoringProject" / DEFAULT_CONFIG_DIR_NAME


def resolve_switch_configs_dir(configured_dir: str | None) -> Path:
    raw = str(configured_dir or "").strip()
    if raw:
        return Path(raw).expanduser()
    return default_switch_configs_dir()


def _normalize_token(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return "".join(ch if ch.isalnum() else "_" for ch in text)


def find_switch_config_files(
    root_dir: Path,
    switch_name: str,
    switch_ip: str,
    *,
    max_results: int = 20,
) -> list[Path]:
    root = Path(root_dir)
    if not root.is_dir():
        return []

    name_token = _normalize_token(switch_name)
    ip_token = str(switch_ip or "").strip().lower()
    ip_flat = "".join(ch for ch in ip_token if ch.isalnum())

    matches: list[tuple[int, float, Path]] = []
    for candidate in root.rglob("*"):
        if not candidate.is_file():
            continue

        file_name = candidate.name.lower()
        stem_token = _normalize_token(candidate.stem)
        flat_name = "".join(ch for ch in file_name if ch.isalnum())

        score = 0
        if ip_token and ip_token in file_name:
            score += 120
        if ip_flat and ip_flat and ip_flat in flat_name:
            score += 60
        if name_token and name_token in stem_token:
            score += 90
        if name_token and name_token in _normalize_token(str(candidate.parent)):
            score += 40
        if (ip_token or ip_flat) and name_token and score:
            score += 30

        if score <= 0:
            continue
        try:
            mtime = candidate.stat().st_mtime
        except OSError:
            mtime = 0.0
        matches.append((score, mtime, candidate))

    matches.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [item[2] for item in matches[:max_results]]


def open_path_with_default_app(path: Path) -> None:
    target = str(Path(path))
    if os.name == "nt":
        os.startfile(target)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", target], shell=False)
        return
    subprocess.Popen(["xdg-open", target], shell=False)
