from __future__ import annotations

import hashlib
import json
import mimetypes
import uuid
from collections.abc import Callable
from pathlib import Path

from monitoring.models.linked_file import LinkedFile
from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.utils.app_paths import app_data_root


DEFAULT_LINKED_FILES_DIR_NAME = "linked_files"


def default_linked_files_root_dir() -> Path:
    return app_data_root() / DEFAULT_LINKED_FILES_DIR_NAME


class LinkedFileService:
    def __init__(
        self,
        manager: MariaDBFileManager | None = None,
        *,
        storage_root_provider: Callable[[], Path] | None = None,
    ) -> None:
        self._mgr = manager or MariaDBFileManager()
        self._storage_root_provider = storage_root_provider or default_linked_files_root_dir

    def storage_root_dir(self) -> Path:
        return Path(self._storage_root_provider())

    def store_bytes(
        self,
        *,
        owner_kind: str,
        owner_id: str,
        module_code: str,
        category: str,
        filename: str,
        content: bytes,
        detail: str = "",
        metadata: dict[str, str] | None = None,
        created_by: str = "",
        version_label: str = "",
    ) -> LinkedFile:
        normalized_owner_kind = _normalize_token(owner_kind, default="owner")
        normalized_owner_id = _normalize_owner_id(owner_id)
        normalized_module = _normalize_token(module_code, default="core")
        normalized_category = _normalize_token(category, default="attachment")
        clean_filename = _sanitize_filename(filename)
        file_id = uuid.uuid4().hex
        target_dir = self.storage_root_dir() / normalized_module / normalized_owner_kind / normalized_owner_id / normalized_category
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = _ensure_unique_path(target_dir / clean_filename)
        raw_content = bytes(content or b"")
        target_path.write_bytes(raw_content)
        digest = hashlib.sha256(raw_content).hexdigest()
        mime_type = mimetypes.guess_type(clean_filename)[0] or "application/octet-stream"
        row = self._mgr.upsert_linked_file(
            file_id=file_id,
            owner_kind=normalized_owner_kind,
            owner_id=normalized_owner_id,
            module_code=normalized_module,
            category=normalized_category,
            filename=target_path.name,
            stored_path=str(target_path),
            mime_type=mime_type,
            size_bytes=len(raw_content),
            sha256=digest,
            version_label=str(version_label or "").strip(),
            detail=str(detail or "").strip(),
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            sync_status="local_only",
            sync_error="",
            created_by=str(created_by or "").strip(),
        )
        return _linked_file_from_row(row)

    def list_files(
        self,
        *,
        owner_kind: str,
        owner_id: str,
        category: str = "",
        module_code: str = "",
        limit: int = 200,
    ) -> list[LinkedFile]:
        rows = self._mgr.list_linked_files(
            owner_kind=_normalize_token(owner_kind, default="owner"),
            owner_id=_normalize_owner_id(owner_id),
            category=_normalize_token(category, default="") if category else "",
            module_code=_normalize_token(module_code, default="") if module_code else "",
            limit=limit,
        )
        return [_linked_file_from_row(row) for row in rows]

    def get_file(self, file_id: str) -> LinkedFile | None:
        row = self._mgr.get_linked_file(file_id=str(file_id or "").strip())
        return _linked_file_from_row(row) if row else None

    def get_file_by_stored_path(self, stored_path: Path | str) -> LinkedFile | None:
        for candidate in self._stored_path_candidates(stored_path):
            row = self._mgr.get_linked_file_by_stored_path(stored_path=candidate)
            if row:
                return _linked_file_from_row(row)
        return None

    def list_files_under_stored_path(self, stored_path: Path | str, *, limit: int = 10000) -> list[LinkedFile]:
        rows_by_id: dict[str, LinkedFile] = {}
        for candidate in self._stored_path_candidates(stored_path):
            for separator in ("/", "\\"):
                prefix = candidate.rstrip("/\\") + separator
                rows = self._mgr.list_linked_files_by_stored_path_prefix(
                    stored_path=candidate,
                    child_path_pattern=f"{prefix}%",
                    limit=limit,
                )
                for row in rows:
                    item = _linked_file_from_row(row)
                    rows_by_id[item.id] = item
        return list(rows_by_id.values())[:limit]

    @staticmethod
    def _stored_path_candidates(stored_path: Path | str) -> list[str]:
        raw_path = str(stored_path or "").strip()
        if not raw_path:
            return []
        candidates = [raw_path]
        try:
            absolute_path = str(Path(raw_path).expanduser().absolute())
            if absolute_path not in candidates:
                candidates.append(absolute_path)
        except OSError:
            pass
        try:
            resolved_path = str(Path(raw_path).expanduser().resolve())
            if resolved_path not in candidates:
                candidates.append(resolved_path)
        except OSError:
            pass
        return candidates

    def list_files_by_module_category(
        self,
        *,
        module_code: str,
        category: str,
        limit: int = 1000,
    ) -> list[LinkedFile]:
        rows = self._mgr.list_linked_files_by_module_category(
            module_code=_normalize_token(module_code, default="core"),
            category=_normalize_token(category, default="attachment"),
            limit=limit,
        )
        return [_linked_file_from_row(row) for row in rows]

    def update_sync_state(self, file_id: str, *, sync_status: str, sync_error: str = "") -> bool:
        return bool(
            self._mgr.update_linked_file_sync_state(
                file_id=str(file_id or "").strip(),
                sync_status=str(sync_status or "local_only"),
                sync_error=str(sync_error or ""),
            )
        )

    def delete_file(self, file_id: str, *, delete_physical_file: bool = False) -> bool:
        existing = self.get_file(file_id)
        deleted = bool(self._mgr.delete_linked_file(file_id=str(file_id or "").strip()))
        if deleted and delete_physical_file and existing is not None:
            try:
                Path(existing.stored_path).unlink(missing_ok=True)
            except OSError:
                pass
        return deleted


