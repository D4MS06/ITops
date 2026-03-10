from __future__ import annotations

import logging
import shutil
import subprocess
import webbrowser
from pathlib import Path
from tkinter import Frame, Menu, filedialog, messagebox, simpledialog

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.ui.config_files_actions_mixin import ConfigFilesActionsMixin
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.dialogs.config_files_manager import ConfigFilesManagerDialog
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.utils.action_compat import action_allows_os
from monitoring.utils.config_files import find_switch_config_files, resolve_local_type_versions_dir
from monitoring.utils.file_drop import hook_dropfiles

LOGGER = logging.getLogger(__name__)


class TypeDevicesView(ConfigFilesActionsMixin, DeviceListView):
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
        self._config_storage = ConfigStorageService()
        self.device_type = str(device_type_code).strip().lower()
        self._type_label = str(type_label).strip() or self.device_type
        super().__init__(parent, model=model, controller=controller)
        self._drop_enabled = hook_dropfiles(self.tree, self._on_files_dropped)
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
        self.controller.refresh_views()

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
        self.controller.refresh_views()

    def _on_delete(self) -> None:
        did, _dev = self._selected_device()
        if not did:
            messagebox.showinfo("Supprimer", "Selectionnez un equipement.")
            return
        if messagebox.askyesno("Confirmation", "Supprimer cet equipement ?"):
            self.model.delete_device(self.device_type, did)
            self.refresh_paused = False
            self.controller.refresh_views()

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
            insert_at = 0
            insert_at = self._insert_dynamic_actions(menu, dev, at_index=insert_at)
            ip = str(getattr(dev, "ip", "")).strip()
            if self.model.is_config_download_type(self.device_type):
                matches = find_switch_config_files(
                    self._configs_root_dir(),
                    str(getattr(dev, "name", "")),
                    str(getattr(dev, "ip", "")),
                    max_results=1,
                )
                config_menu = Menu(
                    menu,
                    tearoff=0,
                    bg=self.theme.colors["menu_bg"],
                    fg=self.theme.colors["menu_fg"],
                )
                config_menu.add_command(
                    label="Telecharger",
                    command=self._download_selected_config_file,
                    state="normal" if matches else "disabled",
                )
                config_menu.add_command(
                    label="Importer un fichier de conf",
                    command=self._import_selected_config_file,
                )
                config_menu.add_command(label="Gestion des fichiers", command=self._manage_selected_config_files)
                menu.insert_cascade(insert_at, label="Fichiers de configuration", menu=config_menu)
                insert_at += 1
                menu.insert_separator(insert_at)
                insert_at += 1
            if ip:
                self._add_network_tools_submenu(menu, ip, at_index=insert_at)
                insert_at += 1
                menu.insert_separator(insert_at)
        return menu

    def _insert_dynamic_actions(self, menu: Menu, dev, *, at_index: int = 0) -> int:
        actions = self._mgr.list_type_actions(self.device_type)
        if not actions:
            return at_index
        subtype = str(getattr(dev, "type", ""))
        visible_actions = [a for a in actions if action_allows_os(str(a.get("os_scope", "")), subtype)]
        if not visible_actions:
            return at_index
        for action in reversed(visible_actions):
            label = str(action.get("label", "")).strip() or str(action.get("action_key", "")).strip()
            target_kind = str(action.get("target_kind", "")).strip().lower()
            builtin = str(action.get("target_value", "")).strip().lower() or str(action.get("action_key", "")).strip().lower()
            state = "normal" if target_kind == "builtin" and self._can_run_builtin(dev, builtin) else "disabled"
            menu.insert_command(
                at_index,
                label=label,
                state=state,
                command=lambda b=builtin, d=dev: self._run_builtin_action(d, b),
            )
        at_index += len(visible_actions)
        menu.insert_separator(at_index)
        return at_index + 1

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

    def _configs_root_dir(self) -> Path:
        return self._config_storage.backup_root_dir()

    def _local_versions_dir(self) -> Path:
        return resolve_local_type_versions_dir(device_type=self.device_type)

    def _config_record_for_menu(self):
        did, dev = self._selected_device()
        return self.device_type, did, dev, self._type_label

    def _config_record_from_drop_row(self, row_id: str):
        did = str(row_id)
        dev = self.model.device_data.get(self.device_type, {}).get(did)
        return self.device_type, did, dev, self._type_label

    def _config_local_versions_root(self, dtype: str) -> Path:
        _ = dtype
        return self._local_versions_dir().parent

    def _is_config_enabled_for_type(self, dtype: str) -> bool:
        return self.model.is_config_download_type(dtype)

    def _download_selected_config_file(self) -> None:
        self._download_config_for_record()

    def _manage_selected_config_files(self) -> None:
        self._manage_config_files_for_record()

    def _import_selected_config_file(self) -> None:
        self._import_config_file_for_record()

    def _on_files_dropped(self, paths: list[Path], pointer_x: int, pointer_y: int) -> None:
        self._import_config_drop_on_row(paths, pointer_y)
