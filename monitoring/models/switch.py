# monitoring/models/switch.py
from monitoring.models.device import Device

class Switch(Device):
    def __init__(self, ip, name, description, device_id=None):
        super().__init__(ip, name, description, device_type="switch", device_id=device_id)
