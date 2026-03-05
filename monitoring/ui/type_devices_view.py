from __future__ import annotations

import logging
import shutil
import subprocess
import webbrowser
from pathlib import Path
from tkinter import Frame, Menu, filedialog, messagebox, simpledialog

from monitoring.config.settings import load_settings
from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.utils.action_compat import action_allows_os
from monitoring.utils.config_files import find_switch_config_files, resolve_switch_configs_dir

LOGGER = logging.getLogger(__name__)


class TypeDevicesView(DeviceListView):
    columns = ("name", "ip", "desc")
    headings = {"name": "Nom", "ip": "IP", "desc": "Description"}
    tag_configs: dict[str, dict] = {}

    def __init__(
        self,
        parent: Frame,
        *,
        device_type_code: str,
        type_label: str,
        model: DevicesModel | None = None,
        controller: AppController | None = None,
    ) -> None:
        self._mgr = SQLiteFileManager()
        self.device_type = str(device_type_code).strip().lower()
        self._type_label = str(type_label).strip() or self.device_type
        super().__init__(parent, model=model, controller=controller)
        self.update_display()

    def _selected_device(self):
        sel = self.tree.selection()
        if not sel:
            return None, None
        did = str(sel[0])
        return did, self.model.device_data.get(self.device_type, {}).get(did)

    def _on_add(self) -> None:
        dlg = DeviceForm(self.parent, title=f"Ajouter {self._type_label}", default_type=self.device_type)
        if dlg.result is None:
            return
        d = dlg.result
        success = self.model.add_device(
            self.device_type,
            d["name"],
            d["ip"],
            d["desc"],
            id_Teamviewer=d.get("tv_id", ""),
            device_subtype=d.get("subtype", ""),
            action_double_click=d.get("action_double_click", ""),
            web_url=d.get("web_url", ""),
            ssh_user=d.get("ssh_user", ""),
            custom_data=d.get("custom_data", {}),
            notify=d.get("notify", True),
        )
        if not success:
            messagebox.showwarning("Duplication", "IP deja utilisee.")
        self.refresh_paused = False
        self.controller._refresh_all_views()

    def _on_edit(self) -> None:
        did, dev = self._selected_device()
        if not did or not dev:
            messagebox.showinfo("Modifier", "Selectionnez un equipement.")
            return
        initial = {
            "name": dev.name,
            "ip": dev.ip,
            "desc": dev.description,
            "subtype": getattr(dev, "type", ""),
            "tv_id": getattr(dev, "id_Teamviewer", ""),
            "action_double_click": getattr(dev, "action_double_click", ""),
            "web_url": getattr(dev, "web_url", ""),
            "ssh_user": getattr(dev, "ssh_user", ""),
            "notify": self.model.notify_flags.get(self.device_type, {}).get(did, True),
            "custom_data": self.model.extract_custom_data(dev),
        }
        dlg = DeviceForm(
            self.parent,
            title=f"Modifier {self._type_label}",
            default_type=self.device_type,
            initial=initial,
        )
        if dlg.result is None:
            return
        d = dlg.result
        ok = self.model.update_device(
            self.device_type,
            did,
            new_name=d["name"],
            new_ip=d["ip"],
            new_description=d["desc"],
            id_Teamviewer=d.get("tv_id", ""),
            device_subtype=d.get("subtype", ""),
            action_double_click=d.get("action_double_click", ""),
            web_url=d.get("web_url", ""),
            ssh_user=d.get("ssh_user", ""),
            custom_data=d.get("custom_data", {}),
            notify=d.get("notify", True),
        )
        if not ok:
            messagebox.showerror("Erreur", "Echec de la mise a jour.")
        self.refresh_paused = False
        self.controller._refresh_all_views()

    def _on_delete(self) -> None:
        did, _dev = self._selected_device()
        if not did:
            messagebox.showinfo("Supprimer", "Selectionnez un equipement.")
            return
        if messagebox.askyesno("Confirmation", "Supprimer cet equipement ?"):
            self.model.delete_device(self.device_type, did)
            self.refresh_paused = False
            self.controller._refresh_all_views()

    def _on_double_click(self, _event=None) -> None:
        _did, dev = self._selected_device()
        if not dev:
            return
        try:
            subtype = str(getattr(dev, "type", "")).strip().lower()
            action = str(getattr(dev, "action_double_click", "")).strip().lower()
            allowed = [
                str(a.get("action_key", "")).strip().lower()
                for a in self._mgr.list_type_actions(self.device_type)
                if action_allows_os(str(a.get("os_scope", "")), subtype)
            ]
            if action and action not in allowed:
                action = ""
            if not action:
                action = allowed[0] if allowed else "web"
            self._run_builtin_action(dev, action)
        except Exception as exc:
            LOGGER.exception("Erreur ouverture action device : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir l'action pour {getattr(dev, 'ip', '')}")

    def _build_context_menu(self) -> Menu:
        menu = super()._build_context_menu()
        _did, dev = self._selected_device()
        if dev:
            ip = str(getattr(dev, "ip", "")).strip()
            if ip:
                self._add_network_tools_submenu(menu, ip, at_index=0)
            if self.model.is_config_download_type(self.device_type):
                menu.insert_command(
                    1,
                    label="Telecharger la conf",
                    command=self._download_selected_config_file,
                )
                menu.insert_separator(2)
            self._append_dynamic_actions(menu, dev)
        return menu

    def _append_dynamic_actions(self, menu: Menu, dev) -> None:
        actions = self._mgr.list_type_actions(self.device_type)
        if not actions:
            return
        subtype = str(getattr(dev, "type", ""))
        visible_actions = [a for a in actions if action_allows_os(str(a.get("os_scope", "")), subtype)]
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

    def _run_builtin_action(self, dev, builtin: str) -> None:
        ip = str(getattr(dev, "ip", "")).strip()
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
            else:
                login = simpledialog.askstring("Connexion SSH", f"Login SSH pour {ip} :", parent=self.parent)
                login = str(login or "").strip()
                if not login:
                    return
                target = f"{login}@{ip}"
            if shutil.which("wt"):
                subprocess.Popen(["wt", "ssh", target])
            else:
                subprocess.Popen(["cmd", "/c", "start", "ssh", target])
            return
        webbrowser.open(web_url or f"http://{ip}")

    @staticmethod
    def _configs_root_dir() -> Path:
        settings = load_settings()
        configured = str(getattr(settings, "switch_configs_dir", "") or "").strip()
        return resolve_switch_configs_dir(configured)

    def _download_selected_config_file(self) -> None:
        did, dev = self._selected_device()
        if not did or dev is None:
            messagebox.showinfo("Configurations", "Selectionnez un equipement.")
            return
        root_dir = self._configs_root_dir()
        matches = find_switch_config_files(root_dir, str(getattr(dev, "name", "")), str(getattr(dev, "ip", "")))
        if not matches:
            messagebox.showinfo(
                "Configurations",
                f"Aucun fichier trouve pour {dev.name} ({dev.ip}).\nDossier scanne: {root_dir}",
            )
            return
        source = matches[0]
        target = filedialog.asksaveasfilename(
            parent=self.parent,
            title="Telecharger la conf",
            initialfile=source.name,
            defaultextension=source.suffix or ".cfg",
            filetypes=[("Config", "*.cfg *.conf *.txt"), ("Tous les fichiers", "*.*")],
        )
        if not target:
            return
        try:
            shutil.copy2(source, target)
            messagebox.showinfo("Configurations", f"Configuration telechargee vers:\n{target}")
        except Exception as exc:
            LOGGER.exception("Erreur telechargement configuration : %s", exc)
            messagebox.showerror("Configurations", f"Impossible de telecharger la configuration: {exc}")
