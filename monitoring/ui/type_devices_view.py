from __future__ import annotations

import logging
from pathlib import Path
from tkinter import Frame, Menu, messagebox

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.services.device_actions_service import DeviceActionService
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.services.settings_service import SettingsService
from monitoring.ui.config_files_actions_mixin import ConfigFilesActionsMixin
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.dialogs.device_form import DeviceForm
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
        settings_service: SettingsService | None = None,
        device_actions_service: DeviceActionService | None = None,
    ) -> None:
        self._config_storage = ConfigStorageService()
        self.device_type = str(device_type_code).strip().lower()
        self._type_label = str(type_label).strip() or self.device_type
        super().__init__(
            parent,
            model=model,
            controller=controller,
            settings_service=settings_service,
            device_actions_service=device_actions_service,
        )
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
        success = self._create_device_from_form(dlg.result)
        if not success:
            messagebox.showwarning("Duplication", "IP deja utilisee.")
        self.refresh_paused = False
        self.controller.refresh_views()

    def _on_edit(self) -> None:
        did, dev = self._selected_device()
        if not did or not dev:
            messagebox.showinfo("Modifier", "Selectionnez un equipement.")
            return
        dlg = DeviceForm(
            self.parent,
            title=f"Modifier {self._type_label}",
            default_type=self.device_type,
            initial=self._build_device_form_initial(did, dev),
        )
        if dlg.result is None:
            return
        ok = self._update_device_from_form(did, dlg.result)
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
            self._run_device_action(dev)
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
        actions = self._available_action_rows_for_device(dev)
        if not actions:
            return at_index
        for action in reversed(actions):
            label = str(action.get("label", "")).strip() or str(action.get("action_key", "")).strip()
            builtin = str(action.get("target_value", "")).strip().lower() or str(action.get("action_key", "")).strip().lower()
            state = "normal" if self.device_actions_service.can_run_action(dev, builtin) else "disabled"
            menu.insert_command(
                at_index,
                label=label,
                state=state,
                command=lambda b=builtin, d=dev: self._run_device_action(d, b),
            )
        at_index += len(actions)
        menu.insert_separator(at_index)
        return at_index + 1

    def _append_dynamic_actions(self, menu: Menu, dev) -> None:
        actions = self._available_action_rows_for_device(dev)
        if not actions:
            return
        menu.add_separator()
        for action in actions:
            label = str(action.get("label", "")).strip() or str(action.get("action_key", "")).strip()
            builtin = str(action.get("target_value", "")).strip().lower() or str(action.get("action_key", "")).strip().lower()
            state = "normal" if self.device_actions_service.can_run_action(dev, builtin) else "disabled"
            menu.add_command(
                label=label,
                state=state,
                command=lambda b=builtin, d=dev: self._run_device_action(d, b),
            )

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
