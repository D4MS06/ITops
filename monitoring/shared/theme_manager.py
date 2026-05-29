from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ThemeDefinition:
    key: str
    label: str
    colors: Dict[str, str]
    editable: bool = False


THEME_PRESETS: dict[str, ThemeDefinition] = {
    "light": ThemeDefinition(
        key="light",
        label="Light",
        editable=False,
        colors={
            "app_bg": "#e9edf2",
            "surface_bg": "#d9e0e8",
            "panel_bg": "#f2f5f8",
            "panel_hover_bg": "#e8eef5",
            "text_primary": "#0f172a",
            "text_secondary": "#475569",
            "text_muted": "#64748b",
            "kpi_total_accent": "#1e3a8a",
            "button_inactive_bg": "#e2e8f0",
            "button_inactive_fg": "#0f172a",
            "button_active_bg": "#16a34a",
            "button_active_fg": "#ffffff",
            "button_global_bg": "#7c3aed",
            "nav_active_bg": "#93c5fd",
            "nav_inactive_bg": "#cfd8e3",
            "placeholder_bg": "#e9edf2",
            "placeholder_border": "#c7d0db",
            "tree_bg": "#ffffff",
            "tree_fg": "#0f172a",
            "tree_heading_bg": "#d9e0e8",
            "tree_heading_fg": "#0f172a",
            "tree_select_bg": "#bfdbfe",
            "menu_bg": "#f2f5f8",
            "menu_fg": "#0f172a",
            "menu_border": "#bcc8d8",
            "control_bg": "#e2e8f0",
            "control_fg": "#0f172a",
            "control_border": "#c7d0db",
            "control_hover_bg": "#93c5fd",
            "control_hover_fg": "#0f172a",
            "control_hover_border": "#93c5fd",
        },
    ),
    "dark": ThemeDefinition(
        key="dark",
        label="Dark",
        editable=False,
        colors={
            "app_bg": "#111827",
            "surface_bg": "#1f2937",
            "panel_bg": "#263244",
            "panel_hover_bg": "#324052",
            "text_primary": "#e5e7eb",
            "text_secondary": "#cbd5e1",
            "text_muted": "#94a3b8",
            "kpi_total_accent": "#cbd5e1",
            "button_inactive_bg": "#374151",
            "button_inactive_fg": "#e5e7eb",
            "button_active_bg": "#16a34a",
            "button_active_fg": "#ffffff",
            "button_global_bg": "#7c3aed",
            "nav_active_bg": "#2563eb",
            "nav_inactive_bg": "#374151",
            "placeholder_bg": "#111827",
            "placeholder_border": "#263241",
            "tree_bg": "#0f172a",
            "tree_fg": "#e2e8f0",
            "tree_heading_bg": "#263244",
            "tree_heading_fg": "#e5e7eb",
            "tree_select_bg": "#1d4ed8",
            "menu_bg": "#1f2937",
            "menu_fg": "#e5e7eb",
            "menu_border": "#4a6078",
            "control_bg": "#374151",
            "control_fg": "#e5e7eb",
            "control_border": "#263241",
            "control_hover_bg": "#2563eb",
            "control_hover_fg": "#ffffff",
            "control_hover_border": "#2563eb",
        },
    ),
}


def list_themes() -> list[ThemeDefinition]:
    return list(THEME_PRESETS.values())


def resolve_theme(theme_key: str) -> ThemeDefinition:
    key = (theme_key or "light").strip().lower()
    base = THEME_PRESETS["light"]
    selected = THEME_PRESETS.get(key, base)
    merged_colors: Dict[str, str] = dict(base.colors)
    merged_colors.update(dict(selected.colors or {}))
    return ThemeDefinition(
        key=selected.key,
        label=selected.label,
        colors=merged_colors,
        editable=selected.editable,
    )
