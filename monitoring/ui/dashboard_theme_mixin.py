from __future__ import annotations

from tkinter import Label

from monitoring.config.settings import save_settings
from monitoring.ui.theme_manager import resolve_theme


class DashboardThemeMixin:
    def _set_theme_from_menu(self, theme_key: str) -> None:
        self.var_theme.set(theme_key)
        self._on_theme_changed()

    def _set_status_indicator_style_from_menu(self, style_key: str) -> None:
        self.notification_settings.status_indicator_style = str(style_key or "badge").strip().lower()
        save_settings(self.notification_settings)
        self._refresh_status_indicators()

    def _refresh_status_indicators(self) -> None:
        style_key = str(getattr(self.notification_settings, "status_indicator_style", "badge") or "badge")
        for view in [*getattr(self, "type_views", {}).values(), getattr(self, "consolidated_app", None)]:
            if view is None:
                continue
            try:
                view.refresh_status_icons(style_key)
            except Exception:
                continue

    def _on_theme_changed(self) -> None:
        requested = self.var_theme.get().strip().lower() if hasattr(self, "var_theme") else "light"
        self.theme = resolve_theme(requested)
        self.notification_settings.ui_theme = self.theme.key
        save_settings(self.notification_settings)
        self._apply_theme()
        self.root.after(50, lambda: self._apply_window_chrome_theme(self.theme.key == "dark"))

    def _apply_theme(self) -> None:
        c = self.theme.colors
        self.root.configure(bg=c["app_bg"])
        self._apply_window_chrome_theme(self.theme.key == "dark")
        for menu_obj in (
            getattr(self, "settings_menu", None),
            getattr(self, "monitoring_submenu", None),
            getattr(self, "personalization_submenu", None),
            getattr(self, "theme_submenu", None),
            getattr(self, "logs_menu", None),
            getattr(self, "help_menu", None),
        ):
            if menu_obj is None:
                continue
            try:
                menu_obj.configure(
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    activebackground=c["panel_hover_bg"],
                    activeforeground=c["text_primary"],
                )
            except Exception:
                pass
        try:
            self.menu_bar_frame.configure(bg=c["menu_bg"])
        except Exception:
            pass
        for btn in getattr(self, "menu_buttons", []):
            try:
                btn.configure(
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                    activeforeground=c.get("control_hover_fg", c["text_primary"]),
                    relief="flat",
                    bd=0,
                )
            except Exception:
                continue

        for widget in (
            getattr(self, "cards_grid", None),
            getattr(self, "mon_wrap", None),
            getattr(self, "detail_container", None),
            getattr(self, "global_detail_frame", None),
        ):
            if widget is not None:
                try:
                    widget.configure(bg=c["app_bg"])
                except Exception:
                    pass
        for frame in getattr(self, "type_detail_frames", {}).values():
            try:
                frame.configure(bg=c["app_bg"])
            except Exception:
                pass

        for widget in (
            getattr(self, "topbar", None),
            getattr(self, "topbar_right", None),
            getattr(self, "navbar", None),
            getattr(self, "mon_panel", None),
        ):
            if widget is not None:
                try:
                    widget.configure(bg=c["surface_bg"])
                except Exception:
                    pass
        try:
            self.mon_panel.configure(highlightbackground=c["placeholder_border"])
        except Exception:
            pass

        for widget in (getattr(self, "placeholder", None), getattr(self, "placeholder_image", None)):
            if widget is not None:
                try:
                    widget.configure(bg=c["placeholder_bg"])
                except Exception:
                    pass

        # Update top bar labels.
        for child in self.topbar.winfo_children() if hasattr(self, "topbar") else []:
            if isinstance(child, Label):
                try:
                    # Keep version text slightly muted.
                    fg = c["text_secondary"] if str(child.cget("text")).startswith("v") else c["text_primary"]
                    child.configure(bg=c["surface_bg"], fg=fg)
                except Exception:
                    continue

        # Update KPI card palette.
        for key, card_def in self.card_defs.items():
            card_def["base_bg"] = c["panel_bg"]
            card_def["hover_bg"] = c["panel_hover_bg"]
            frame = card_def["frame"]
            labels = card_def["labels"]
            status_widgets = card_def.get("status_widgets") or {}
            try:
                frame.configure(bg=c["panel_bg"])
                labels[0].configure(bg=c["panel_bg"], fg=c["text_secondary"])
                labels[2].configure(bg=c["panel_bg"], fg=c["text_muted"])
                if isinstance(status_widgets, dict):
                    for st_lbl in status_widgets.values():
                        st_lbl.configure(bg=c["panel_bg"])
                if key.endswith("_status"):
                    labels[1].configure(fg=c.get("kpi_total_accent", c["text_secondary"]))
                    if isinstance(status_widgets, dict):
                        if status_widgets.get("lbl_up") is not None:
                            status_widgets["lbl_up"].configure(fg=c["text_muted"])
                        if status_widgets.get("lbl_down") is not None:
                            status_widgets["lbl_down"].configure(fg=c["text_muted"])
                        if status_widgets.get("val_up") is not None:
                            status_widgets["val_up"].configure(fg="#16a34a")
                        if status_widgets.get("val_down") is not None:
                            status_widgets["val_down"].configure(fg="#dc2626")
                elif key.endswith("_total") and key != "all_total":
                    labels[1].configure(fg=c.get("kpi_total_accent", c["text_secondary"]))
            except Exception:
                pass
            self._set_card_hover(key, False)

        try:
            self.dashboard_placeholder_title.configure(bg=c["placeholder_bg"], fg=c["text_primary"])
            self.dashboard_placeholder_subtitle.configure(bg=c["placeholder_bg"], fg=c["text_muted"])
            self.placeholder.configure(bg=c["placeholder_bg"])
            self.placeholder_image.configure(bg=c["placeholder_bg"])
        except Exception:
            pass

        self._update_nav_buttons()
        self._update_monitoring_buttons()
        self._refresh_dashboard_watermark()

        for view in [*getattr(self, "type_views", {}).values(), getattr(self, "consolidated_app", None)]:
            if view is None:
                continue
            try:
                if hasattr(view, "apply_theme"):
                    view.apply_theme(self.theme.key)
                elif hasattr(view, "update_display"):
                    view.update_display()
            except Exception:
                continue
        try:
            self.btn_cards_edit.configure(
                bg=c["surface_bg"],
                fg=c["text_primary"],
                activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                activeforeground=c.get("control_hover_fg", c["text_primary"]),
            )
            self._set_round_action_pill_container_bg(self.btn_cards_add, c["surface_bg"])
        except Exception:
            pass
        self._apply_cards_edit_ui_state()

