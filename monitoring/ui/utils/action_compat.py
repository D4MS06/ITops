from __future__ import annotations

from typing import Iterable

PLATFORM_OPTIONS = ["Windows", "Linux", "Firmware", "Autre"]

def normalize_platform(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"windows", "linux", "firmware", "autre"}:
        return raw
    return "autre"


def parse_os_scope(raw_scope: str) -> set[str]:
    return {normalize_platform(v) for v in str(raw_scope or "").split(",") if str(v).strip()}


def action_allows_os(raw_scope: str, platform: str) -> bool:
    scope = parse_os_scope(raw_scope)
    if not scope:
        return True
    return normalize_platform(platform) in scope


def format_os_scope(scope_values: Iterable[str]) -> str:
    ordered = []
    seen: set[str] = set()
    for item in scope_values:
        key = normalize_platform(str(item))
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ",".join(ordered)
