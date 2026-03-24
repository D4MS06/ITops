from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

from monitoring.services.config_files_interactive_service import ConfigFilesInteractiveService
from monitoring.ui.dialogs.config_drop_confirm import ConfigDropConfirmDialog
from monitoring.ui.dialogs.config_files_manager import ConfigFilesManagerDialog


class ConfigFilesActionsMixin:
    def _config_files_interactive(self) -> ConfigFilesInteractiveService:
        service = getattr(self, "_config_files_ui_service", None)
        if service is None:
            service = ConfigFilesInteractiveService(self._config_storage)
            setattr(self, "_config_files_ui_service", service)
        return service

    def _config_record_for_menu(self):
        raise NotImplementedError

    def _config_record_from_drop_row(self, row_id: str):
        raise NotImplementedError

    def _config_local_versions_root(self, dtype: str) -> Path:
        raise NotImplementedError

    def _is_config_enabled_for_type(self, dtype: str) -> bool:
        raise NotImplementedError

    def _show_config_unsupported_message(self) -> None:
        messagebox.showinfo("Configurations", "Le type selectionne ne supporte pas la gestion de conf.")

    def _show_config_selection_required_message(self) -> None:
        messagebox.showinfo("Configurations", "Selectionnez un equipement.")

    def _resolve_config_record_or_notify(self):
        dtype, did, dev, type_label = self._config_record_for_menu()
        if dev is None or dtype is None or did is None:
            self._show_config_selection_required_message()
            return None
        if not self._is_config_enabled_for_type(dtype):
            self._show_config_unsupported_message()
            return None
        return dtype, did, dev, type_label

    def _download_config_for_record(self) -> None:
        resolved = self._resolve_config_record_or_notify()
        if resolved is None:
            return
        _dtype, did, dev, _type_label = resolved
        self._config_files_interactive().download_latest_backup_with_dialog(
            parent=self.parent,
            device_name=str(getattr(dev, "name", "") or did),
            device_ip=str(getattr(dev, "ip", "")),
            dialog_title="Telecharger la conf",
        )

    def _manage_config_files_for_record(self) -> None:
        resolved = self._resolve_config_record_or_notify()
        if resolved is None:
            return
        dtype, did, dev, type_label = resolved
        ConfigFilesManagerDialog(
            self.parent,
            local_versions_root=self._config_local_versions_root(dtype),
            device_type_label=type_label,
            device_name=str(getattr(dev, "name", "") or did),
        )

    def _import_config_file_for_record(self) -> None:
        resolved = self._resolve_config_record_or_notify()
        if resolved is None:
            return
        _dtype, did, dev, type_label = resolved
        source = filedialog.askopenfilename(
            parent=self.parent,
            title="Importer un fichier de configuration",
            filetypes=[("Config", "*.cfg *.conf *.txt"), ("Tous les fichiers", "*.*")],
        )
        if not source:
            return
        src_path = Path(source)
        try:
            target = self._config_storage.import_device_config_version(
                device_type_label=type_label,
                device_name=str(getattr(dev, "name", "") or did),
                source_file=src_path,
                stamp_dt=self._config_storage.file_created_at(src_path),
            )
            messagebox.showinfo("Configurations", f"Version importee:\n{target}")
        except Exception as exc:
            messagebox.showerror("Configurations", f"Impossible d'importer le fichier: {exc}")

    def _import_config_drop_on_row(self, paths: list[Path], pointer_y: int) -> None:
        local_y = int(pointer_y - self.tree.winfo_rooty())
        row_id = str(self.tree.identify_row(local_y))
        if not row_id:
            return
        self.tree.selection_set(row_id)
        self.tree.focus(row_id)
        dtype, did, dev, type_label = self._config_record_from_drop_row(row_id)
        if dev is None or dtype is None or did is None:
            return
        if not self._is_config_enabled_for_type(dtype):
            return

        source = Path(paths[0])
        try:
            created = self._config_storage.file_created_at(source)
            target_name = self._config_storage.build_import_target_name(
                device_type_label=type_label,
                device_name=str(getattr(dev, "name", "") or did),
                source_file=source,
                stamp_dt=created,
            )
        except Exception:
            return

        dlg = ConfigDropConfirmDialog(
            self.parent,
            device_label=f"{type_label} / {getattr(dev, 'name', did)}",
            source_name=source.name,
            target_name=target_name,
            source_date_label=created.strftime("%Y-%m-%d %H:%M:%S"),
        )
        if not dlg.result:
            return
        try:
            target = self._config_storage.import_device_config_version(
                device_type_label=type_label,
                device_name=str(getattr(dev, "name", "") or did),
                source_file=source,
                detail=str(dlg.result.detail or ""),
                stamp_dt=created,
            )
            messagebox.showinfo("Fichiers de configuration", f"Fichier importe:\n{target}", parent=self.parent)
        except Exception as exc:
            messagebox.showerror("Fichiers de configuration", f"Import impossible: {exc}", parent=self.parent)
