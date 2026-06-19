from __future__ import annotations

import json
from pathlib import Path

from monitoring.services.linked_file_service import LinkedFileService


class _FakeLinkedFileManager:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def upsert_linked_file(self, **kwargs) -> dict:
        try:
            metadata = json.loads(str(kwargs.get("metadata_json") or "{}"))
        except Exception:
            metadata = {}
        row = {
            "id": kwargs["file_id"],
            "owner_kind": kwargs["owner_kind"],
            "owner_id": kwargs["owner_id"],
            "module_code": kwargs["module_code"],
            "category": kwargs["category"],
            "filename": kwargs["filename"],
            "stored_path": kwargs["stored_path"],
            "mime_type": kwargs["mime_type"],
            "size_bytes": kwargs["size_bytes"],
            "sha256": kwargs["sha256"],
            "version_label": kwargs["version_label"],
            "detail": kwargs["detail"],
            "metadata": metadata if isinstance(metadata, dict) else {},
            "sync_status": kwargs["sync_status"],
            "sync_error": kwargs["sync_error"],
            "created_by": kwargs["created_by"],
            "created_at": "2026-06-17 10:00:00",
            "updated_at": "2026-06-17 10:00:00",
        }
        self.rows[row["id"]] = row
        return row

    def list_linked_files(self, *, owner_kind, owner_id, category="", module_code="", limit=200):
        rows = [
            row
            for row in self.rows.values()
            if row["owner_kind"] == owner_kind
            and row["owner_id"] == owner_id
            and (not category or row["category"] == category)
            and (not module_code or row["module_code"] == module_code)
        ]
        return rows[:limit]

    def list_linked_files_by_module_category(self, *, module_code, category, limit=1000):
        rows = [
            row
            for row in self.rows.values()
            if row["module_code"] == module_code and row["category"] == category
        ]
        return rows[:limit]

    def get_linked_file(self, *, file_id):
        return self.rows.get(file_id)

    def get_linked_file_by_stored_path(self, *, stored_path):
        for row in self.rows.values():
            if row["stored_path"] == stored_path:
                return row
        return None

    def list_linked_files_by_stored_path_prefix(self, *, stored_path, child_path_pattern, limit=10000):
        child_prefix = str(child_path_pattern).removesuffix("%")
        rows = [
            row
            for row in self.rows.values()
            if row["stored_path"] == stored_path or row["stored_path"].startswith(child_prefix)
        ]
        return rows[:limit]

    def update_linked_file_sync_state(self, *, file_id, sync_status, sync_error=""):
        row = self.rows.get(file_id)
        if row is None:
            return 0
        row["sync_status"] = sync_status
        row["sync_error"] = sync_error
        return 1

    def delete_linked_file(self, *, file_id):
        return 1 if self.rows.pop(file_id, None) is not None else 0


def test_linked_file_service_stores_bytes_under_owner_scope(tmp_path: Path):
    manager = _FakeLinkedFileManager()
    service = LinkedFileService(manager, storage_root_provider=lambda: tmp_path)

    item = service.store_bytes(
        owner_kind="Device",
        owner_id="SW/CORE 01",
        module_code="Monitoring",
        category="Config",
        filename="../startup config.cfg",
        content=b"hostname SW-CORE-01\n",
        detail="Import initial",
        metadata={"source": "manual_import"},
        created_by="sa",
        version_label="startup",
    )

    assert item.owner_kind == "device"
    assert item.owner_id == "SW_CORE_01"
    assert item.module_code == "monitoring"
    assert item.category == "config"
    assert item.filename == "startup config.cfg"
    assert item.size_bytes == len(b"hostname SW-CORE-01\n")
    assert item.sha256
    assert Path(item.stored_path).read_bytes() == b"hostname SW-CORE-01\n"
    assert Path(item.stored_path).is_relative_to(tmp_path)

    rows = service.list_files(owner_kind="device", owner_id="SW_CORE_01", category="config")
    assert rows == [item]


def test_linked_file_service_can_delete_physical_file(tmp_path: Path):
    manager = _FakeLinkedFileManager()
    service = LinkedFileService(manager, storage_root_provider=lambda: tmp_path)
    item = service.store_bytes(
        owner_kind="device",
        owner_id="sw1",
        module_code="monitoring",
        category="config",
        filename="running.cfg",
        content=b"config",
    )

    assert Path(item.stored_path).is_file()
    assert service.delete_file(item.id, delete_physical_file=True) is True
    assert not Path(item.stored_path).exists()


def test_linked_file_service_can_find_and_delete_row_after_external_file_delete(tmp_path: Path):
    manager = _FakeLinkedFileManager()
    service = LinkedFileService(manager, storage_root_provider=lambda: tmp_path)
    item = service.store_bytes(
        owner_kind="device",
        owner_id="sw1",
        module_code="monitoring",
        category="config",
        filename="running.cfg",
        content=b"config",
    )
    Path(item.stored_path).unlink()

    linked = service.get_file_by_stored_path(Path(item.stored_path))

    assert linked == item
    assert service.delete_file(linked.id, delete_physical_file=False) is True
    assert service.get_file(item.id) is None


def test_linked_file_service_lists_rows_under_storage_folder(tmp_path: Path):
    manager = _FakeLinkedFileManager()
    service = LinkedFileService(manager, storage_root_provider=lambda: tmp_path)
    item_a = service.store_bytes(
        owner_kind="device",
        owner_id="sw1",
        module_code="monitoring",
        category="config",
        filename="running.cfg",
        content=b"config-a",
    )
    item_b = service.store_bytes(
        owner_kind="device",
        owner_id="sw1",
        module_code="monitoring",
        category="config",
        filename="startup.cfg",
        content=b"config-b",
    )
    folder = Path(item_a.stored_path).parent

    rows = service.list_files_under_stored_path(folder)

    assert {row.id for row in rows} == {item_a.id, item_b.id}
