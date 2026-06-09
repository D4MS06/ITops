import json

from monitoring.shared.theme_manager import list_editor_color_keys, resolve_theme


def test_dark_theme_uses_digital_blue_interaction_tokens():
    theme = resolve_theme("dark")

    assert theme.colors["interaction_hover_bg"] == "#0e7490"
    assert theme.colors["interaction_hover_bg"] == theme.colors["control_hover_bg"]
    assert theme.colors["interaction_hover_bg"] == theme.colors["nav_active_bg"]
    assert theme.colors["interaction_selected_bg"] == theme.colors["tree_select_bg"]


def test_theme_overrides_are_scoped_by_theme():
    overrides = json.dumps(
        {
            "light": {"interaction_hover_bg": "#c7f9ff"},
            "dark": {"interaction_hover_bg": "#22d3ee"},
        }
    )

    light = resolve_theme("light", overrides)
    dark = resolve_theme("dark", overrides)

    assert light.colors["interaction_hover_bg"] == "#c7f9ff"
    assert dark.colors["interaction_hover_bg"] == "#22d3ee"
    assert dark.colors["control_hover_bg"] == "#22d3ee"


def test_editor_keys_expose_colors_only():
    keys = set(list_editor_color_keys())

    assert "interaction_hover_bg" in keys
    assert "interaction_selected_bg" in keys
    assert "box_shadow" not in keys
    assert "button_radius" not in keys
