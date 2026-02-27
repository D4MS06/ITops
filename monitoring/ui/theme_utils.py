from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


def _control_tokens(colors: dict[str, str]) -> dict[str, str]:
    return {
        "bg": colors.get("control_bg", colors.get("button_inactive_bg", "#e2e8f0")),
        "fg": colors.get("control_fg", colors.get("button_inactive_fg", "#0f172a")),
        "border": colors.get("control_border", colors.get("placeholder_border", "#c7d0db")),
        "hover_bg": colors.get("control_hover_bg", colors.get("panel_hover_bg", "#e8eef5")),
        "hover_fg": colors.get("control_hover_fg", colors.get("text_primary", "#0f172a")),
        "hover_border": colors.get("control_hover_border", colors.get("nav_active_bg", "#93c5fd")),
    }


def _snapshot_button_style(button: tk.Widget) -> dict[str, object]:
    keys = (
        "bg",
        "fg",
        "activebackground",
        "activeforeground",
        "relief",
        "bd",
        "highlightthickness",
        "highlightbackground",
        "highlightcolor",
    )
    snap: dict[str, object] = {}
    for key in keys:
        try:
            snap[key] = button.cget(key)
        except Exception:
            continue
    return snap


def _restore_button_style(button: tk.Widget, snapshot: dict[str, object]) -> None:
    if not snapshot:
        return
    try:
        button.configure(**snapshot)
    except Exception:
        pass


def apply_control_button_style(button: tk.Widget, colors: dict[str, str], *, hovered: bool = False) -> None:
    t = _control_tokens(colors)
    if hovered:
        button.configure(
            bg=t["hover_bg"],
            fg=t["hover_fg"],
            activebackground=t["hover_bg"],
            activeforeground=t["hover_fg"],
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightbackground=t["hover_border"],
            highlightcolor=t["hover_border"],
        )
    else:
        button.configure(
            bg=t["bg"],
            fg=t["fg"],
            activebackground=t["hover_bg"],
            activeforeground=t["hover_fg"],
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightbackground=t["border"],
            highlightcolor=t["hover_border"],
        )


def bind_control_button_hover(button: tk.Widget, colors: dict[str, str]) -> None:
    apply_control_button_style(button, colors, hovered=False)
    button.bind("<Enter>", lambda _e: apply_control_button_style(button, colors, hovered=True), add="+")
    button.bind("<Leave>", lambda _e: apply_control_button_style(button, colors, hovered=False), add="+")


def bind_blue_hover(
    button: tk.Widget,
    colors: dict[str, str] | Callable[[], dict[str, str]],
) -> None:
    def _colors() -> dict[str, str]:
        if isinstance(colors, dict):
            return colors
        if callable(colors):
            try:
                resolved = colors()
                if isinstance(resolved, dict):
                    return resolved
            except Exception:
                pass
        return {}

    def _on_enter(_evt=None) -> None:
        t = _control_tokens(_colors())
        setattr(button, "_nm_prev_style", _snapshot_button_style(button))
        try:
            button.configure(
                bg=t["hover_bg"],
                fg=t["hover_fg"],
                activebackground=t["hover_bg"],
                activeforeground=t["hover_fg"],
                relief="flat",
                highlightthickness=1,
                highlightbackground=t["hover_border"],
                highlightcolor=t["hover_border"],
            )
        except Exception:
            pass

    def _on_leave(_evt=None) -> None:
        snap = getattr(button, "_nm_prev_style", None)
        if isinstance(snap, dict):
            _restore_button_style(button, snap)

    button.bind("<Enter>", _on_enter, add="+")
    button.bind("<Leave>", _on_leave, add="+")
