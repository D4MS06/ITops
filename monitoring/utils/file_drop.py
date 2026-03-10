from __future__ import annotations

from pathlib import Path
import weakref
from typing import Callable

_HOOKS: dict[int, dict] = {}


def _decode_path(raw) -> str:
    if isinstance(raw, bytes):
        for enc in ("utf-8", "mbcs", "latin-1"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode(errors="ignore")
    return str(raw)


def hook_dropfiles(widget, callback: Callable[[list[Path], int, int], None]) -> bool:
    try:
        import windnd  # type: ignore
    except Exception:
        return False

    top = widget.winfo_toplevel()
    top_id = int(top.winfo_id())
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
        paths: list[Path] = []
        for item in files or []:
            path = Path(_decode_path(item)).expanduser()
            if path.is_file():
                paths.append(path)
        if not paths:
            return

        alive_targets = []
        for wref, cb in bucket["targets"]:
            w = wref()
            if w is None:
                continue
            try:
                if not bool(w.winfo_exists()):
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
                cb(paths, px, py)
                return

    try:
        if not bool(bucket.get("hooked", False)):
            windnd.hook_dropfiles(top, func=_on_drop)
            bucket["hooked"] = True
        return True
    except Exception:
        return False
