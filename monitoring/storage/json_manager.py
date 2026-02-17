import json
import os
import shutil
import sys
import threading

from monitoring.utils.exceptions import DeviceReadingError
from monitoring.utils.logger import log_with_timestamp


class JSONFileManager:
    _lock = threading.Lock()

    def __init__(self, filename: str = "devices.json"):
        self.filename = filename
        local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        self.data_dir = os.path.join(local_app_data, "NetworkMonitoringProject", "data")
        self.filepath = os.path.join(self.data_dir, filename)
        self.seed_path = self._resolve_seed_path(filename)

    @staticmethod
    def _resolve_seed_path(filename: str) -> str | None:
        candidates = [os.path.join(os.path.dirname(__file__), filename)]
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "monitoring", "storage", filename))

        for path in candidates:
            if path and os.path.isfile(path):
                return path
        return None

    def _ensure_data_file(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        if os.path.isfile(self.filepath):
            return

        if self.seed_path and os.path.isfile(self.seed_path):
            shutil.copy2(self.seed_path, self.filepath)
            return

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump({"switch": [], "server": []}, f, indent=2)

    def read_json_file(self) -> dict:
        try:
            with JSONFileManager._lock:
                self._ensure_data_file()
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    log_with_timestamp(f"Contenu lu du fichier JSON: {data}")
                return data
        except FileNotFoundError:
            raise DeviceReadingError("Le fichier de donnees est introuvable.")
        except json.JSONDecodeError:
            raise DeviceReadingError("Erreur lors de la lecture du fichier JSON.")

    def write_to_json_file(self, data: dict) -> None:
        with JSONFileManager._lock:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            log_with_timestamp("Ecriture reussie dans le fichier JSON.")
