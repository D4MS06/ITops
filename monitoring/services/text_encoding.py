"""Safe detection and repair of legacy UTF-8 mojibake."""

from __future__ import annotations

import re


_MOJIBAKE_MARKERS = re.compile(r"[ÃÂ�]")


def repair_legacy_utf8_mojibake(value: object) -> str:
    """Return a repaired value only when legacy decoding markers decrease."""
    repaired = str(value or "")
    for _index in range(3):
        before_markers = len(_MOJIBAKE_MARKERS.findall(repaired))
        if not before_markers:
            break
        candidates: list[str] = []
        for encoding in ("cp1252", "latin-1"):
            try:
                candidates.append(repaired.encode(encoding).decode("utf-8"))
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
        if not candidates:
            break
        candidate = min(candidates, key=lambda item: len(_MOJIBAKE_MARKERS.findall(item)))
        if len(_MOJIBAKE_MARKERS.findall(candidate)) >= before_markers:
            break
        repaired = candidate
    return repaired


def has_repairable_legacy_utf8_mojibake(value: object) -> bool:
    return repair_legacy_utf8_mojibake(value) != str(value or "")
