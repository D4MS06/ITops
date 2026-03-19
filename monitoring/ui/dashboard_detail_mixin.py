from __future__ import annotations

from tkinter import BOTH, Frame, Label

from monitoring.ui.consolidated_view import ConsolidatedView
from monitoring.ui.type_devices_view import TypeDevicesView


class DashboardDetailMixin:
    def _create_detail_area(self) -> None:
        self.detail_container = Frame(self.root, bg=self.theme.colors["app_bg"])
        self.detail_container.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        self.placeholder = Frame(self.detail_container, bg=self.theme.colors["placeholder_bg"])
        self._dashboard_watermark = None
        self.placeholder_image = Label(self.placeholder, bg=self.theme.colors["placeholder_bg"])
        self.placeholder_image.pack(pady=(24, 8))
        self.dashboard_placeholder_title = Label(
            self.placeholder,
            text="Aucune sonde active",
            bg=self.theme.colors["placeholder_bg"],
            fg=self.theme.colors["text_primary"],
            font=("Segoe UI", 13, "bold"),
        )
        self.dashboard_placeholder_title.pack(pady=(8, 4))
        self.dashboard_placeholder_subtitle = Label(
            self.placeholder,
            text="Cliquez sur un monitoring de type ou sur Demarrer Global.",
            bg=self.theme.colors["placeholder_bg"],
            fg=self.theme.colors["text_muted"],
            font=("Segoe UI", 10),
        )
        self.dashboard_placeholder_subtitle.pack()
        self._refresh_dashboard_watermark()

        self.global_detail_frame = Frame(self.detail_container, bg=self.theme.colors["app_bg"])
        self.type_detail_frames: dict[str, Frame] = {}
        self.type_views: dict[str, TypeDevicesView] = {}
        for dtype in self._ordered_type_codes():
            frame = Frame(self.detail_container, bg=self.theme.colors["app_bg"])
            view = TypeDevicesView(
                frame,
                device_type_code=dtype,
                type_label=str(self.model.type_definitions.get(dtype, {}).get("label", dtype)),
                model=self.model,
                controller=self.controller,
                settings_service=self.settings_service,
                device_actions_service=self.device_actions_service,
            )
            view.pack(fill=BOTH, expand=True)
            self.type_detail_frames[dtype] = frame
            self.type_views[dtype] = view

        self.consolidated_app = ConsolidatedView(
            self.global_detail_frame,
            model=self.model,
            controller=self.controller,
            settings_service=self.settings_service,
            device_actions_service=self.device_actions_service,
        )
        self.consolidated_app.pack(fill=BOTH, expand=True)

    def _hide_details(self) -> None:
        self.placeholder.pack_forget()
        for frame in self.type_detail_frames.values():
            frame.pack_forget()
        self.global_detail_frame.pack_forget()

    def _show_dashboard(self) -> None:
        running_types = [dtype for dtype in self._monitored_type_codes() if bool(self.model.do_run.get(dtype, False))]
        if len(running_types) > 1:
            self._show_global_embedded()
            return
        if len(running_types) == 1:
            self._show_type_embedded(running_types[0])
            return

        self._show_summary_panels()
        self._hide_details()
        self.placeholder.pack(fill=BOTH, expand=True, pady=20)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()

    def _show_type_detail(self, dtype: str) -> None:
        view = self.type_views.get(dtype)
        frame = self.type_detail_frames.get(dtype)
        if view is None or frame is None:
            return
        self._hide_summary_panels()
        self._hide_details()
        view.set_local_monitoring_button_visible(True)
        view.set_force_inventory_visible(True)
        frame.pack(fill=BOTH, expand=True)
        self.current_detail = dtype
        self.active_tree_filter = None
        self._update_nav_buttons()
        view.update_display()

    def _show_global_detail(self) -> None:
        self._hide_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(True)
        self.consolidated_app.set_force_inventory_visible(True)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "global"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.consolidated_app.update_display()

    def _show_type_filtered(self, dtype: str, status: str | None) -> None:
        view = self.type_views.get(dtype)
        frame = self.type_detail_frames.get(dtype)
        if view is None or frame is None:
            return
        self._show_summary_panels()
        self._hide_details()
        view.set_local_monitoring_button_visible(False)
        view.set_force_inventory_visible(status is None)
        frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = (dtype, status)
        self._update_nav_buttons()
        view.update_display()
        self._apply_active_tree_filter()

    def _show_global_filtered(self, status: str | None = None) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(False)
        self.consolidated_app.set_force_inventory_visible(status is None)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = ("global", status)
        self._update_nav_buttons()
        self.consolidated_app.update_display()
        self._apply_active_tree_filter()

    def _show_type_embedded(self, dtype: str) -> None:
        view = self.type_views.get(dtype)
        frame = self.type_detail_frames.get(dtype)
        if view is None or frame is None:
            return
        self._show_summary_panels()
        self._hide_details()
        view.set_local_monitoring_button_visible(False)
        view.set_force_inventory_visible(False)
        frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()
        view.update_display()

    def _show_global_embedded(self) -> None:
        self._show_summary_panels()
        self._hide_details()
        self.consolidated_app.set_local_monitoring_button_visible(False)
        self.consolidated_app.set_force_inventory_visible(False)
        self.global_detail_frame.pack(fill=BOTH, expand=True)
        self.current_detail = "dashboard"
        self.active_tree_filter = None
        self._update_nav_buttons()
        self.consolidated_app.update_display()

    def _apply_active_tree_filter(self) -> None:
        if not self.active_tree_filter:
            for dtype, view in self.type_views.items():
                self._filter_tree(view.tree, self.model.device_data.get(dtype, {}), None)
            self._filter_consolidated_tree(self.consolidated_app.tree, self.model.device_data, None)
            return

        target, status_filter = self.active_tree_filter
        if target in self.type_views:
            self._filter_tree(self.type_views[target].tree, self.model.device_data.get(target, {}), status_filter)
            return
        if target == "global":
            self._filter_consolidated_tree(self.consolidated_app.tree, self.model.device_data, status_filter)

    @staticmethod
    def _filter_tree(tree, devices: dict, status_filter: str | None) -> None:
        for did, dev in devices.items():
            iid = str(did)
            if not tree.exists(iid):
                continue
            status = getattr(dev, "status", "")
            if status_filter and status != status_filter:
                tree.detach(iid)
            else:
                tree.reattach(iid, "", "end")

    @staticmethod
    def _filter_consolidated_tree(tree, devices_by_type: dict, status_filter: str | None) -> None:
        for dtype, devices in devices_by_type.items():
            for did, dev in devices.items():
                iid = f"{dtype}::{did}"
                if not tree.exists(iid):
                    continue
                status = getattr(dev, "status", "")
                if status_filter and status != status_filter:
                    tree.detach(iid)
                else:
                    tree.reattach(iid, "", "end")

    def _update_nav_buttons(self) -> None:
        base = self.theme.colors["nav_inactive_bg"]
        active = self.theme.colors["nav_active_bg"]
        fg = self.theme.colors["text_primary"]
        for name, btn in (
            ("dashboard", self.btn_dashboard),
            *[(dtype, btn) for dtype, btn in self.type_nav_buttons.items()],
            ("global", self.btn_global),
        ):
            btn.config(
                bg=active if self.current_detail == name else base,
                fg=fg,
                relief="sunken" if self.current_detail == name else "raised",
            )

    def _toggle_monitoring_target(self, target: str) -> None:
        self.controller.view = self
        if target in self.type_views:
            self._show_type_embedded(target)
        if target == "global":
            self._show_global_embedded()

        if target == "global":
            if any(self.model.do_run.values()):
                self.controller.stop_all_monitoring()
            else:
                for dtype in self._monitored_type_codes():
                    self.controller.start_monitoring(dtype)
            self.update_display()
            return

        if target in self.type_views:
            if self.model.do_run.get(target, False):
                self.controller.stop_monitoring(target)
            else:
                self.controller.start_monitoring(target)
        self.update_display()


