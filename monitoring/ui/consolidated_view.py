# src/monitoring/ui/consolidated_view.py

from __future__ import annotations

import ipaddress
import logging
import webbrowser
from tkinter import Frame, Menu, IntVar, simpledialog, messagebox
from typing import Any, Tuple

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.view_mixins import ContextMenuMixin

LOGGER = logging.getLogger(__name__)


class ConsolidatedView(DeviceListView, ContextMenuMixin):
    """
    Vue globale (switch + server) fusionnée, sans gestion du monitoring
    dans le menu contextuel. Se met à jour via AppController._refresh_all_views()
    ou start_monitoring(), avec désélection automatique.
    """

    device_type: str = "consolidated"
    columns: Tuple[str, ...] = ("type", "name", "ip", "status")
    headings = {
        "type":   "Type",
        "name":   "Nom",
        "ip":     "IP",
        "status": "Statut",
    }

    def __init__(
        self,
        parent: Frame,
        *,
        model: DevicesModel | None = None,
        controller: AppController | None = None,
    ) -> None:
        """Initialise la vue globale et affiche immédiatement son contenu."""
        self.total_devices   = IntVar(value=0)
        self.online_devices  = IntVar(value=0)
        self.offline_devices = IntVar(value=0)

        super().__init__(parent, model=model, controller=controller)

        # Fusion des flags notify switch+server
        try:
            merged: dict[str, bool] = {}
            for dtype in ("switch", "server"):
                for did, flag in self.model.notify_flags.get(dtype, {}).items():
                    merged[f"{dtype}-{did}"] = flag
            self.model.notify_flags[self.device_type] = merged
        except Exception:
            LOGGER.exception("Impossible d'initialiser notify_flags pour 'consolidated'")

        # Masquer icône & toggle individuel
        self.tree.configure(show=("headings",))
        self.btn_toggle.pack_forget()

        # Clic-droit & double-clic
        self.bind_context_menu_with_pause(self.tree, self._build_context_menu)
        self.tree.bind("<Double-1>", self._on_double_click)

        # Affichage initial
        self.update_display()

    def start_monitoring(self) -> None:
        """
        Méthode appelée par le Dashboard pour démarrer globalement
        et rafraîchir instantanément. Désélectionne tout avant.
        """
        # Désélection dans toutes les vues
        for v in getattr(self.controller, "views", []):
            try:
                v.tree.selection_remove(*v.tree.selection())
            except Exception:
                pass

        # Forcer un update
        try:
            self.update_display()
        except Exception:
            LOGGER.exception("Erreur dans start_monitoring() de la vue globale")

    def _on_add(self) -> None:
        # … inchangé …
        dtype = simpledialog.askstring("Ajouter", "Type (switch/server) ?")
        if dtype not in ("switch", "server"):
            return

        form = DeviceForm(self.parent, title=f"Ajouter {dtype}", default_type=dtype)
        if form.result is None:
            return
        data = form.result

        try:
            if dtype == "switch":
                ok = self.model.add_device(
                    "switch",
                    data["name"], data["ip"], data["desc"],
                    notify=data.get("notify", True),
                )
            else:
                ok = self.model.add_device(
                    "server",
                    data["name"], data["ip"], data["desc"],
                    id_Teamviewer=data.get("tv_id", ""),
                    device_subtype=data.get("subtype", ""),
                    notify=data.get("notify", True),
                )
            if not ok:
                messagebox.showwarning("Duplication", "IP déjà utilisée.")
        except Exception:
            LOGGER.exception("Erreur ajout device")
        finally:
            self.refresh_paused = False
            self.controller._refresh_all_views()

    def _on_edit(self) -> None:
        # … inchangé …
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Modifier", "Sélectionnez un device.")
            return
        iid = sel[0]
        dtype, did = iid.split("-", 1)
        dev = self.model.device_data.get(dtype, {}).get(did)
        if not dev:
            return

        initial = {
            "name": dev.name,
            "ip": dev.ip,
            "desc": getattr(dev, "description", ""),
            "notify": self.model.notify_flags.get(dtype, {}).get(did, True),
        }
        if dtype == "server":
            initial.update(
                subtype=getattr(dev, "type", ""),
                tv_id=getattr(dev, "id_Teamviewer", ""),
            )

        form = DeviceForm(
            self.parent,
            title=f"Modifier {dtype.capitalize()}",
            default_type=dtype,
            initial=initial,
        )
        if form.result is None:
            return
        data = form.result

        try:
            if dtype == "switch":
                ok = self.model.update_device(
                    "switch", did,
                    new_name=data["name"],
                    new_ip=data["ip"],
                    new_description=data["desc"],
                    notify=data.get("notify", True),
                )
            else:
                ok = self.model.update_device(
                    "server", did,
                    new_name=data["name"],
                    new_ip=data["ip"],
                    new_description=data["desc"],
                    id_Teamviewer=data.get("tv_id", ""),
                    device_subtype=data.get("subtype", ""),
                    notify=data.get("notify", True),
                )
            if not ok:
                messagebox.showerror("Erreur", "Échec de la mise à jour.")
        except Exception:
            LOGGER.exception("Erreur modification device")
        finally:
            self.refresh_paused = False
            self.controller._refresh_all_views()

    def _on_delete(self) -> None:
        # … inchangé …
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Supprimer", "Sélectionnez un device.")
            return
        iid = sel[0]
        dtype, did = iid.split("-", 1)
        if messagebox.askyesno("Confirmation", f"Supprimer ce {dtype}?"):
            try:
                self.model.delete_device(dtype, did)
            except Exception:
                LOGGER.exception("Erreur suppression device")
            finally:
                self.refresh_paused = False
                self.controller._refresh_all_views()

    def update_display(self) -> None:
        # … inchangé …
        if self.refresh_paused or self.is_locked_view():
            return

        try:
            records: list[tuple[str, str, Any]] = []
            for dtype in ("switch", "server"):
                for did, dev in self.model.device_data.get(dtype, {}).items():
                    records.append((dtype, did, dev))

            if self.sort_col:
                key_funcs = {
                    "type":   lambda x: x[0].lower(),
                    "name":   lambda x: x[2].name.lower(),
                    "ip":     lambda x: ipaddress.ip_address(x[2].ip),
                    "status": lambda x: x[2].status,
                }
                records.sort(key=key_funcs[self.sort_col], reverse=self.sort_reverse)

            self.tree.config(height=max(len(records), 5))
            self.tree.delete(*self.tree.get_children())

            tot = on = off = 0
            for dtype, did, dev in records:
                iid = f"{dtype}-{did}"
                status_txt = "🟢 Online" if dev.status == "online" else "🔴 Offline"
                self.tree.insert(
                    "", "end",
                    iid=iid,
                    values=(dtype.capitalize(), dev.name, dev.ip, status_txt),
                    tags=(dev.status,),
                )
                tot += 1
                if dev.status == "online":
                    on += 1
                else:
                    off += 1

            self.total_devices.set(tot)
            self.online_devices.set(on)
            self.offline_devices.set(off)

        except Exception:
            LOGGER.exception("Erreur update_display global")

    def _build_context_menu(self) -> Menu:
        """
        Hérite Add/Edit/Delete/Alert seul (pas de toggle monitoring).
        """
        menu = super()._build_context_menu()
        # supprime tout ce qui pourrait rester après le 2ᵉ separator
        try:
            end = menu.index("end")
            seps = [i for i in range(end+1) if menu.type(i) == "separator"]
            if len(seps) >= 2:
                for idx in range(seps[1] + 1, end + 1)[::-1]:
                    menu.delete(idx)
        except Exception:
            pass
        return menu

    def _on_double_click(self, _evt=None) -> None:
        # … inchangé …
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        dtype, did = iid.split("-", 1)
        dev = self.model.device_data.get(dtype, {}).get(did)
        if not dev:
            return

        try:
            if dtype == "switch":
                webbrowser.open(f"http://{dev.ip}")
            else:
                typ = getattr(dev, "type", "").lower()
                tv = getattr(dev, "id_Teamviewer", "")
                if typ == "windows" and tv:
                    url = f"https://start.teamviewer.com/{tv}"
                elif typ == "dsm":
                    url = f"http://{dev.ip}:5000"
                else:
                    url = f"http://{dev.ip}"
                webbrowser.open(url)
        except Exception as exc:
            LOGGER.exception("Erreur ouverture URL : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d’ouvrir l’interface pour {dev.ip}")