def _linked_file_from_row(row: dict) -> LinkedFile:
    return LinkedFile(
        id=str(row.get("id") or ""),
        owner_kind=str(row.get("owner_kind") or ""),
        owner_id=str(row.get("owner_id") or ""),
        module_code=str(row.get("module_code") or ""),
        category=str(row.get("category") or ""),
        filename=str(row.get("filename") or ""),
        stored_path=str(row.get("stored_path") or ""),
        mime_type=str(row.get("mime_type") or ""),
        size_bytes=int(row.get("size_bytes") or 0),
        sha256=str(row.get("sha256") or ""),
        version_label=str(row.get("version_label") or ""),
        detail=str(row.get("detail") or ""),
        metadata=dict(row.get("metadata") or {}),
        sync_status=str(row.get("sync_status") or "local_only"),
        sync_error=str(row.get("sync_error") or ""),
        created_by=str(row.get("created_by") or ""),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


def _normalize_token(value: str, *, default: str) -> str:
    raw = str(value or "").strip().lower()
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in raw).strip("_")
    return cleaned or default


def _normalize_owner_id(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "unknown"
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in raw)
    return cleaned.strip("._-") or "unknown"


def _sanitize_filename(value: str) -> str:
    raw = Path(str(value or "attachment.bin").strip()).name
    cleaned = "".join(ch if ch.isalnum() or ch in {" ", "-", "_", "."} else "_" for ch in raw)
    cleaned = " ".join(cleaned.split()).strip(" .")
    return cleaned or "attachment.bin"


def _ensure_unique_path(path: Path) -> Path:
    target = Path(path)
    if not target.exists():
        return target
    idx = 2
    while True:
        candidate = target.with_name(f"{target.stem}_{idx}{target.suffix}")
        if not candidate.exists():
            return candidate
        idx += 1
