from __future__ import annotations

import os
from pathlib import Path


def app_data_root() -> Path:
    override = str(os.environ.get("NMP_DATA_DIR") or "").strip()
    if override:
        return Path(override).expanduser()
    if os.name != "nt":
        return Path("/var/lib/itops")
    return Path(os.environ.get("LOCALAPPDATA") or str(Path.home())) / "NetworkMonitoringProject"
