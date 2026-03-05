from __future__ import annotations

import ipaddress
import logging
import shutil
import subprocess
import webbrowser
from pathlib import Path
from tkinter import Frame, IntVar, Menu, filedialog, messagebox
from typing import Any, Tuple

from monitoring.config.settings import load_settings
from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.utils.action_compat import action_allows_os
from monitoring.ui.view_mixins import ContextMenuMixin
from monitoring.utils.config_files import find_switch_config_files, resolve_switch_configs_dir

LOGGER = logging.getLogger(__name__)


class ConsolidatedView(DeviceListView, ContextMenuMixin):
    """Global view combining all device types."""

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
        self.total_devices = IntVar(value=0)
        self.online_devices = IntVar(value=0)
        self.offline_devices = IntVar(value=0)
        self._mgr = SQLiteFileManager()

        super().__init__(parent, model=model, controller=controller)

        self.tree.configure(show=("tree", "headings"))
        self.tree.heading("#0", text="Statut", anchor="center")
        self.tree.column("#0", width=56, minwidth=56, stretch=False, anchor="center")
        self.tree.column("type", width=120, minwidth=100, stretch=False, anchor="w")
        self.tree.column("name", width=190, minwidth=150, stretch=True, anchor="w")
        self.tree.column("ip", width=130, minwidth=120, stretch=False, anchor="w")
        self.tree.column("desc", width=320, minwidth=220, stretch=True, anchor="w")
        self.tree.column("status", width=130, minwidth=120, stretch=False, anchor="w")
        self.btn_toggle.config(command=self._toggle_monitoring_global)

        self.bind_context_menu_with_pause(self.tree, self._build_context_menu)
        self.tree.bind("<Double-1>", self._on_double_click)

        self.update_display()

    @staticmethod
    def _iid(dtype: str, did: str) -> str:
        return f"{dtype}::{did}"

    @staticmethod
    def _parse_iid(iid: str) -> tuple[str, str] | tuple[None, None]:
        if "::" not in iid:
            return None, None
        dtype, did = iid.split("::", 1)
        return dtype, did

    def _selected_record(self) -> tuple[str, str, Any] | tuple[None, None, None]:
        sel = self.tree.selection()
        if not sel:
            return None, None, None
        dtype, did = self._parse_iid(str(sel[0]))
        if not dtype or not did:
            return None, None, None
        dev = self.model.device_data.get(dtype, {}).get(did)
        if dev is None:
            return None, None, None
        return dtype, did, dev

    def start_monitoring(self) -> None:
        for view in getattr(self.controller, "views", []):
            try:
                view.tree.selection_remove(*view.tree.selection())
            except Exception:
                pass

        try:
            self.update_display()
        except Exception:
            LOGGER.exception("Error in global start_monitoring")

    def _toggle_monitoring_global(self) -> None:
        self.refresh_paused = False
        self.controller.view = self
        running_types = [dtype for dtype, running in self.model.do_run.items() if bool(running)]
        if running_types:
            self.controller.stop_all_monitoring()
        else:
            for dtype in list(self.model.do_run.keys()):
                self.controller.start_monitoring(dtype)
        self.update_display()

    def _on_add(self) -> None:
        form = DeviceForm(self.parent, title="Ajouter un appareil")
        if form.result is None:
            return
        data = form.result
        dtype = str(data.get("kind", "")).strip()
        if not dtype:
            return

        try:
            ok = self.model.add_device(
                dtype,
                data["name"],
                data["ip"],
                data["desc"],
                id_Teamviewer=data.get("tv_id", ""),
                device_subtype=data.get("subtype", ""),
                action_double_click=data.get("action_double_click", ""),
                web_url=data.get("web_url", ""),
                ssh_user=data.get("ssh_user", ""),
                custom_data=data.get("custom_data", {}),
                notify=data.get("notify", True),
            )
            if not ok:
                messagebox.showwarning("Duplication", "IP deja utilisee.")
        except Exception:
            LOGGER.exception("Error adding device")
        finally:
            self.refresh_paused = False
            self.controller._refresh_all_views()

    def _on_edit(self) -> None:
        dtype, did, dev = self._selected_record()
        if dev is None or dtype is None or did is None:
            messagebox.showinfo("Modifier", "Selectionnez un device.")
            return

        initial = {
            "kind": dtype,
            "name": dev.name,
            "ip": dev.ip,
            "desc": getattr(dev, "description", ""),
            "notify": self.model.notify_flags.get(dtype, {}).get(did, True),
            "subtype": getattr(dev, "type", ""),
            "tv_id": getattr(dev, "id_Teamviewer", ""),
            "action_double_click": getattr(dev, "action_double_click", ""),
            "web_url": getattr(dev, "web_url", ""),
            "ssh_user": getattr(dev, "ssh_user", ""),
            "custom_data": self.model.extract_custom_data(dev),
        }

        form = DeviceForm(
            self.parent,
            title=f"Modifier {dtype}",
            default_type=dtype,
            initial=initial,
        )
        if form.result is None:
            return
        data = form.result

        try:
            ok = self.model.update_device(
                dtype,
                did,
                new_name=data["name"],
                new_ip=data["ip"],
                new_description=data["desc"],
                id_Teamviewer=data.get("tv_id", ""),
                device_subtype=data.get("subtype", ""),
                action_double_click=data.get("action_double_click", ""),
                web_url=data.get("web_url", ""),
                ssh_user=data.get("ssh_user", ""),
                custom_data=data.get("custom_data", {}),
                notify=data.get("notify", True),
            )
            if not ok:
                messagebox.showerror("Erreur", "Echec de la mise a jour.")
        except Exception:
            LOGGER.exception("Error editing device")
        finally:
            self.refresh_paused = False
            self.controller._refresh_all_views()

    def _on_delete(self) -> None:
        dtype, did, _dev = self._selected_record()
        if not dtype or not did:
            messagebox.showinfo("Supprimer", "Selectionnez un device.")
            return
        if messagebox.askyesno("Confirmation", f"Supprimer ce {dtype} ?"):
            try:
                self.model.delete_device(dtype, did)
            except Exception:
                LOGGER.exception("Error deleting device")
            finally:
                self.refresh_paused = False
                self.controller._refresh_all_views()

    def update_display(self) -> None:
        if self.refresh_paused or self.is_locked_view():
            return

        try:
            records: list[tuple[str, str, Any]] = []
            for dtype in sorted(self.model.device_data.keys()):
                for did, dev in self.model.device_data.get(dtype, {}).items():
                    records.append((dtype, did, dev))

            query = self.search_var.get().strip().lower()
            if query:
                records = [
                    (dtype, did, dev)
                    for dtype, did, dev in records
                    if query
                    in " ".join(
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
            desired_iids = [self._iid(dtype, did) for dtype, did, _ in records]
            desired_set = set(desired_iids)

            stale_iids = [iid for iid in set(self._row_state).difference(desired_set) if self.tree.exists(iid)]
            if stale_iids:
                self.tree.delete(*stale_iids)
            for iid in stale_iids:
                self._row_state.pop(iid, None)

            total = online = offline = 0
            for dtype, did, dev in records:
                iid = self._iid(dtype, did)
                status_map = {"online": "Online", "offline": "Offline", "idle": "Idle"}
                status_txt = status_map.get(str(dev.status).lower(), str(dev.status).capitalize())
                icon = {
                    "online": self.img_online,
                    "offline": self.img_offline,
                    "idle": self.img_idle,
                }.get(dev.status, self.img_idle)
                values = (
                    str(self.model.type_definitions.get(dtype, {}).get("label", dtype)).strip() or dtype,
                    dev.name,
                    dev.ip,
                    getattr(dev, "description", ""),
                    status_txt,
                )
                state_sig = (dev.status, values)
                if not self.tree.exists(iid):
                    self.tree.insert("", "end", iid=iid, image=icon, values=values, tags=(dev.status,))
                elif self._row_state.get(iid) != state_sig:
                    self.tree.item(iid, image=icon, values=values, tags=(dev.status,))
                self._row_state[iid] = state_sig

                total += 1
                if dev.status == "online":
                    online += 1
                elif dev.status == "offline":
                    offline += 1

            for idx, iid in enumerate(desired_iids):
                if self.tree.exists(iid):
                    try:
                        self.tree.move(iid, "", idx)
                    except Exception:
                        pass

            self.total_devices.set(total)
            self.online_devices.set(online)
            self.offline_devices.set(offline)

            running_any = any(bool(v) for v in self.model.do_run.values())
            self.btn_toggle.config(
                text="Arreter Global" if running_any else "Demarrer Global",
                bg=self.theme.colors["button_active_bg"] if running_any else self.theme.colors["button_inactive_bg"],
                activebackground=self.theme.colors["button_active_bg"]
                if running_any
                else self.theme.colors["button_inactive_bg"],
                fg=self.theme.colors["button_active_fg"] if running_any else self.theme.colors["button_inactive_fg"],
            )
            self._set_placeholder_visible(
                (not running_any) and (not self.force_inventory_visible),
                title="Monitoring global arrete",
                subtitle="Demarrez le monitoring global pour afficher les equipements en temps reel.",
            )

        except Exception:
            LOGGER.exception("Error global update_display")

    @staticmethod
    def _switch_configs_root_dir() -> Path:
        settings = load_settings()
        configured = str(getattr(settings, "switch_configs_dir", "") or "").strip()
        return resolve_switch_configs_dir(configured)

    def _download_config_for_selected(self) -> None:
        dtype, _did, dev = self._selected_record()
        if dev is None or dtype is None:
            messagebox.showinfo("Configurations", "Selectionnez un equipement.")
            return
        if not self.model.is_config_download_type(dtype):
            messagebox.showinfo("Configurations", "Le type selectionne ne supporte pas le telechargement de conf.")
            return

        root_dir = self._switch_configs_root_dir()
        matches = find_switch_config_files(root_dir, str(getattr(dev, "name", "")), str(getattr(dev, "ip", "")))
        if not matches:
            messagebox.showinfo(
                "Configurations",
                f"Aucun fichier trouve pour {dev.name} ({dev.ip}).\nDossier scanne: {root_dir}",
            )
            return

        source = matches[0]
        filename = source.name
        target = filedialog.asksaveasfilename(
            parent=self.parent,
            title="Telecharger la conf",
            initialfile=filename,
            defaultextension=source.suffix or ".cfg",
            filetypes=[("Config", "*.cfg *.conf *.txt"), ("Tous les fichiers", "*.*")],
        )
        if not target:
            return

        try:
            shutil.copy2(source, target)
            messagebox.showinfo("Configurations", f"Configuration telechargee vers:\n{target}")
        except Exception as exc:
            LOGGER.exception("Error downloading config: %s", exc)
            messagebox.showerror("Configurations", f"Impossible de telecharger la configuration: {exc}")

    def _build_context_menu(self) -> Menu:
        menu = super()._build_context_menu()
        dtype, _did, dev = self._selected_record()
        if dev is not None and dtype is not None and self.model.is_config_download_type(dtype):
            menu.insert_command(0, label="Telecharger la conf", command=self._download_config_for_selected)
            menu.insert_separator(1)
        if dev is not None and dtype is not None:
            self._append_dynamic_actions(menu, dtype, dev)

        return menu

    def _append_dynamic_actions(self, menu: Menu, dtype: str, dev) -> None:
        actions = self._mgr.list_type_actions(str(dtype))
        if not actions:
            return
        visible_actions = []
        for action in actions:
            if not action_allows_os(str(action.get("os_scope", "")), str(getattr(dev, "type", ""))):
                continue
            visible_actions.append(action)
        if not visible_actions:
            return
        menu.add_separator()
        for action in visible_actions:
            label = str(action.get("label", "")).strip() or str(action.get("action_key", "")).strip()
            target_kind = str(action.get("target_kind", "")).strip().lower()
            builtin = str(action.get("target_value", "")).strip().lower() or str(action.get("action_key", "")).strip().lower()
            state = "normal" if target_kind == "builtin" and self._can_run_builtin(dev, builtin) else "disabled"
            menu.add_command(
                label=label,
                state=state,
                command=lambda b=builtin, d=dev: self._run_builtin_action(d, b),
            )

    @staticmethod
    def _can_run_builtin(dev, builtin: str) -> bool:
        ip = str(getattr(dev, "ip", "")).strip()
        tv_id = str(getattr(dev, "id_Teamviewer", "")).strip()
        if builtin == "teamviewer":
            return bool(tv_id)
        if builtin in {"web", "ssh", "remote_desktop"}:
            return bool(ip)
        return False

    @staticmethod
    def _run_builtin_action(dev, builtin: str) -> None:
        ip = str(getattr(dev, "ip", "")).strip()
        subtype = str(getattr(dev, "type", "")).strip().lower()
        tv_id = str(getattr(dev, "id_Teamviewer", "")).strip()
        web_url = str(getattr(dev, "web_url", "")).strip()
        ssh_user = str(getattr(dev, "ssh_user", "")).strip()
        if builtin == "teamviewer":
            if tv_id:
                webbrowser.open(f"https://start.teamviewer.com/{tv_id}")
            return
        if builtin == "remote_desktop":
            subprocess.Popen(["mstsc", f"/v:{ip}"])
            return
        if builtin == "ssh":
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
        elif subtype == "dsm":
            url = f"http://{ip}:5000"
        else:
            url = f"http://{ip}"
        webbrowser.open(url)

    def _on_double_click(self, _evt=None) -> None:
        dtype, _did, dev = self._selected_record()
        if dev is None or dtype is None:
            return

        try:
            subtype = str(getattr(dev, "type", "")).strip().lower()
            ip = str(getattr(dev, "ip", "")).strip()
            tv_id = str(getattr(dev, "id_Teamviewer", "")).strip()
            action = str(getattr(dev, "action_double_click", "")).strip().lower()
            web_url = str(getattr(dev, "web_url", "")).strip()
            ssh_user = str(getattr(dev, "ssh_user", "")).strip()

            allowed_action_keys = [
                str(a.get("action_key", "")).strip().lower()
                for a in self._mgr.list_type_actions(str(dtype))
                if action_allows_os(str(a.get("os_scope", "")), subtype)
            ]
            if action and action not in allowed_action_keys:
                action = ""
            if not action:
                action = allowed_action_keys[0] if allowed_action_keys else "web"

            if action == "teamviewer":
                if tv_id:
                    webbrowser.open(f"https://start.teamviewer.com/{tv_id}")
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
            elif subtype == "dsm":
                url = f"http://{ip}:5000"
            else:
                url = f"http://{ip}"
            webbrowser.open(url)
        except Exception as exc:
            LOGGER.exception("Error opening action: %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir l'interface pour {dev.ip}")
