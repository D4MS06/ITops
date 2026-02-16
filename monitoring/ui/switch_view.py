# src/monitoring/ui/switch_view.py

from __future__ import annotations

import logging
import webbrowser
from tkinter import Frame, Menu, messagebox

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.dialogs.device_form import DeviceForm

LOGGER = logging.getLogger(__name__)


class SwitchIHM(DeviceListView):
    """IHM de monitoring des switches."""

    device_type = "switch"
    columns = ("name", "ip", "desc")
    headings = {"name": "Nom", "ip": "IP", "desc": "Description"}
    tag_configs: dict[str, dict] = {}

    def __init__(
        self,
        parent: Frame,
        *,
        model: DevicesModel | None = None,
        controller: AppController | None = None,
    ) -> None:
        super().__init__(parent, model=model, controller=controller)
        self.update_display()

    def _on_add(self) -> None:
        dlg = DeviceForm(self.parent, title="Ajouter un switch", default_type="switch")
        if dlg.result is None:
            return
        d = dlg.result
        success = self.model.add_device(
            "switch",
            d["name"],
            d["ip"],
            d["desc"],
            notify=d.get("notify", True),
        )
        if not success:
            messagebox.showwarning("Duplication", "IP deja utilisee.")
        self.refresh_paused = False
        self.controller._refresh_all_views()

    def _on_edit(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Modifier", "Selectionnez un switch.")
            return
        did = sel[0]
        dev = self.model.device_data["switch"][did]
        initial = {
            "name": dev.name,
            "ip": dev.ip,
            "desc": dev.description,
            "notify": self.model.notify_flags["switch"].get(did, True),
        }
        dlg = DeviceForm(
            self.parent,
            title="Modifier Switch",
            default_type="switch",
            initial=initial,
        )
        if dlg.result is None:
            return
        d = dlg.result
        ok = self.model.update_device(
            "switch",
            did,
            new_name=d["name"],
            new_ip=d["ip"],
            new_description=d["desc"],
            notify=d.get("notify", True),
        )
        if not ok:
            messagebox.showerror("Erreur", "Echec de la mise a jour.")
        self.refresh_paused = False
        self.controller._refresh_all_views()

    def _on_delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Supprimer", "Selectionnez un switch.")
            return
        if messagebox.askyesno("Confirmation", "Supprimer ce switch ?"):
            self.model.delete_device("switch", sel[0])
            self.refresh_paused = False
            self.controller._refresh_all_views()

    def _on_double_click(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        dev = self.model.device_data["switch"].get(sel[0])
        if not dev:
            return
        try:
            webbrowser.open(f"http://{dev.ip}")
        except Exception as exc:
            LOGGER.exception("Erreur ouverture IP switch : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir {dev.ip}")

    def _build_context_menu(self) -> Menu:
        menu = super()._build_context_menu()
        sel = self.tree.selection()
        if sel:
            dev = self.model.device_data["switch"].get(sel[0])
            if dev:
                menu.add_separator()
                self._add_network_tools_submenu(menu, str(dev.ip).strip())
        return menu

    def _on_selection_mutual(self, _evt=None) -> None:
        try:
            self.parent.master.server_view.tree.selection_remove(
                *self.parent.master.server_view.tree.selection()
            )
        except Exception:
            pass
        try:
            self.parent.master.consolidated_app.tree.selection_remove(
                *self.parent.master.consolidated_app.tree.selection()
            )
        except Exception:
            pass
