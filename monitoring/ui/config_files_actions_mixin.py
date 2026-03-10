from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog, messagebox

from monitoring.ui.dialogs.config_drop_confirm import ConfigDropConfirmDialog
from monitoring.ui.dialogs.config_files_manager import ConfigFilesManagerDialog

LOGGER = logging.getLogger(__name__)


class ConfigFilesActionsMixin:
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

    def _download_config_for_record(self) -> None:
        dtype, did, dev, type_label = self._config_record_for_menu()
        if dev is None or dtype is None or did is None:
            self._show_config_selection_required_message()
            return
        if not self._is_config_enabled_for_type(dtype):
            self._show_config_unsupported_message()
            return

        matches = self._config_storage.find_device_backup_files(
            device_name=str(getattr(dev, "name", "") or did),
            device_ip=str(getattr(dev, "ip", "")),
            max_results=1,
        )
        if not matches:
            messagebox.showinfo(
                "Configurations",
                f"Aucune sauvegarde trouvee pour {getattr(dev, 'name', '')} ({getattr(dev, 'ip', '')}).\n"
                f"Dossier scanne: {self._config_storage.backup_root_dir()}",
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
            self._config_storage.download_latest_device_backup(
                device_name=str(getattr(dev, "name", "") or did),
                device_ip=str(getattr(dev, "ip", "")),
                target_path=Path(target),
            )
            messagebox.showinfo("Configurations", f"Configuration telechargee vers:\n{target}")
        except Exception as exc:
            LOGGER.exception("Erreur telechargement configuration : %s", exc)
            messagebox.showerror("Configurations", f"Impossible de telecharger la configuration: {exc}")

    def _manage_config_files_for_record(self) -> None:
        dtype, did, dev, type_label = self._config_record_for_menu()
        if dev is None or dtype is None or did is None:
            self._show_config_selection_required_message()
            return
        if not self._is_config_enabled_for_type(dtype):
            self._show_config_unsupported_message()
            return
        ConfigFilesManagerDialog(
            self.parent,
            local_versions_root=self._config_local_versions_root(dtype),
            device_type_label=type_label,
            device_name=str(getattr(dev, "name", "") or did),
        )

    def _import_config_file_for_record(self) -> None:
        dtype, did, dev, type_label = self._config_record_for_menu()
        if dev is None or dtype is None or did is None:
            self._show_config_selection_required_message()
            return
        if not self._is_config_enabled_for_type(dtype):
            self._show_config_unsupported_message()
            return
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
