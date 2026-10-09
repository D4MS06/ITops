from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path
import re
import weakref
from typing import Callable

_HOOKS: dict[int, dict] = {}
LOGGER = logging.getLogger(__name__)


def _decode_path(raw) -> str:
    if isinstance(raw, bytes):
        for enc in ("utf-8", "mbcs", "latin-1"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        text = raw.decode(errors="ignore")
    else:
        text = str(raw)
    text = text.strip()
    # Explorer drag-drop can wrap paths with braces when spaces are present.
    if text.startswith("{") and text.endswith("}") and "} {" not in text and "}\t{" not in text:
        text = text[1:-1].strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    return text


def decode_dropped_paths(raw_items) -> list[Path]:
    paths: list[Path] = []
    for item in raw_items or []:
        text = _decode_path(item)
        if not text:
            continue
        chunks: list[str] = []
        if "\x00" in text:
            chunks.extend(part.strip() for part in text.split("\x00") if part.strip())
        elif text.startswith("{") and "} {" in text:
            for match in re.finditer(r"\{([^}]*)\}|([^\s]+)", text):
                token = (match.group(1) or match.group(2) or "").strip()
                if token:
                    chunks.append(token)
        else:
            chunks.append(text)
        for token in chunks:
            normalized = _decode_path(token)
            if not normalized:
                continue
            path = Path(normalized).expanduser()
            if path.is_file():
                paths.append(path)
    return paths


def _allow_uac_drop_messages(hwnd: int) -> None:
    if not hwnd:
        return
    if str(os.name).lower() != "nt":
        return
    try:
        change_filter = getattr(ctypes.windll.user32, "ChangeWindowMessageFilterEx", None)  # type: ignore[attr-defined]
        if change_filter is None:
            return
        MSGFLT_ALLOW = 1
        for msg in (0x0233, 0x0049, 0x004A):  # WM_DROPFILES, WM_COPYGLOBALDATA, WM_COPYDATA
            try:
                change_filter(int(hwnd), int(msg), int(MSGFLT_ALLOW), None)
            except Exception:
                continue
    except Exception as exc:
        LOGGER.debug("UAC drop message filter setup skipped: %s", exc)


def hook_dropfiles(widget, callback: Callable[[list[Path], int, int], None]) -> bool:
    try:
        import windnd  # type: ignore
    except Exception:
        return False

    top = widget.winfo_toplevel()
    top_id = int(top.winfo_id())
    _allow_uac_drop_messages(top_id)
    bucket = _HOOKS.setdefault(top_id, {"targets": [], "hooked": False, "top_ref": weakref.ref(top)})
    bucket["targets"].append((weakref.ref(widget), callback))

    def _on_drop(files, *_args):
        try:
            top_obj = bucket["top_ref"]()
            if top_obj is None:
                return
            px = int(top_obj.winfo_pointerx())
            py = int(top_obj.winfo_pointery())
        except Exception:
            px, py = 0, 0
        paths = decode_dropped_paths(files)
        if not paths and files:
            # Last-resort decode path to support edge cases from shell extensions.
            for item in files or []:
                raw = _decode_path(item)
                if not raw:
                    continue
                candidate = Path(raw).expanduser()
                if candidate.is_file():
                    paths.append(candidate)
        if not paths:
            LOGGER.debug("Drop ignored: no valid file path parsed from payload=%r", files)
            return

        alive_targets = []
        for wref, cb in bucket["targets"]:
            w = wref()
            if w is None:
                continue
            try:
                if not bool(w.winfo_exists()) or not bool(w.winfo_ismapped()):
                    continue
            except Exception:
                continue
            alive_targets.append((wref, cb))
        bucket["targets"] = alive_targets

        # Route vers le widget actuellement sous le pointeur.
        for wref, cb in reversed(bucket["targets"]):
            w = wref()
            if w is None:
                continue
            try:
                x0 = int(w.winfo_rootx())
                y0 = int(w.winfo_rooty())
                x1 = x0 + int(w.winfo_width())
                y1 = y0 + int(w.winfo_height())
            except Exception:
                continue
            if x0 <= px < x1 and y0 <= py < y1:
                try:
                    cb(paths, px, py)
                except Exception as exc:
                    LOGGER.exception("Drop callback failed for widget=%r: %s", w, exc)
                return

        # Fallback: if pointer routing misses, use the latest alive target.
        if bucket["targets"]:
            wref, cb = bucket["targets"][0]
            w = wref()
            if w is not None:
                try:
                    cb(paths, px, py)
                except Exception as exc:
                    LOGGER.exception("Drop callback fallback failed for widget=%r: %s", w, exc)
                return

    try:
        if not bool(bucket.get("hooked", False)):
            windnd.hook_dropfiles(top, func=_on_drop, force_unicode=True)
            bucket["hooked"] = True
        return True
    except Exception:
        return False
