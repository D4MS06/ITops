from __future__ import annotations

import shutil
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

from monitoring.ui.dialogs.config_storage_settings import ConfigStorageSettingsDialog
from monitoring.utils.config_files import find_switch_config_files, open_path_with_default_app


class DashboardConfigSyncMixin:
    """Configuration backup and sync actions for the dashboard."""

    def _switch_configs_root_dir(self) -> Path:
        return self.config_storage.backup_root_dir()

    def _open_switch_configs_root(self) -> None:
        root_dir = self._switch_configs_root_dir()
        if str(getattr(self.notification_settings, "config_storage_mode", "local") or "local").strip().lower() != "smb3":
            root_dir.mkdir(parents=True, exist_ok=True)
        try:
            open_path_with_default_app(root_dir)
        except Exception as exc:
            messagebox.showerror("Fichiers de configuration", f"Impossible d'ouvrir le dossier de sauvegarde: {exc}")

    def _open_config_storage_settings_dialog(self) -> None:
        dlg = ConfigStorageSettingsDialog(self.root, self.notification_settings)
        if not dlg.result:
            return
        self.notification_settings = dlg.result
        self._save_settings()

    def _run_config_sync_now_interactive(self) -> None:
        self._run_config_sync_now(manual_feedback=True)

    def _run_config_sync_now(self, *, manual_feedback: bool) -> None:
        def worker() -> None:
            ok, info = self.config_storage.ensure_backup_connection()
            if not ok:
                if manual_feedback:
                    self.root.after(0, lambda: messagebox.showerror("Sauvegarde", f"Connexion dossier de sauvegarde impossible: {info}"))
                return
            stats = self.config_storage.sync_local_versions_to_backup()
            total_scanned = int(stats.scanned)
            total_copied = int(stats.copied)
            if manual_feedback:
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Sauvegarde",
                        f"Termine.\nVersions locales analysees: {total_scanned}\nFichiers sauvegardes: {total_copied}",
                    ),
                )

        threading.Thread(target=worker, daemon=True, name="ConfigSyncNow").start()

    def _schedule_config_auto_sync(self) -> None:
        enabled = bool(getattr(self.notification_settings, "config_auto_sync_enabled", False))
        interval = max(
            5,
            int(getattr(self.notification_settings, "config_auto_sync_interval_seconds", 3600) or 3600),
        )
        if enabled:
            self._run_config_sync_now(manual_feedback=False)
        self.root.after(interval * 1000, self._schedule_config_auto_sync)

    def _get_selected_config_device_record(self):
        if bool(getattr(self.global_detail_frame, "winfo_manager", lambda: "")()):
            sel = tuple(self.consolidated_app.tree.selection())
            if sel:
                iid = str(sel[0])
                if "::" in iid:
                    dtype, did = iid.split("::", 1)
                    dev = self.model.device_data.get(dtype, {}).get(did)
                    if dev is not None and self.model.is_config_download_type(dtype):
                        return dtype, did, dev

        for dtype in self._ordered_type_codes():
            frame = self.type_detail_frames.get(dtype)
            view = self.type_views.get(dtype)
            if frame is None or view is None:
                continue
            if not bool(getattr(frame, "winfo_manager", lambda: "")()):
                continue
            sel = tuple(view.tree.selection())
            if not sel:
                continue
            did = str(sel[0])
            dev = self.model.device_data.get(dtype, {}).get(did)
            if dev is not None and self.model.is_config_download_type(dtype):
                return dtype, did, dev
        return None, None, None

    def _download_selected_device_config(self) -> None:
        _dtype, _did, dev = self._get_selected_config_device_record()
        if dev is None:
            messagebox.showinfo(
                "Configurations",
                "Selectionnez un equipement compatible configuration dans une vue de type ou en vue globale.",
            )
            return
        root_dir = self._switch_configs_root_dir()
        matches = find_switch_config_files(root_dir, str(getattr(dev, "name", "")), str(getattr(dev, "ip", "")))
        if not matches:
            messagebox.showinfo(
                "Configurations",
                f"Aucune sauvegarde trouvee pour {dev.name} ({dev.ip}).\nDossier scanne: {root_dir}",
            )
            return
        source = matches[0]
        target = filedialog.asksaveasfilename(
            parent=self.root,
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
            messagebox.showerror("Configurations", f"Impossible de telecharger la configuration: {exc}")
