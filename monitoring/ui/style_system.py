from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UiFontTokens:
    heading: tuple[str, int, str]
    body: tuple[str, int]
    small: tuple[str, int]
    button: tuple[str, int, str]
    card_value: tuple[str, int, str]
    card_state_value: tuple[str, int, str]
    symbol_button: tuple[str, int, str]


@dataclass(frozen=True)
class UiMetricTokens:
    tree_row_height: int
    dialog_tree_row_height: int
    card_height_default: int
    card_height_status: int
    card_height_state_with_actions: int


@dataclass(frozen=True)
class UiStyleTokens:
    fonts: UiFontTokens
    metrics: UiMetricTokens


def resolve_ui_style_tokens(_theme_key: str) -> UiStyleTokens:
    # Base tokens shared across windows. Kept centralized to ease future theme editor support.
    return UiStyleTokens(
        fonts=UiFontTokens(
            heading=("Segoe UI", 9, "bold"),
            body=("Segoe UI", 10),
            small=("Segoe UI", 8),
            button=("Segoe UI", 10, "bold"),
            card_value=("Segoe UI", 14, "bold"),
            card_state_value=("Segoe UI", 12, "bold"),
            symbol_button=("Segoe UI Symbol", 9, "bold"),
        ),
        metrics=UiMetricTokens(
            tree_row_height=24,
            dialog_tree_row_height=24,
            card_height_default=72,
            card_height_status=92,
            card_height_state_with_actions=102,
        ),
    )
