# monitoring/models/server.py
from monitoring.models.device import Device


class Server(Device):
    def __init__(
        self,
        ip,
        name,
        description,
        id_Teamviewer: str,
        subtype: str,
        action_double_click: str = "",
        web_url: str = "",
        ssh_user: str = "",
        device_id=None,
    ):
        super().__init__(ip, name, description, device_type="server", device_id=device_id)
        self.id_Teamviewer = id_Teamviewer
        self.type = subtype
        self.action_double_click = action_double_click
        self.web_url = web_url
        self.ssh_user = ssh_user
