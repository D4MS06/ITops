# src/monitoring/ui/server_view.py

from __future__ import annotations

import logging
import webbrowser
from tkinter import Frame, messagebox
from tkinter import BOTH, LEFT, TOP

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.dialogs.device_form import DeviceForm

LOGGER = logging.getLogger(__name__)


class ServerIHM(DeviceListView):
    """IHM de monitoring des serveurs."""

    device_type = "server"
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
        dlg = DeviceForm(self.parent, title="Ajouter un serveur", default_type="server")
        if dlg.result is None:
            return
        d = dlg.result
        success = self.model.add_device(
            "server",
            d["name"],
            d["ip"],
            d["desc"],
            id_Teamviewer=d.get("tv_id", ""),
            device_subtype=d.get("subtype", ""),
            notify=d.get("notify", True),
        )
        if not success:
            messagebox.showwarning("Duplication", "IP déjà utilisée.")
        self.refresh_paused = False
        self.controller._refresh_all_views()

    def _on_edit(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Modifier", "Sélectionnez un serveur.")
            return
        did = sel[0]
        dev = self.model.device_data["server"][did]
        initial = {
            "name": dev.name,
            "ip": dev.ip,
            "desc": dev.description,
            "subtype": getattr(dev, "type", ""),
            "tv_id": getattr(dev, "id_Teamviewer", ""),
            "notify": self.model.notify_flags["server"].get(did, True),
        }
        dlg = DeviceForm(
            self.parent,
            title="Modifier Serveur",
            default_type="server",
            initial=initial,
        )
        if dlg.result is None:
            return
        d = dlg.result
        ok = self.model.update_device(
            "server",
            did,
            new_name=d["name"],
            new_ip=d["ip"],
            new_description=d["desc"],
            id_Teamviewer=d.get("tv_id", ""),
            device_subtype=d.get("subtype", ""),
            notify=d.get("notify", True),
        )
        if not ok:
            messagebox.showerror("Erreur", "Échec de la mise à jour.")
        self.refresh_paused = False
        self.controller._refresh_all_views()

    def _on_delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Supprimer", "Sélectionnez un serveur.")
            return
        if messagebox.askyesno("Confirmation", "Supprimer ce serveur ?"):
            self.model.delete_device("server", sel[0])
            self.refresh_paused = False
            self.controller._refresh_all_views()

    def _on_double_click(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        dev = self.model.device_data["server"].get(sel[0])
        if not dev:
            return
        try:
            if getattr(dev, "type", "").lower() == "windows" and getattr(dev, "id_Teamviewer", ""):
                webbrowser.open(f"https://start.teamviewer.com/{dev.id_Teamviewer}")
            elif getattr(dev, "type", "").lower() == "dsm":
                webbrowser.open(f"http://{dev.ip}:5000")
            else:
                webbrowser.open(f"http://{dev.ip}")
        except Exception as exc:
            LOGGER.exception("Erreur ouverture URL serveur : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d’ouvrir {dev.ip}")

    def _on_selection_mutual(self, _evt=None) -> None:
        try:
            self.parent.master.switch_view.tree.selection_remove(
                *self.parent.master.switch_view.tree.selection()
            )
        except Exception:
            pass
        try:
            self.parent.master.consolidated_app.tree.selection_remove(
                *self.parent.master.consolidated_app.tree.selection()
            )
        except Exception:
            pass
