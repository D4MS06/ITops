# src/monitoring/ui/consolidated_view.py

from __future__ import annotations

import ipaddress
import logging
import shutil
import subprocess
import webbrowser
from tkinter import Frame, IntVar, Menu, messagebox
from typing import Any, Tuple

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.view_mixins import ContextMenuMixin

LOGGER = logging.getLogger(__name__)


class ConsolidatedView(DeviceListView, ContextMenuMixin):
    """Vue globale fusionnant switch et server."""

    device_type: str = "consolidated"
    columns: Tuple[str, ...] = ("type", "name", "ip", "desc", "status")
    headings = {
        "type": "Type",
        "name": "Nom",
        "ip": "IP",
        "desc": "Description",
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
        self.total_devices = IntVar(value=0)
        self.online_devices = IntVar(value=0)
        self.offline_devices = IntVar(value=0)

        super().__init__(parent, model=model, controller=controller)

        try:
            merged: dict[str, bool] = {}
            for dtype in ("switch", "server"):
                for did, flag in self.model.notify_flags.get(dtype, {}).items():
                    merged[f"{dtype}-{did}"] = flag
            self.model.notify_flags[self.device_type] = merged
        except Exception:
            LOGGER.exception("Impossible d'initialiser notify_flags pour 'consolidated'")

        self.tree.configure(show=("headings",))
        self.tree.column("type", width=100, minwidth=90, stretch=False, anchor="w")
        self.tree.column("name", width=190, minwidth=150, stretch=True, anchor="w")
        self.tree.column("ip", width=130, minwidth=120, stretch=False, anchor="w")
        self.tree.column("desc", width=320, minwidth=220, stretch=True, anchor="w")
        self.tree.column("status", width=130, minwidth=120, stretch=False, anchor="w")
        self.btn_toggle.config(command=self._toggle_monitoring_global)

        self.bind_context_menu_with_pause(self.tree, self._build_context_menu)
        self.tree.bind("<Double-1>", self._on_double_click)

        self.update_display()

    def start_monitoring(self) -> None:
        """Rafraîchit la vue globale après désélection des autres vues."""
        for view in getattr(self.controller, "views", []):
            try:
                view.tree.selection_remove(*view.tree.selection())
            except Exception:
                pass

        try:
            self.update_display()
        except Exception:
            LOGGER.exception("Erreur dans start_monitoring() de la vue globale")

    def _toggle_monitoring_global(self) -> None:
        self.refresh_paused = False
        self.controller.view = self
        if any(self.model.do_run.values()):
            self.controller.stop_all_monitoring()
        else:
            self.controller.start_monitoring("switch")
            self.controller.start_monitoring("server")
        self.update_display()

    def _on_add(self) -> None:
        form = DeviceForm(self.parent, title="Ajouter un appareil")
        if form.result is None:
            return
        data = form.result
        dtype = data.get("kind")
        if dtype not in ("switch", "server"):
            return

        try:
            if dtype == "switch":
                ok = self.model.add_device(
                    "switch",
                    data["name"],
                    data["ip"],
                    data["desc"],
                    notify=data.get("notify", True),
                )
            else:
                ok = self.model.add_device(
                    "server",
                    data["name"],
                    data["ip"],
                    data["desc"],
                    id_Teamviewer=data.get("tv_id", ""),
                    device_subtype=data.get("subtype", ""),
                    action_double_click=data.get("action_double_click", ""),
                    web_url=data.get("web_url", ""),
                    ssh_user=data.get("ssh_user", ""),
                    notify=data.get("notify", True),
                )
            if not ok:
                messagebox.showwarning("Duplication", "IP deja utilisee.")
        except Exception:
            LOGGER.exception("Erreur ajout device")
        finally:
            self.refresh_paused = False
            self.controller._refresh_all_views()

    def _on_edit(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Modifier", "Selectionnez un device.")
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
                action_double_click=getattr(dev, "action_double_click", ""),
                web_url=getattr(dev, "web_url", ""),
                ssh_user=getattr(dev, "ssh_user", ""),
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
                    "switch",
                    did,
                    new_name=data["name"],
                    new_ip=data["ip"],
                    new_description=data["desc"],
                    notify=data.get("notify", True),
                )
            else:
                ok = self.model.update_device(
                    "server",
                    did,
                    new_name=data["name"],
                    new_ip=data["ip"],
                    new_description=data["desc"],
                    id_Teamviewer=data.get("tv_id", ""),
                    device_subtype=data.get("subtype", ""),
                    action_double_click=data.get("action_double_click", ""),
                    web_url=data.get("web_url", ""),
                    ssh_user=data.get("ssh_user", ""),
                    notify=data.get("notify", True),
                )
            if not ok:
                messagebox.showerror("Erreur", "Echec de la mise a jour.")
        except Exception:
            LOGGER.exception("Erreur modification device")
        finally:
            self.refresh_paused = False
            self.controller._refresh_all_views()

    def _on_delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Supprimer", "Selectionnez un device.")
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
        if self.refresh_paused or self.is_locked_view():
            return

        try:
            records: list[tuple[str, str, Any]] = []
            for dtype in ("switch", "server"):
                for did, dev in self.model.device_data.get(dtype, {}).items():
                    records.append((dtype, did, dev))

            query = self.search_var.get().strip().lower()
            if query:
                records = [
                    (dtype, did, dev)
                    for dtype, did, dev in records
                    if query in " ".join(
                        [
                            str(dtype),
                            str(did),
                            str(getattr(dev, "name", "")),
                            str(getattr(dev, "ip", "")),
                            str(getattr(dev, "description", "")),
                            str(getattr(dev, "status", "")),
                            str(getattr(dev, "type", "")),
                        ]
                    ).lower()
                ]

            if self.sort_col:
                key_funcs = {
                    "type": lambda x: str(x[0]).lower(),
                    "name": lambda x: str(getattr(x[2], "name", "")).lower(),
                    "ip": lambda x: ipaddress.ip_address(str(getattr(x[2], "ip", ""))),
                    "desc": lambda x: str(getattr(x[2], "description", "")).lower(),
                    "status": lambda x: str(getattr(x[2], "status", "")).lower(),
                }
                key_fn = key_funcs.get(str(self.sort_col))
                if key_fn is not None:
                    records.sort(key=key_fn, reverse=self.sort_reverse)

            self.tree.config(height=max(len(records), 5))
            desired_iids = [f"{dtype}-{did}" for dtype, did, _ in records]
            desired_set = set(desired_iids)

            stale_iids = [iid for iid in set(self._row_state).difference(desired_set) if self.tree.exists(iid)]
            if stale_iids:
                self.tree.delete(*stale_iids)
            for iid in stale_iids:
                self._row_state.pop(iid, None)

            tot = on = off = 0
            for dtype, did, dev in records:
                iid = f"{dtype}-{did}"
                status_txt = "Online" if dev.status == "online" else "Offline"
                values = (
                    dtype.capitalize(),
                    dev.name,
                    dev.ip,
                    getattr(dev, "description", ""),
                    status_txt,
                )
                state_sig = (dev.status, values)
                if not self.tree.exists(iid):
                    self.tree.insert("", "end", iid=iid, values=values, tags=(dev.status,))
                elif self._row_state.get(iid) != state_sig:
                    self.tree.item(iid, values=values, tags=(dev.status,))
                self._row_state[iid] = state_sig
                tot += 1
                if dev.status == "online":
                    on += 1
                else:
                    off += 1

            for idx, iid in enumerate(desired_iids):
                if self.tree.exists(iid):
                    try:
                        self.tree.move(iid, "", idx)
                    except Exception:
                        pass

            self.total_devices.set(tot)
            self.online_devices.set(on)
            self.offline_devices.set(off)

            running_switch = self.model.do_run.get("switch", False)
            running_server = self.model.do_run.get("server", False)
            running_any = running_switch or running_server
            self.btn_toggle.config(
                text="Arreter Global" if running_any else "Demarrer Global",
                bg="#27ae60" if running_any else "#9e9e9e",
                activebackground="#27ae60" if running_any else "#9e9e9e",
                fg="white",
            )

        except Exception:
            LOGGER.exception("Erreur update_display global")

    def _build_context_menu(self) -> Menu:
        """Menu contextuel sans toggle monitoring."""
        menu = super()._build_context_menu()
        try:
            end = menu.index("end")
            seps = [i for i in range(end + 1) if menu.type(i) == "separator"]
            if len(seps) >= 2:
                for idx in range(seps[1] + 1, end + 1)[::-1]:
                    menu.delete(idx)
        except Exception:
            pass
        return menu

    def _on_double_click(self, _evt=None) -> None:
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
                return

            typ = str(getattr(dev, "type", "")).strip().lower()
            ip = str(getattr(dev, "ip", "")).strip()
            tv = str(getattr(dev, "id_Teamviewer", "")).strip()
            action = str(getattr(dev, "action_double_click", "")).strip().lower()
            web_url = str(getattr(dev, "web_url", "")).strip()
            ssh_user = str(getattr(dev, "ssh_user", "")).strip()

            if not action:
                if typ == "windows":
                    action = "teamviewer" if tv else "remote_desktop"
                elif typ == "linux":
                    action = "ssh"
                else:
                    action = "web"

            if action == "teamviewer":
                if tv:
                    webbrowser.open(f"https://start.teamviewer.com/{tv}")
                else:
                    subprocess.Popen(["mstsc", f"/v:{ip}"])
                return

            if action == "remote_desktop":
                subprocess.Popen(["mstsc", f"/v:{ip}"])
                return

            if action == "ssh":
                if ssh_user:
                    target = f"{ssh_user}@{ip}"
                    if shutil.which("wt"):
                        subprocess.Popen(["wt", "ssh", target])
                    else:
                        subprocess.Popen(["cmd", "/c", "start", "ssh", target])
                else:
                    subprocess.Popen(["cmd.exe", "/k", f"set /p u=SSH login: && ssh %u%@{ip}"])
                return

            if web_url:
                url = web_url
            elif typ == "dsm":
                url = f"http://{ip}:5000"
            else:
                url = f"http://{ip}"
            webbrowser.open(url)
        except Exception as exc:
            LOGGER.exception("Erreur ouverture URL : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir l'interface pour {dev.ip}")
