from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ThemeDefinition:
    key: str
    label: str
    colors: dict[str, str]
    editable: bool = False


# Keys intentionally exposed to a future graphic-chart editor.
# They describe colors only. Layout, shadows and button design stay in CSS.
EDITOR_COLOR_KEYS: tuple[str, ...] = (
    "app_bg",
    "surface_bg",
    "panel_bg",
    "panel_hover_bg",
    "text_primary",
    "text_secondary",
    "text_muted",
    "accent_primary",
    "success_bg",
    "success_fg",
    "interaction_hover_bg",
    "interaction_hover_bg_top",
    "interaction_hover_fg",
    "interaction_hover_border",
    "interaction_selected_bg",
    "interaction_selected_fg",
    "interaction_selected_border",
    "line_soft",
    "control_bg",
    "control_fg",
    "control_border",
    "tree_bg",
    "tree_fg",
    "tree_heading_bg",
    "tree_heading_fg",
    "menu_bg",
    "menu_fg",
    "menu_border",
)

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


THEME_PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "app_bg": "#e9edf2",
        "surface_bg": "#d9e0e8",
        "panel_bg": "#f2f5f8",
        "panel_hover_bg": "#e8eef5",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "text_muted": "#64748b",
        "accent_primary": "#0f7fe5",
        "success_bg": "#16a34a",
        "success_fg": "#ffffff",
        "interaction_hover_bg": "#d7ebff",
        "interaction_hover_bg_top": "#eaf5ff",
        "interaction_hover_fg": "#053f7d",
        "interaction_hover_border": "#6aa9df",
        "interaction_selected_bg": "#e2f1ff",
        "interaction_selected_fg": "#0f172a",
        "interaction_selected_border": "#6aa9df",
        "line_soft": "#c7d0db",
        "control_bg": "#e2e8f0",
        "control_fg": "#0f172a",
        "control_border": "#c7d0db",
        "tree_bg": "#ffffff",
        "tree_fg": "#0f172a",
        "tree_heading_bg": "#d9e0e8",
        "tree_heading_fg": "#0f172a",
        "menu_bg": "#f2f5f8",
        "menu_fg": "#0f172a",
        "menu_border": "#bcc8d8",
    },
    "dark": {
        "app_bg": "#111827",
        "surface_bg": "#1f2937",
        "panel_bg": "#263244",
        "panel_hover_bg": "#324052",
        "text_primary": "#e5e7eb",
        "text_secondary": "#cbd5e1",
        "text_muted": "#94a3b8",
        "accent_primary": "#0891b2",
        "success_bg": "#16a34a",
        "success_fg": "#ffffff",
        "interaction_hover_bg": "#0e7490",
        "interaction_hover_bg_top": "#0891b2",
        "interaction_hover_fg": "#ffffff",
        "interaction_hover_border": "#67e8f9",
        "interaction_selected_bg": "#0284c7",
        "interaction_selected_fg": "#ffffff",
        "interaction_selected_border": "#67e8f9",
        "line_soft": "#263241",
        "control_bg": "#374151",
        "control_fg": "#e5e7eb",
        "control_border": "#263241",
        "tree_bg": "#0f172a",
        "tree_fg": "#e2e8f0",
        "tree_heading_bg": "#263244",
        "tree_heading_fg": "#e5e7eb",
        "menu_bg": "#1f2937",
        "menu_fg": "#e5e7eb",
        "menu_border": "#4a6078",
    },
}


THEME_LABELS: dict[str, str] = {
    "light": "Light",
    "dark": "Dark",
}


def _normalize_theme_key(theme_key: str) -> str:
    key = (theme_key or "light").strip().lower()
    return key if key in THEME_PALETTES else "light"


def _sanitize_color_overrides(raw: object) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        return {}
    allowed = set(EDITOR_COLOR_KEYS)
    sanitized: dict[str, str] = {}
    for key, value in raw.items():
        name = str(key or "").strip()
        color = str(value or "").strip()
        if name in allowed and _HEX_COLOR_RE.match(color):
            sanitized[name] = color
    return sanitized


def _parse_theme_overrides(overrides_json: str) -> dict[str, dict[str, str]]:
    raw_text = str(overrides_json or "").strip()
    if not raw_text:
        return {}
    try:
        raw = json.loads(raw_text)
    except (TypeError, ValueError):
        return {}
    if not isinstance(raw, Mapping):
        return {}

    source = raw.get("themes") if isinstance(raw.get("themes"), Mapping) else raw
    parsed: dict[str, dict[str, str]] = {}
    for theme_key in THEME_PALETTES:
        parsed[theme_key] = _sanitize_color_overrides(source.get(theme_key))

    # Legacy flat payload: apply valid colors to the active theme in resolve_theme().
    parsed["_flat"] = _sanitize_color_overrides(raw)
    return parsed


def _derive_color_tokens(palette: Mapping[str, str]) -> dict[str, str]:
    accent = str(palette["accent_primary"])
    success_bg = str(palette["success_bg"])
    success_fg = str(palette["success_fg"])
    line = str(palette["line_soft"])
    hover_bg = str(palette["interaction_hover_bg"])
    hover_fg = str(palette["interaction_hover_fg"])
    hover_border = str(palette["interaction_hover_border"])
    selected_bg = str(palette["interaction_selected_bg"])
    selected_fg = str(palette["interaction_selected_fg"])
    selected_border = str(palette["interaction_selected_border"])

    colors = dict(palette)
    colors.update(
        {
            # Legacy/API aliases consumed by the current UI. These are linked on purpose
            # so the editor does not expose separate colors for every hover target.
            "kpi_total_accent": str(palette["text_secondary"]),
            "button_global_bg": accent,
            "button_active_bg": success_bg,
            "button_active_fg": success_fg,
            "button_inactive_bg": str(palette["control_bg"]),
            "button_inactive_fg": str(palette["control_fg"]),
            "nav_active_bg": hover_bg,
            "nav_inactive_bg": str(palette["control_bg"]),
            "placeholder_bg": str(palette["app_bg"]),
            "placeholder_border": line,
            "tree_select_bg": selected_bg,
            "control_hover_bg": hover_bg,
            "control_hover_fg": hover_fg,
            "control_hover_border": hover_border,
            "interaction_selected_fg": selected_fg,
            "interaction_selected_border": selected_border,
            "menu_border": str(palette["menu_border"]),
        }
    )
    return colors


def _build_theme(theme_key: str, colors: Mapping[str, str]) -> ThemeDefinition:
    key = _normalize_theme_key(theme_key)
    return ThemeDefinition(
        key=key,
        label=THEME_LABELS.get(key, key.title()),
        colors=_derive_color_tokens(colors),
        editable=False,
    )


THEME_PRESETS: dict[str, ThemeDefinition] = {
    key: _build_theme(key, palette) for key, palette in THEME_PALETTES.items()
}


def list_themes() -> list[ThemeDefinition]:
    return list(THEME_PRESETS.values())


def list_editor_color_keys() -> tuple[str, ...]:
    return EDITOR_COLOR_KEYS


def resolve_theme(theme_key: str, overrides_json: str = "") -> ThemeDefinition:
    key = _normalize_theme_key(theme_key)
    palette = dict(THEME_PALETTES["light"])
    if key != "light":
        palette.update(THEME_PALETTES[key])

    overrides = _parse_theme_overrides(overrides_json)
    palette.update(overrides.get(key, {}))
    palette.update(overrides.get("_flat", {}))
    return _build_theme(key, palette)
