from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LinkedFile:
    id: str
    owner_kind: str
    owner_id: str
    module_code: str
    category: str
    filename: str
    stored_path: str
    mime_type: str = ""
    size_bytes: int = 0
    sha256: str = ""
    version_label: str = ""
    detail: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    sync_status: str = "local_only"
    sync_error: str = ""
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
