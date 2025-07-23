# monitoring/storage/json_manager.py
import os
import json
import threading
from monitoring.utils.logger import log_with_timestamp
from monitoring.utils.exceptions import DeviceReadingError

class JSONFileManager:
    _lock = threading.Lock()

    def __init__(self, filename: str = "devices.json"):
        base_dir = os.path.dirname(__file__)
        self.filepath = os.path.join(base_dir, filename)

    def read_json_file(self) -> dict:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                log_with_timestamp(f"Contenu lu du fichier JSON: {data}")
            return data
        except FileNotFoundError:
            raise DeviceReadingError("Le fichier de données est introuvable.")
        except json.JSONDecodeError:
            raise DeviceReadingError("Erreur lors de la lecture du fichier JSON.")

    def write_to_json_file(self, data: dict) -> None:
        with JSONFileManager._lock:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            log_with_timestamp("Écriture réussie dans le fichier JSON.")
