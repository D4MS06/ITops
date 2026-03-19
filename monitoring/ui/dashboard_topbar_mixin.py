from __future__ import annotations

from tkinter import LEFT, TOP, Button, Canvas, Frame, Label

from monitoring.ui.theme_utils import bind_blue_hover


class DashboardTopbarMixin:
    def _create_topbar(self) -> None:
        bar = Frame(self.root, bg=self.theme.colors["surface_bg"], height=86)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        bar.pack_propagate(False)
        self.topbar = bar

        Label(
            bar,
            text="Tableau de bord Monitoring Reseau",
            font=("Segoe UI", 16, "bold"),
            fg=self.theme.colors["text_primary"],
            bg=self.theme.colors["surface_bg"],
        ).pack(side=LEFT, padx=16)

        right_block = Frame(bar, bg=self.theme.colors["surface_bg"])
        right_block.pack(side="right", padx=14)
        self.topbar_right = right_block

        nav = Frame(right_block, bg=self.theme.colors["surface_bg"])
        nav.pack(side=TOP, anchor="e", pady=(4, 2))
        self.navbar = nav

        self.btn_dashboard = Button(nav, text="Tableau de bord", command=self._show_dashboard, width=14)
        self.btn_dashboard.pack(side=LEFT, padx=3)
        self.type_nav_buttons: dict[str, Button] = {}
        for dtype in self._ordered_type_codes():
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            btn = Button(nav, text=label, command=lambda dt=dtype: self._show_type_detail(dt), width=10)
            btn.pack(side=LEFT, padx=3)
            self.type_nav_buttons[dtype] = btn
        self.btn_global = Button(nav, text="Globale", command=self._show_global_detail, width=10)
        self.btn_global.pack(side=LEFT, padx=3)
        self.btn_cards_edit = Button(
            nav,
            text="\u270E",
            command=self._toggle_cards_edit_mode,
            width=3,
            relief="solid",
            bd=1,
            font=("Segoe UI Symbol", 10, "bold"),
        )
        self.btn_cards_edit.pack(side=LEFT, padx=(8, 3))
        self.btn_cards_add = self._create_round_action_pill(
            nav,
            symbol="+",
            size=34,
            command=self._on_add_card_click,
            fill="#2563EB",
            hover_fill="#1D4ED8",
            text_color="#FFFFFF",
            disabled_fill="#CBD5E1",
            disabled_text="#64748B",
            container_bg=self.theme.colors["surface_bg"],
        )
        self.btn_cards_add.pack(side=LEFT, padx=(2, 3))
        for btn in [self.btn_dashboard, *self.type_nav_buttons.values(), self.btn_global]:
            bind_blue_hover(btn, lambda: self.theme.colors)
        bind_blue_hover(self.btn_cards_edit, lambda: self.theme.colors)

    @staticmethod
    def _pill_meta(widget: Canvas) -> dict:
        return getattr(widget, "_pill_meta", {})

    def _create_round_action_pill(
        self,
        parent: Frame,
        *,
        symbol: str,
        size: int,
        command,
        fill: str,
        hover_fill: str,
        text_color: str,
        disabled_fill: str,
        disabled_text: str,
        container_bg: str,
    ) -> Canvas:
        pad = 2
        pill = Canvas(
            parent,
            width=size,
            height=size,
            bd=0,
            highlightthickness=0,
            bg=container_bg,
            cursor="hand2",
        )
        oval = pill.create_oval(pad, pad, size - pad, size - pad, fill=fill, outline=fill, width=1)
        cx = size / 2.0
        cy = size / 2.0
        half = max(5, int(size * 0.2))
        stroke = max(2, int(size * 0.12))
        icon_items: list[int] = []
        icon_items.append(
            pill.create_line(
                cx - half,
                cy,
                cx + half,
                cy,
                fill=text_color,
                width=stroke,
                capstyle="round",
            )
        )
        if symbol == "+":
            icon_items.append(
                pill.create_line(
                    cx,
                    cy - half,
                    cx,
                    cy + half,
                    fill=text_color,
                    width=stroke,
                    capstyle="round",
                )
            )
        pill._pill_meta = {
            "command": command,
            "oval": oval,
            "icon_items": icon_items,
            "fill": fill,
            "hover_fill": hover_fill,
            "text_color": text_color,
            "disabled_fill": disabled_fill,
            "disabled_text": disabled_text,
            "enabled": True,
            "hovered": False,
        }

        def _on_click(_evt=None) -> None:
            meta = self._pill_meta(pill)
            if bool(meta.get("enabled", True)):
                try:
                    cmd = meta.get("command")
                    if callable(cmd):
                        cmd()
                except Exception as exc:
                    self.logger.debug("Action pill command failed: %s", exc)

        def _on_enter(_evt=None) -> None:
            meta = self._pill_meta(pill)
            meta["hovered"] = True
            self._set_round_action_pill_state(pill, enabled=bool(meta.get("enabled", True)))

        def _on_leave(_evt=None) -> None:
            meta = self._pill_meta(pill)
            meta["hovered"] = False
            self._set_round_action_pill_state(pill, enabled=bool(meta.get("enabled", True)))

        pill.bind("<Button-1>", _on_click)
        pill.bind("<Enter>", _on_enter)
        pill.bind("<Leave>", _on_leave)
        return pill

    def _set_round_action_pill_state(
        self,
        pill: Canvas,
        *,
        enabled: bool,
        border_color: str | None = None,
    ) -> None:
        meta = self._pill_meta(pill)
        if not meta:
            return
        meta["enabled"] = bool(enabled)
        hovered = bool(meta.get("hovered", False))
        if enabled:
            fill = str(meta.get("hover_fill")) if hovered else str(meta.get("fill"))
            text_color = str(meta.get("text_color"))
            outline = str(border_color or fill)
            width = 2 if border_color else 1
            cursor = "hand2"
        else:
            fill = str(meta.get("disabled_fill"))
            text_color = str(meta.get("disabled_text"))
            outline = fill
            width = 1
            cursor = "arrow"
        try:
            pill.itemconfigure(meta.get("oval"), fill=fill, outline=outline, width=width)
            for item_id in meta.get("icon_items", []):
                pill.itemconfigure(item_id, fill=text_color)
            pill.configure(cursor=cursor)
        except Exception as exc:
            self.logger.debug("Round action pill state update failed: %s", exc)

    def _set_round_action_pill_container_bg(self, pill: Canvas, bg: str) -> None:
        try:
            pill.configure(bg=bg)
        except Exception as exc:
            self.logger.debug("Round action pill container update failed: %s", exc)
