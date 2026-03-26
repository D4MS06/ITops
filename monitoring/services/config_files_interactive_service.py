from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog, messagebox

from monitoring.utils.config_files import list_local_config_versions

LOGGER = logging.getLogger(__name__)


class ConfigFilesInteractiveService:
    """Shared interactive UI workflows for configuration files operations."""

    def __init__(self, config_storage) -> None:
        self._config_storage = config_storage

    def download_latest_backup_with_dialog(
        self,
        *,
        parent,
        device_name: str,
        device_ip: str,
        device_type_label: str = "",
        dialog_title: str = "Telecharger la conf",
    ) -> Path | None:
        normalized_name = str(device_name or "").strip()
        normalized_ip = str(device_ip or "").strip()
        matches = self._config_storage.find_device_backup_files(
            device_name=normalized_name,
            device_ip=normalized_ip,
            max_results=1,
        )
        source: Path | None = matches[0] if matches else None
        if source is None:
            try:
                local_rows = list_local_config_versions(
                    local_versions_root=self._config_storage.local_versions_root_dir(),
                    device_type_label=str(device_type_label or ""),
                    device_name=normalized_name,
                )
            except Exception:
                local_rows = []
            if local_rows:
                source = Path(str(local_rows[0].get("path", "") or ""))

        if source is None or not source.is_file():
            messagebox.showinfo(
                "Configurations",
                f"Aucune sauvegarde trouvee pour {normalized_name} ({normalized_ip}).\n"
                f"Dossier scanne: {self._config_storage.backup_root_dir()}",
                parent=parent,
            )
            return None

        target = filedialog.asksaveasfilename(
            parent=parent,
            title=dialog_title,
            initialfile=source.name,
            defaultextension=source.suffix or ".cfg",
            filetypes=[("Config", "*.cfg *.conf *.txt"), ("Tous les fichiers", "*.*")],
        )
        if not target:
            return None

        try:
            destination = Path(target)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            messagebox.showinfo("Configurations", f"Configuration telechargee vers:\n{destination}", parent=parent)
            return destination
        except Exception as exc:
            LOGGER.exception("Erreur telechargement configuration : %s", exc)
            messagebox.showerror("Configurations", f"Impossible de telecharger la configuration: {exc}", parent=parent)
            return None
