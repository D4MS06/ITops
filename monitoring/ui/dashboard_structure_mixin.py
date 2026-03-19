from __future__ import annotations

from typing import TYPE_CHECKING
from tkinter import LEFT, X, Button, Frame, StringVar

if TYPE_CHECKING:
    from monitoring.ui.dashboard_contracts import DashboardMixinContract


class DashboardStructureMixin:
    def _menu_button_options(self: "DashboardMixinContract") -> dict[str, object]:
        c = self.theme.colors
        return {
            "bg": c["menu_bg"],
            "fg": c["menu_fg"],
            "activebackground": c.get("control_hover_bg", c["panel_hover_bg"]),
            "activeforeground": c.get("control_hover_fg", c["text_primary"]),
            "relief": "flat",
            "bd": 0,
            "padx": 10,
            "pady": 3,
        }

    def _add_menu_button(
        self: "DashboardMixinContract",
        menu_frame: Frame,
        *,
        text: str,
        items_getter,
        left_pad: int,
    ) -> Button:
        btn = Button(menu_frame, text=text, **self._menu_button_options())
        btn.configure(command=lambda b=btn: self._popup_custom_menu(b, items_getter()))
        btn.pack(side=LEFT, padx=(left_pad, 0))
        return btn

    def _create_menu(self: "DashboardMixinContract") -> None:
        c = self.theme.colors
        self.root.config(menu="")
        menu_frame = Frame(self.root, bg=c["menu_bg"], height=28)
        menu_frame.pack(fill=X, padx=0, pady=0)
        menu_frame.pack_propagate(False)
        self.var_theme = StringVar(value=self.theme.key)
        btn_supervision = self._add_menu_button(menu_frame, text="Supervision", items_getter=self._supervision_menu_items, left_pad=4)
        btn_inventory = self._add_menu_button(menu_frame, text="Equipements", items_getter=self._inventory_menu_items, left_pad=2)
        btn_display = self._add_menu_button(menu_frame, text="Affichage", items_getter=self._display_menu_items, left_pad=2)
        btn_help = self._add_menu_button(menu_frame, text="Aide", items_getter=self._help_menu_items, left_pad=2)

        self.menu_bar_frame = menu_frame
        self.menu_buttons = [btn_supervision, btn_inventory, btn_display, btn_help]
        self._menu_popups: list[Frame] = []
        self._submenu_anchor_by_level: dict[int, str] = {}
        self._menu_outside_click_bind = None

    def _rebuild_dynamic_sections(self: "DashboardMixinContract") -> None:
        for view in [*getattr(self, "type_views", {}).values(), getattr(self, "consolidated_app", None)]:
            if view is None:
                continue
            try:
                self.controller.unregister_view(view)
            except Exception as exc:
                self.logger.debug("Unable to unregister stale view during rebuild: %s", exc)
                continue
        for widget in (
            getattr(self, "topbar", None),
            getattr(self, "cards_grid", None),
            getattr(self, "mon_wrap", None),
            getattr(self, "detail_container", None),
        ):
            try:
                if widget is not None:
                    widget.destroy()
            except Exception as exc:
                self.logger.debug("Unable to destroy widget during dashboard rebuild: %s", exc)
                continue
        self._create_topbar()
        self._create_kpi_cards()
        self._create_monitoring_bar()
        self._create_detail_area()
        self._show_dashboard()
        self.update_display()
        self._apply_theme()
