from __future__ import annotations

from typing import Iterable

PLATFORM_OPTIONS = ["Windows", "Linux", "Firmware", "Autre"]
DEFAULT_PLATFORM_KEYS = {"windows", "linux", "firmware", "autre"}


def normalize_platform(value: str) -> str:
    raw = str(value or "").replace(",", " ").strip().lower()
    raw = " ".join(raw.split())
    return raw or "autre"


def parse_os_scope(raw_scope: str) -> set[str]:
    return {normalize_platform(v) for v in str(raw_scope or "").split(",") if str(v).strip()}


def action_allows_os(raw_scope: str, platform: str) -> bool:
    scope = parse_os_scope(raw_scope)
    if not scope:
        return True
    normalized_platform = normalize_platform(platform)
    if normalized_platform in scope:
        return True
    return normalized_platform not in DEFAULT_PLATFORM_KEYS and "autre" in scope


def format_os_scope(scope_values: Iterable[str]) -> str:
    ordered = []
    seen: set[str] = set()
    for item in scope_values:
        raw = str(item or "").strip()
        if not raw:
            continue
        key = normalize_platform(raw)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ",".join(ordered)
