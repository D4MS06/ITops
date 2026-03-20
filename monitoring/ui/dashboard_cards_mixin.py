from __future__ import annotations

import json
from tkinter import LEFT, Button, Frame, Label, Menu, X

from monitoring.ui.theme_utils import bind_blue_hover


class DashboardCardsMixin:
    def _create_kpi_cards(self) -> None:
        self.cards_grid = Frame(self.root, bg=self.theme.colors["app_bg"])
        self.cards_grid.pack(fill=X, padx=10, pady=(2, 8))
        self.cards_edit_mode = False
        self._drag_card_key: str | None = None
        self._card_order: list[str] = []
        self._hidden_cards: set[str] = set()

        self.card_values: dict[str, Label] = {}
        self.card_subs: dict[str, Label] = {}
        self.card_defs: dict[str, dict] = {}
        self.card_click_actions = {
            "all_total": self._show_global_filtered,
            "web_server_state": self._open_web_server_dialog,
        }
        rows = []
        for dtype in self._ordered_type_codes():
            label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
            self.card_click_actions[f"{dtype}_status"] = lambda dt=dtype: self._show_type_filtered(dt, None)
            rows.extend(
                [
                    (f"{dtype}_status", f"Etat {label}", self.theme.colors.get("kpi_total_accent", self.theme.colors["text_secondary"])),
                ]
            )
        rows.extend(
            [
                ("all_total", "Equipements", "#1d4ed8"),
                ("monitoring_state", "Monitoring", "#7c3aed"),
                ("web_server_state", "Serveur web", "#0891b2"),
            ]
        )
        default_order = [key for key, _title, _accent in rows]
        self._card_order, self._hidden_cards = self._load_saved_cards_layout(default_order)

        for col in range(4):
            self.cards_grid.grid_columnconfigure(col, weight=1, uniform="kpi")

        row_by_key = {key: (title, color) for key, title, color in rows}
        for key in default_order:
            title, color = row_by_key[key]
            self._create_card(self.cards_grid, key, title, color, row=0, col=0)
        self._layout_cards()
        self._apply_cards_edit_ui_state()

    def _load_saved_cards_layout(self, default_order: list[str]) -> tuple[list[str], set[str]]:
        raw = str(getattr(self.notification_settings, "dashboard_cards_order_json", "") or "").strip()
        hidden_raw = str(getattr(self.notification_settings, "dashboard_hidden_cards_json", "") or "").strip()
        ordered: list[str] = []
        hidden: set[str] = set()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    ordered = [str(v) for v in parsed if isinstance(v, str) and str(v) in default_order]
            except Exception:
                ordered = []
        if hidden_raw:
            try:
                hidden_parsed = json.loads(hidden_raw)
                if isinstance(hidden_parsed, list):
                    hidden = {str(v) for v in hidden_parsed if isinstance(v, str) and str(v) in default_order}
            except Exception:
                hidden = set()
        if not ordered:
            ordered = list(default_order)
        ordered = [k for k in ordered if k not in hidden]
        known = set(ordered) | hidden
        for key in default_order:
            if key not in known:
                ordered.append(key)
        return ordered, hidden

    def _save_cards_layout(self) -> None:
        try:
            self.notification_settings.dashboard_cards_order_json = json.dumps(self._card_order, ensure_ascii=False)
            self.notification_settings.dashboard_hidden_cards_json = json.dumps(sorted(self._hidden_cards), ensure_ascii=False)
            self._save_settings()
        except Exception:
            self.logger.exception("Erreur sauvegarde disposition des tuiles")

    def _toggle_cards_edit_mode(self) -> None:
        self.cards_edit_mode = not bool(getattr(self, "cards_edit_mode", False))
        if not self.cards_edit_mode:
            self._save_cards_layout()
        self._apply_cards_edit_ui_state()

    def _apply_cards_edit_ui_state(self) -> None:
        active = bool(getattr(self, "cards_edit_mode", False))
        border_color = "#25A244" if active else self.theme.colors["placeholder_border"]
        try:
            self.btn_cards_edit.configure(highlightthickness=2, highlightbackground=border_color)
        except Exception as exc:
            self.logger.debug("Cards edit button styling failed: %s", exc)
        try:
            self._set_round_action_pill_state(
                self.btn_cards_add,
                enabled=active and bool(self._hidden_cards),
                border_color=border_color if active else None,
            )
            if active and not self.btn_cards_add.winfo_manager():
                self.btn_cards_add.pack(side=LEFT, padx=(2, 3))
            if (not active) and self.btn_cards_add.winfo_manager():
                self.btn_cards_add.pack_forget()
        except Exception as exc:
            self.logger.debug("Cards add button state update failed: %s", exc)
        for key, card_def in self.card_defs.items():
            frame = card_def["frame"]
            clickable = bool(card_def.get("clickable", False))
            remove_btn = card_def.get("remove_btn")
            try:
                frame.configure(
                    cursor="fleur" if active else "",
                    highlightbackground=border_color if active else self.theme.colors["placeholder_border"],
                    highlightthickness=2 if active else 1,
                )
            except Exception:
                continue
            if remove_btn is not None:
                if active and key in self._card_order:
                    try:
                        self._set_round_action_pill_state(
                            remove_btn,
                            enabled=(len(self._card_order) > 1),
                        )
                        remove_btn.place(relx=1.0, x=-5, y=5, anchor="ne")
                    except Exception as exc:
                        self.logger.debug("Card remove button placement failed for %s: %s", key, exc)
                else:
                    try:
                        remove_btn.place_forget()
                    except Exception as exc:
                        self.logger.debug("Card remove button hide failed for %s: %s", key, exc)
            widgets = (frame, *card_def["labels"])
            for widget in widgets:
                widget.unbind("<Enter>")
                widget.unbind("<Leave>")
                widget.unbind("<ButtonPress-1>")
                widget.unbind("<B1-Motion>")
                widget.unbind("<ButtonRelease-1>")
                if active:
                    widget.bind("<ButtonPress-1>", lambda evt, k=key: self._on_card_drag_start(evt, k))
                    widget.bind("<B1-Motion>", self._on_card_drag_motion)
                    widget.bind("<ButtonRelease-1>", self._on_card_drag_end)
                elif clickable:
                    widget.bind("<Enter>", lambda _evt, k=key: self._set_card_hover(k, True))
                    widget.bind("<Leave>", lambda _evt, k=key: self._set_card_hover(k, False))
                    widget.bind("<ButtonPress-1>", lambda _evt, k=key: self._on_card_click(k))
            status_widgets = card_def.get("status_widgets") or {}
            status_bind_items = tuple(status_widgets.items()) if isinstance(status_widgets, dict) else ()
            for wname, st_lbl in status_bind_items:
                st_lbl.unbind("<Enter>")
                st_lbl.unbind("<Leave>")
                st_lbl.unbind("<ButtonPress-1>")
                st_lbl.unbind("<B1-Motion>")
                st_lbl.unbind("<ButtonRelease-1>")
                if active:
                    st_lbl.bind("<ButtonPress-1>", lambda evt, k=key: self._on_card_drag_start(evt, k))
                    st_lbl.bind("<B1-Motion>", self._on_card_drag_motion)
                    st_lbl.bind("<ButtonRelease-1>", self._on_card_drag_end)
                elif clickable:
                    st_lbl.bind("<Enter>", lambda _evt, k=key: self._set_card_hover(k, True))
                    st_lbl.bind("<Leave>", lambda _evt, k=key: self._set_card_hover(k, False))
                    if wname == "val_up":
                        st_lbl.bind("<ButtonPress-1>", lambda _evt, k=key: self._on_status_metric_click(k, "online"))
                    elif wname == "val_down":
                        st_lbl.bind("<ButtonPress-1>", lambda _evt, k=key: self._on_status_metric_click(k, "offline"))
                    else:
                        st_lbl.bind("<ButtonPress-1>", lambda _evt, k=key: self._on_card_click(k))

    def _layout_cards(self) -> None:
        for card_def in self.card_defs.values():
            try:
                card_def["frame"].grid_remove()
            except Exception as exc:
                self.logger.debug("Card grid_remove failed: %s", exc)
        for idx, key in enumerate(self._card_order):
            card_def = self.card_defs.get(key)
            if not card_def:
                continue
            row = idx // 4
            col = idx % 4
            card_def["frame"].grid_configure(row=row, column=col)

    def _on_card_drag_start(self, _evt, key: str) -> None:
        if not self.cards_edit_mode:
            return
        self._drag_card_key = str(key)

    def _on_card_drag_motion(self, _evt) -> None:
        return

    def _on_card_drag_end(self, evt) -> None:
        if not self.cards_edit_mode:
            return
        dragged = str(self._drag_card_key or "")
        self._drag_card_key = None
        if not dragged or dragged not in self._card_order:
            return
        target_key = self._card_key_under_pointer(int(evt.x_root), int(evt.y_root))
        if not target_key or target_key == dragged or target_key not in self._card_order:
            return
        old_idx = self._card_order.index(dragged)
        new_idx = self._card_order.index(target_key)
        if old_idx == new_idx:
            return
        self._card_order.pop(old_idx)
        self._card_order.insert(new_idx, dragged)
        self._layout_cards()

    def _remove_card(self, key: str) -> None:
        key = str(key)
        if key not in self._card_order:
            return
        if len(self._card_order) <= 1:
            return
        self._card_order = [k for k in self._card_order if k != key]
        self._hidden_cards.add(key)
        self._layout_cards()
        self._apply_cards_edit_ui_state()

    def _add_card(self, key: str) -> None:
        key = str(key)
        if key not in self.card_defs or key in self._card_order:
            return
        self._hidden_cards.discard(key)
        self._card_order.append(key)
        self._layout_cards()
        self._apply_cards_edit_ui_state()

    def _on_add_card_click(self) -> None:
        if not bool(getattr(self, "cards_edit_mode", False)):
            return
        hidden = [k for k in self.card_defs.keys() if k in self._hidden_cards]
        if not hidden:
            return
        menu = Menu(self.root, tearoff=0)
        for key in hidden:
            title = str(self.card_defs.get(key, {}).get("title", key))
            menu.add_command(label=f"+ {title}", command=lambda k=key: self._add_card(k))
        try:
            x = self.btn_cards_add.winfo_rootx()
            y = self.btn_cards_add.winfo_rooty() + self.btn_cards_add.winfo_height()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception as exc:
                self.logger.debug("Card add popup menu grab_release failed: %s", exc)

    def _card_key_under_pointer(self, x_root: int, y_root: int) -> str | None:
        target = self.root.winfo_containing(x_root, y_root)
        while target is not None:
            for key, card_def in self.card_defs.items():
                if target == card_def["frame"]:
                    return key
            target = target.master
        return None

    def _show_summary_panels(self) -> None:
        self.cards_grid.pack(fill=X, padx=10, pady=(2, 8), before=self.detail_container)
        self.mon_wrap.pack(fill=X, padx=10, pady=(0, 8), before=self.detail_container)

    def _hide_summary_panels(self) -> None:
        self.cards_grid.pack_forget()
        self.mon_wrap.pack_forget()

    def _create_card(
        self,
        parent: Frame,
        key: str,
        title: str,
        accent: str,
        *,
        row: int,
        col: int,
    ) -> None:
        clickable = key != "monitoring_state"
        base_bg = self.theme.colors["panel_bg"]
        hover_bg = self.theme.colors["panel_hover_bg"]
        has_status_row = key.endswith("_status") or key == "all_total"
        card_height = 92 if has_status_row else 72
        if key == "web_server_state":
            card_height = 102

        card = Frame(
            parent,
            bg=base_bg,
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.theme.colors["placeholder_border"],
            padx=8,
            pady=3,
            height=card_height,
        )
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=3)
        # Les widgets internes utilisent pack; il faut donc figer via pack_propagate
        # pour eviter les variations de hauteur et les sauts de layout.
        card.pack_propagate(False)

        title_lbl = Label(
            card,
            text=title,
            bg=base_bg,
            fg=self.theme.colors["text_secondary"],
            font=("Segoe UI", 9, "bold"),
            cursor="hand2" if clickable else "arrow",
        )
        title_lbl.pack(anchor="w")

        val = Label(
            card,
            text="-",
            bg=base_bg,
            fg=accent,
            font=("Segoe UI", 14, "bold"),
            cursor="hand2" if clickable else "arrow",
        )
        val.pack(anchor="w", pady=(1, 0))

        sub = Label(
            card,
            text="",
            bg=base_bg,
            fg=self.theme.colors["text_muted"],
            font=("Segoe UI", 8),
            cursor="hand2" if clickable else "arrow",
        )
        sub.pack(anchor="w")
        status_widgets: dict | None = None
        action_button = None
        action_play_button = None
        action_stop_button = None
        action_row = None
        if key.endswith("_status") or key == "all_total":
            status_row = Frame(card, bg=base_bg)
            status_row.pack(anchor="w", pady=(1, 0))
            lbl_up = Label(
                status_row,
                text="En ligne:",
                bg=base_bg,
                fg=self.theme.colors["text_muted"],
                font=("Segoe UI", 8),
                cursor="hand2" if clickable else "arrow",
            )
            lbl_up.pack(side=LEFT, padx=(0, 3))
            status_up = Label(
                status_row,
                text="-",
                bg=base_bg,
                fg="#16a34a",
                font=("Segoe UI", 8, "bold"),
                cursor="hand2" if clickable else "arrow",
            )
            status_up.pack(side=LEFT, padx=(0, 8))
            lbl_down = Label(
                status_row,
                text="Hors ligne:",
                bg=base_bg,
                fg=self.theme.colors["text_muted"],
                font=("Segoe UI", 8),
                cursor="hand2" if clickable else "arrow",
            )
            lbl_down.pack(side=LEFT, padx=(0, 3))
            status_down = Label(
                status_row,
                text="-",
                bg=base_bg,
                fg="#dc2626",
                font=("Segoe UI", 8, "bold"),
                cursor="hand2" if clickable else "arrow",
            )
            status_down.pack(side=LEFT)
            status_widgets = {
                "row": status_row,
                "lbl_up": lbl_up,
                "val_up": status_up,
                "lbl_down": lbl_down,
                "val_down": status_down,
            }
        elif key == "web_server_state":
            action_row = Frame(card, bg=base_bg)
            action_row.pack(fill=X, pady=(2, 0))
            val.pack_forget()
            val.pack(in_=action_row, side=LEFT, anchor="w")
            val.configure(
                fg=self.theme.colors["text_primary"],
                font=("Segoe UI", 10, "bold"),
            )
            action_play_button = Button(
                action_row,
                text="\u25B6",
                width=2,
                command=self._play_web_server_from_dashboard,
                bd=1,
                relief="raised",
                bg=self.theme.colors["button_active_bg"],
                fg=self.theme.colors["button_active_fg"],
                font=("Segoe UI Symbol", 9, "bold"),
                activebackground=self.theme.colors.get("control_hover_bg", self.theme.colors["panel_hover_bg"]),
                activeforeground=self.theme.colors.get("control_hover_fg", self.theme.colors["text_primary"]),
                highlightthickness=1,
                highlightbackground=self.theme.colors["placeholder_border"],
            )
            action_play_button.pack(side=LEFT, padx=(10, 3))
            bind_blue_hover(action_play_button, lambda: self.theme.colors)
            action_stop_button = Button(
                action_row,
                text="\u25A0",
                width=2,
                command=self._stop_web_server_from_dashboard,
                bd=1,
                relief="raised",
                bg="#dc2626",
                fg="#ffffff",
                font=("Segoe UI Symbol", 9, "bold"),
                activebackground="#b91c1c",
                activeforeground="#ffffff",
                highlightthickness=1,
                highlightbackground=self.theme.colors["placeholder_border"],
            )
            action_stop_button.pack(side=LEFT, padx=(0, 0))
            action_button = action_play_button

        btn_remove = self._create_round_action_pill(
            card,
            symbol="\u2212",
            size=20,
            command=lambda k=key: self._remove_card(k),
            fill="#E2E8F0",
            hover_fill="#CBD5E1",
            text_color="#334155",
            disabled_fill="#F1F5F9",
            disabled_text="#94A3B8",
            container_bg=base_bg,
        )
        btn_remove.place_forget()

        self.card_values[key] = val
        self.card_subs[key] = sub
        self.card_defs[key] = {
            "frame": card,
            "labels": (title_lbl, val, sub),
            "status_widgets": status_widgets,
            "action_button": action_button,
            "action_play_button": action_play_button,
            "action_stop_button": action_stop_button,
            "action_row": action_row,
            "base_bg": base_bg,
            "hover_bg": hover_bg,
            "clickable": clickable,
            "title": title,
            "remove_btn": btn_remove,
        }
        self._bind_card_interactions(key)

    def _bind_card_interactions(self, key: str) -> None:
        card_def = self.card_defs[key]
        if not card_def["clickable"]:
            return
        widgets = (card_def["frame"], *card_def["labels"])
        for widget in widgets:
            widget.bind("<Enter>", lambda _evt, k=key: self._set_card_hover(k, True))
            widget.bind("<Leave>", lambda _evt, k=key: self._set_card_hover(k, False))
            widget.bind("<Button-1>", lambda _evt, k=key: self._on_card_click(k))
        status_widgets = card_def.get("status_widgets") or {}
        if isinstance(status_widgets, dict):
            for wname, st_lbl in status_widgets.items():
                st_lbl.bind("<Enter>", lambda _evt, k=key: self._set_card_hover(k, True))
                st_lbl.bind("<Leave>", lambda _evt, k=key: self._set_card_hover(k, False))
                if wname == "val_up":
                    st_lbl.bind("<Button-1>", lambda _evt, k=key: self._on_status_metric_click(k, "online"))
                elif wname == "val_down":
                    st_lbl.bind("<Button-1>", lambda _evt, k=key: self._on_status_metric_click(k, "offline"))
                else:
                    st_lbl.bind("<Button-1>", lambda _evt, k=key: self._on_card_click(k))

    def _set_card_hover(self, key: str, hovered: bool) -> None:
        card_def = self.card_defs.get(key)
        if not card_def:
            return
        if not hovered and self._is_pointer_inside_card(key):
            return
        bg = card_def["hover_bg"] if hovered else card_def["base_bg"]
        border = self.theme.colors["nav_active_bg"] if hovered else self.theme.colors["placeholder_border"]
        card_def["frame"].config(bg=bg, relief="flat", bd=0, highlightbackground=border)
        for lbl in card_def["labels"]:
            lbl.config(bg=bg)
        status_widgets = card_def.get("status_widgets") or {}
        if isinstance(status_widgets, dict):
            for st_lbl in status_widgets.values():
                st_lbl.config(bg=bg)
        action_button = card_def.get("action_button")
        action_row = card_def.get("action_row")
        if action_row is not None:
            try:
                action_row.configure(bg=bg)
            except Exception as exc:
                self.logger.debug("Card action row hover update failed for %s: %s", key, exc)
        remove_btn = card_def.get("remove_btn")
        if remove_btn is not None:
            self._set_round_action_pill_container_bg(remove_btn, bg)

    def _is_pointer_inside_card(self, key: str) -> bool:
        card_def = self.card_defs.get(key)
        if not card_def:
            return False
        frame = card_def.get("frame")
        if frame is None:
            return False
        try:
            x_root, y_root = self.root.winfo_pointerxy()
            target = self.root.winfo_containing(x_root, y_root)
            while target is not None:
                if target == frame:
                    return True
                target = getattr(target, "master", None)
        except Exception:
            return False
        return False

    def _on_card_click(self, key: str) -> None:
        if bool(getattr(self, "cards_edit_mode", False)):
            return
        action = self.card_click_actions.get(key)
        if action:
            action()

    def _on_status_metric_click(self, key: str, status: str) -> None:
        if bool(getattr(self, "cards_edit_mode", False)):
            return
        if key == "all_total":
            self._show_global_filtered(status)
            return
        if key.endswith("_status"):
            dtype = key[: -len("_status")]
            if dtype in self.type_views:
                self._show_type_filtered(dtype, status)


