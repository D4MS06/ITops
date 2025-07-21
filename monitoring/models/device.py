# monitoring/models/device.py
import uuid
from ..utils.logger import log_with_timestamp

class DeviceReadingError(Exception):
    pass

class Device:
    def __init__(self, ip: str, name: str, description: str,
                 device_type: str = "unknown", device_id: str = None):
        self.id = device_id or str(uuid.uuid4())
        self.ip = ip
        self.name = name
        self.description = description
        self.device_type = device_type
        self.status = "idle"
        self.is_monitoring = False
        self.treeview_item = None

    def __str__(self):
        return f"Device(name={self.name}, ip={self.ip}, type={self.device_type})"
