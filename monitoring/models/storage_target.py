from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageTarget:
    id: str
    label: str
    service_code: str
    service_label: str
    kind: str = "smb3"
    remote_path: str = ""
    username: str = ""
    secret_ref: str = ""
    local_mount_path: str = ""
    auto_mount_enabled: bool = True
    status: str = "configured"
    last_error: str = ""
    last_checked_at: str = ""
    created_at: str = ""
    updated_at: str = ""
