from __future__ import annotations

from tkinter import Button, Frame, Menu


class DashboardMenuMixin:
    def _close_custom_menu(self) -> None:
        if self._menu_outside_click_bind is not None:
            try:
                self.root.unbind("<Button-1>", self._menu_outside_click_bind)
            except Exception:
                pass
            self._menu_outside_click_bind = None
        for popup in list(getattr(self, "_menu_popups", [])):
            try:
                popup.place_forget()
                popup.destroy()
            except Exception:
                pass
        self._menu_popups = []
        self._submenu_anchor_by_level = {}

    def _close_submenus_from(self, index: int) -> None:
        popups = getattr(self, "_menu_popups", [])
        for popup in popups[index:]:
            try:
                popup.place_forget()
                popup.destroy()
            except Exception:
                pass
        self._menu_popups = popups[:index]
        for lvl in list(getattr(self, "_submenu_anchor_by_level", {}).keys()):
            if lvl >= index:
                self._submenu_anchor_by_level.pop(lvl, None)

    def _build_dropdown_frame(
        self,
        x: int,
        y: int,
        items: list[tuple[str, object]],
        *,
        level: int,
        animate: bool = False,
        animate_from: tuple[int, int, int] | None = None,
    ) -> Frame:
        c = self.theme.colors
        popup = Frame(
            self.root,
            bg=c["menu_bg"],
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=c.get("menu_border", c["placeholder_border"]),
        )
        popup.lift()
        if animate:
            self._animate_menu_open(
                popup,
                x,
                y,
                level=level,
                animate_from=animate_from,
            )
        else:
            popup.place(x=x, y=y)

        for label, action in items:
            if isinstance(action, list):
                btn = Button(
                    popup,
                    text=label,
                    anchor="w",
                    justify="left",
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                    activeforeground=c.get("control_hover_fg", c["text_primary"]),
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    padx=10,
                    pady=4,
                )
                btn.pack(fill="x")
                btn.bind("<Enter>", lambda _e=None, b=btn: self._menu_item_hover(b, True))
                btn.bind("<Leave>", lambda _e=None, b=btn: self._menu_item_hover(b, False))

                def _open_submenu(_evt=None, *, b=btn, submenu_items=action, lvl=level):
                    anchor_key = f"{lvl+1}:{b.winfo_id()}"
                    if self._submenu_anchor_by_level.get(lvl + 1) == anchor_key:
                        return
                    self._close_submenus_from(lvl + 1)
                    bx = b.winfo_rootx() - self.root.winfo_rootx() + b.winfo_width()
                    by = b.winfo_rooty() - self.root.winfo_rooty()
                    source_x = b.winfo_rootx() - self.root.winfo_rootx()
                    source_y = b.winfo_rooty() - self.root.winfo_rooty()
                    source_w = b.winfo_width()
                    sub = self._build_dropdown_frame(
                        bx,
                        by,
                        submenu_items,
                        level=lvl + 1,
                        animate=True,
                        animate_from=(source_x, source_y, source_w),
                    )
                    self._menu_popups.append(sub)
                    self._submenu_anchor_by_level[lvl + 1] = anchor_key

                btn.configure(command=_open_submenu)
                btn.bind("<Motion>", _open_submenu, add="+")
            else:
                btn = Button(
                    popup,
                    text=label,
                    anchor="w",
                    justify="left",
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    activebackground=c.get("control_hover_bg", c["panel_hover_bg"]),
                    activeforeground=c.get("control_hover_fg", c["text_primary"]),
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    padx=10,
                    pady=4,
                    command=lambda a=action: self._on_custom_menu_action(a),
                )
                btn.pack(fill="x")
                btn.bind(
                    "<Enter>",
                    lambda _e=None, b=btn, lvl=level: (
                        self._close_submenus_from(lvl + 1),
                        self._menu_item_hover(b, True),
                    ),
                )
                btn.bind("<Leave>", lambda _e=None, b=btn: self._menu_item_hover(b, False))
        return popup

    def _menu_item_hover(self, button: Button, hovered: bool) -> None:
        c = self.theme.colors
        hover_bg = c.get("control_hover_bg", c["panel_hover_bg"])
        hover_fg = c.get("control_hover_fg", c["text_primary"])
        hover_border = c.get("control_hover_border", c["nav_active_bg"])
        try:
            if hovered:
                button.configure(
                    bg=hover_bg,
                    fg=hover_fg,
                    relief="flat",
                    bd=0,
                    highlightthickness=1,
                    highlightbackground=hover_border,
                )
            else:
                button.configure(
                    bg=c["menu_bg"],
                    fg=c["menu_fg"],
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                )
        except Exception:
            pass

    def _popup_custom_menu(self, anchor_button: Button, items: list[tuple[str, object]]) -> None:
        self._close_custom_menu()
        x = anchor_button.winfo_x()
        y = self.menu_bar_frame.winfo_y() + self.menu_bar_frame.winfo_height()
        popup = self._build_dropdown_frame(x, y, items, level=0, animate=True)
        self._menu_popups = [popup]
        self._menu_outside_click_bind = self.root.bind("<Button-1>", self._on_root_click_close_menu, add="+")

    def _animate_menu_open(
        self,
        popup: Frame,
        target_x: int,
        target_y: int,
        *,
        level: int,
        animate_from: tuple[int, int, int] | None = None,
    ) -> None:
        if level == 0:
            start_x = target_x - 8
            start_y = target_y - 4
        elif animate_from is not None:
            src_x, src_y, src_w = animate_from
            start_x = src_x + max(6, int(src_w * 0.35))
            start_y = src_y + 1
        else:
            start_x = target_x - 10
            start_y = target_y
        steps = 10 if level > 0 else 6
        popup.place(x=start_x, y=start_y)

        def _step(i: int) -> None:
            if not popup.winfo_exists():
                return
            if i >= steps:
                popup.place_configure(x=target_x, y=target_y)
                return
            t = (i + 1) / steps
            t = 1 - (1 - t) * (1 - t)
            x = int(start_x + (target_x - start_x) * t)
            y = int(start_y + (target_y - start_y) * t)
            popup.place_configure(x=x, y=y)
            popup.after(16 if level > 0 else 14, lambda: _step(i + 1))

        _step(0)

    def _on_root_click_close_menu(self, event) -> None:
        popups = getattr(self, "_menu_popups", [])
        if not popups:
            return
        widget = event.widget
        while widget is not None:
            if widget in popups:
                return
            widget = getattr(widget, "master", None)
        for btn in getattr(self, "menu_buttons", []):
            if event.widget is btn:
                return
        self._close_custom_menu()

    def _on_custom_menu_action(self, action) -> None:
        self._close_custom_menu()
        try:
            action()
        except Exception:
            pass

    @staticmethod
    def _popup_menu(menu: Menu, anchor_button: Button) -> None:
        try:
            x = anchor_button.winfo_rootx()
            y = anchor_button.winfo_rooty() + anchor_button.winfo_height()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

