from __future__ import annotations

import ipaddress
import logging
from pathlib import Path
from tkinter import Frame, IntVar, Menu, messagebox
from typing import Any, Tuple

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.services.device_actions_service import DeviceActionService
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.services.settings_service import SettingsService
from monitoring.ui.config_files_actions_mixin import ConfigFilesActionsMixin
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.view_mixins import ContextMenuMixin
from monitoring.utils.config_files import find_switch_config_files, resolve_local_type_versions_dir
from monitoring.utils.file_drop import hook_dropfiles

LOGGER = logging.getLogger(__name__)


class ConsolidatedView(ConfigFilesActionsMixin, DeviceListView, ContextMenuMixin):
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

    @staticmethod
    def _log_view_debug(message: str, exc: Exception) -> None:
        LOGGER.debug("%s: %s", message, exc)

    def __init__(
        self,
        parent: Frame,
        *,
        model: DevicesModel | None = None,
        controller: AppController | None = None,
        settings_service: SettingsService | None = None,
        device_actions_service: DeviceActionService | None = None,
    ) -> None:
        self.total_devices = IntVar(value=0)
        self.online_devices = IntVar(value=0)
        self.offline_devices = IntVar(value=0)
        self._config_storage = ConfigStorageService()

        super().__init__(
            parent,
            model=model,
            controller=controller,
            settings_service=settings_service,
            device_actions_service=device_actions_service,
        )

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
        self._drop_enabled = hook_dropfiles(self.tree, self._on_files_dropped)

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
            self._safe_clear_view_selection(view)

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
            ok = bool(
                self.model.add_device(
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
            )
            if not ok:
                messagebox.showwarning("Duplication", "IP deja utilisee.")
        except Exception:
            LOGGER.exception("Error adding device")
        finally:
            self.refresh_paused = False
            self.controller.refresh_views()

    def _on_edit(self) -> None:
        dtype, did, dev = self._selected_record()
        if dev is None or dtype is None or did is None:
            messagebox.showinfo("Modifier", "Selectionnez un device.")
            return

        initial = self._build_device_form_initial(did, dev)
        initial["kind"] = dtype

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
            self.controller.refresh_views()

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
                self.controller.refresh_views()

    def update_display(self) -> None:
        if not hasattr(self, "tree"):
            return
        try:
            if not bool(self.winfo_exists()) or not bool(self.tree.winfo_exists()):
                self.controller.unregister_view(self)
                return
        except Exception as exc:
            self._log_view_debug("Consolidated view existence check failed", exc)
            return

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
                else:
                    self.tree.reattach(iid, "", "end")
                    if self._row_state.get(iid) != state_sig:
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
                    except Exception as exc:
                        self._log_view_debug(f"Consolidated tree row move failed for iid={iid}", exc)

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
    def _local_versions_dir(dtype: str) -> Path:
        return resolve_local_type_versions_dir(device_type=dtype)

    def _switch_configs_root_dir(self, _dtype: str) -> Path:
        return self._config_storage.backup_root_dir()

    def _config_record_for_menu(self):
        dtype, did, dev = self._selected_record()
        type_label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype)) if dtype else ""
        return dtype, did, dev, type_label

    def _config_record_from_drop_row(self, row_id: str):
        dtype, did = self._parse_iid(str(row_id))
        if not dtype or not did:
            return None, None, None, ""
        dev = self.model.device_data.get(dtype, {}).get(did)
        type_label = str(self.model.type_definitions.get(dtype, {}).get("label", dtype))
        return dtype, did, dev, type_label

    def _config_local_versions_root(self, dtype: str) -> Path:
        return self._local_versions_dir(dtype).parent

    def _is_config_enabled_for_type(self, dtype: str) -> bool:
        return self.model.is_config_download_type(dtype)

    def _download_config_for_selected(self) -> None:
        super()._download_config_for_record()

    def _build_context_menu(self) -> Menu:
        menu = super()._build_context_menu()
        dtype, _did, dev = self._selected_record()
        if dev is not None and dtype is not None:
            insert_at = 0
            insert_at = self._insert_dynamic_actions(menu, dtype, dev, at_index=insert_at)
            if self.model.is_config_download_type(dtype):
                matches = find_switch_config_files(
                    self._switch_configs_root_dir(dtype),
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
                    command=self._download_config_for_selected,
                    state="normal" if matches else "disabled",
                )
                config_menu.add_command(
                    label="Importer un fichier de conf",
                    command=self._import_config_file_for_selected,
                )
                config_menu.add_command(label="Gestion des fichiers", command=self._manage_config_files_for_selected)
                menu.insert_cascade(insert_at, label="Fichiers de configuration", menu=config_menu)
                insert_at += 1
                menu.insert_separator(insert_at)
                insert_at += 1
            ip = str(getattr(dev, "ip", "")).strip()
            if ip:
                self._add_network_tools_submenu(menu, ip, at_index=insert_at)
                insert_at += 1
                menu.insert_separator(insert_at)

        return menu

    def _manage_config_files_for_selected(self) -> None:
        self._manage_config_files_for_record()

    def _import_config_file_for_selected(self) -> None:
        self._import_config_file_for_record()

    def _on_files_dropped(self, paths: list[Path], pointer_x: int, pointer_y: int) -> None:
        self._import_config_drop_on_row(paths, pointer_y)

    def _insert_dynamic_actions(self, menu: Menu, dtype: str, dev, *, at_index: int = 0) -> int:
        actions = [
            action
            for action in self.model.manager.list_type_actions(str(dtype))
            if str(action.get("action_key", "")).strip().lower()
            in set(
                self.device_actions_service.available_actions(
                    action_rows=self.model.manager.list_type_actions(str(dtype)),
                    subtype=str(getattr(dev, "type", "")),
                )
            )
        ]
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
                command=lambda b=builtin, d=dev: self.device_actions_service.run_action(device=d, action_key=b),
            )
        at_index += len(actions)
        menu.insert_separator(at_index)
        return at_index + 1

    def _append_dynamic_actions(self, menu: Menu, dtype: str, dev) -> None:
        actions = [
            action
            for action in self.model.manager.list_type_actions(str(dtype))
            if str(action.get("action_key", "")).strip().lower()
            in set(
                self.device_actions_service.available_actions(
                    action_rows=self.model.manager.list_type_actions(str(dtype)),
                    subtype=str(getattr(dev, "type", "")),
                )
            )
        ]
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
                command=lambda b=builtin, d=dev: self.device_actions_service.run_action(device=d, action_key=b),
            )

    def _on_double_click(self, _evt=None) -> None:
        dtype, _did, dev = self._selected_record()
        if dev is None or dtype is None:
            return

        try:
            action_rows = self.model.manager.list_type_actions(str(dtype))
            action = self.device_actions_service.resolve_action(
                device_type=str(dtype),
                device=dev,
                configured_action=str(getattr(dev, "action_double_click", "")),
                action_rows=action_rows,
            )
            self.device_actions_service.run_action(device=dev, action_key=action)
        except Exception as exc:
            LOGGER.exception("Error opening action: %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir l'interface pour {dev.ip}")
