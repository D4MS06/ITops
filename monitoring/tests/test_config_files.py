from pathlib import Path
from unittest.mock import patch

from monitoring.config.settings import NotificationSettings
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.utils.config_files import (
    build_device_config_filename,
    delete_local_config_version,
    ensure_smb3_connection,
    find_switch_config_files,
    list_local_config_versions,
    rename_local_config_version,
    resolve_active_config_source_dir,
    resolve_local_device_versions_dir,
    sync_local_versions_to_backup,
    store_imported_config_version,
    sync_latest_config_versions_for_type,
)


def test_find_switch_config_files_prefers_ip_and_recent_file(tmp_path: Path) -> None:
    root = tmp_path / "configs"
    root.mkdir()

    older = root / "SW-CORE-10.0.0.10-old.cfg"
    older.write_text("old")
    newest = root / "SW-CORE-10.0.0.10-latest.cfg"
    newest.write_text("new")

    matches = find_switch_config_files(root, "SW-CORE", "10.0.0.10")
    assert matches
    assert matches[0] == newest


def test_find_switch_config_files_ignores_name_only_when_ip_provided(tmp_path: Path) -> None:
    root = tmp_path / "configs"
    root.mkdir()
    wrong_ip = root / "SW-CORE-10.0.0.20.cfg"
    wrong_ip.write_text("cfg")
    matches = find_switch_config_files(root, "SW-CORE", "10.0.0.10")
    assert matches == []


def test_find_switch_config_files_returns_empty_if_folder_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing-dir"
    matches = find_switch_config_files(missing, "SW1", "10.0.0.1")
    assert matches == []


def test_find_switch_config_files_returns_empty_on_network_oserror(tmp_path: Path) -> None:
    root = tmp_path / "smb-share"
    with patch.object(Path, "is_dir", side_effect=OSError("network down")):
        matches = find_switch_config_files(root, "SW1", "10.0.0.1")
    assert matches == []


def test_resolve_active_config_source_dir_prefers_smb_when_enabled() -> None:
    local = str(Path("C:/configs/local"))
    smb = r"\\srv\configs"
    settings = NotificationSettings(
        switch_configs_dir=local,
        config_storage_mode="smb3",
        config_smb_unc_path=smb,
    )
    resolved = str(resolve_active_config_source_dir(settings)).rstrip("\\/")
    assert resolved == smb


def test_ensure_smb3_connection_accepts_existing_access_despite_1219() -> None:
    settings = NotificationSettings(
        config_storage_mode="smb3",
        config_smb_unc_path=r"\\srv\share\folder",
        config_smb_username="user",
        config_smb_password="pwd",
    )

    class _Proc:
        returncode = 2
        stderr = "System error 1219 has occurred."
        stdout = ""

    with patch("monitoring.utils.config_files.os.name", "nt"), patch(
        "monitoring.utils.config_files.subprocess.run",
        return_value=_Proc(),
    ), patch("monitoring.utils.config_files.Path.is_dir", return_value=True):
        ok, info = ensure_smb3_connection(settings)

    assert ok is True
    assert info == "ok_existing"


def test_sync_latest_config_versions_for_type_is_incremental(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    file1 = source / "SW-1-10.0.0.1.cfg"
    file1.write_text("v1")
    local_root = tmp_path / "versions"
    devices = [{"id": "dev1", "name": "SW-1", "ip": "10.0.0.1"}]

    stats1 = sync_latest_config_versions_for_type(
        source_root=source,
        local_versions_root=local_root,
        device_type="switch",
        device_type_label="Switch",
        devices=devices,
    )
    assert stats1["copied"] >= 1
    type_dir = local_root / "Switch"
    device_dir = type_dir / "SW-1"
    assert device_dir.is_dir()
    copied_files = list(device_dir.glob("SW-1-10.0.0.1_*.cfg"))
    assert copied_files

    stats2 = sync_latest_config_versions_for_type(
        source_root=source,
        local_versions_root=local_root,
        device_type="switch",
        device_type_label="Switch",
        devices=devices,
    )
    assert stats2["copied"] == 0


def test_store_imported_config_version_uses_type_and_device_folders(tmp_path: Path) -> None:
    src = tmp_path / "running.conf"
    src.write_text("content")
    root = tmp_path / "versions"
    target = store_imported_config_version(
        local_versions_root=root,
        device_type_label="Firewall",
        device_name="FW-EDGE-1",
        source_file=src,
    )
    assert target.is_file()
    assert target.parent.name == "FW-EDGE-1"
    assert target.parent.parent.name == "Firewall"
    assert target.name.startswith("Firewall_FW-EDGE-1_")


def test_list_and_delete_local_config_versions_with_detail(tmp_path: Path) -> None:
    src = tmp_path / "backup.cfg"
    src.write_text("cfg")
    root = tmp_path / "versions"
    stored = store_imported_config_version(
        local_versions_root=root,
        device_type_label="Switch",
        device_name="SW-01",
        source_file=src,
        detail="avant maj firmware",
    )
    rows = list_local_config_versions(
        local_versions_root=root,
        device_type_label="Switch",
        device_name="SW-01",
    )
    assert rows
    assert rows[0]["name"] == stored.name
    assert rows[0]["detail"] == "avant maj firmware"
    deleted = delete_local_config_version(
        local_versions_root=root,
        device_type_label="Switch",
        device_name="SW-01",
        filename=stored.name,
    )
    assert deleted is True
    rows_after = list_local_config_versions(
        local_versions_root=root,
        device_type_label="Switch",
        device_name="SW-01",
    )
    assert rows_after == []


def test_build_device_config_filename_readable_timestamp() -> None:
    src = Path(__file__)
    name = build_device_config_filename(
        device_type_label="Switch",
        device_name="APIC",
        source_file=src,
    )
    assert "Switch_APIC_" in name
    # Expected format: YYYY-MM-DD_HH-mm-ss
    parts = name.rsplit(".", 1)[0].split("_")
    assert len(parts) >= 4
    assert "-" in parts[2]
    assert "-" in parts[3]


def test_sync_local_versions_to_backup_copies_tree_incrementally(tmp_path: Path) -> None:
    local_root = tmp_path / "local_versions"
    backup_root = tmp_path / "backup"
    src = tmp_path / "running.cfg"
    src.write_text("v1")

    stored = store_imported_config_version(
        local_versions_root=local_root,
        device_type_label="Switch",
        device_name="SW-01",
        source_file=src,
        detail="pre-check",
    )

    stats1 = sync_local_versions_to_backup(
        local_versions_root=local_root,
        backup_root=backup_root,
    )
    assert stats1 == {"scanned": 1, "copied": 1}
    copied = backup_root / "Switch" / "SW-01" / stored.name
    assert copied.is_file()
    assert copied.read_text() == "v1"

    stats2 = sync_local_versions_to_backup(
        local_versions_root=local_root,
        backup_root=backup_root,
    )
    assert stats2 == {"scanned": 1, "copied": 0}


def test_rename_local_config_version_preserves_detail(tmp_path: Path) -> None:
    src = tmp_path / "running.cfg"
    src.write_text("cfg")
    root = tmp_path / "versions"
    stored = store_imported_config_version(
        local_versions_root=root,
        device_type_label="Switch",
        device_name="SW-01",
        source_file=src,
        detail="avant changement",
    )

    renamed = rename_local_config_version(
        local_versions_root=root,
        device_type_label="Switch",
        device_name="SW-01",
        filename=stored.name,
        new_filename="Switch_SW-01_2026-03-10_08-00-00.cfg",
    )

    assert renamed is not None
    assert renamed.name == "Switch_SW-01_2026-03-10_08-00-00.cfg"
    rows = list_local_config_versions(
        local_versions_root=root,
        device_type_label="Switch",
        device_name="SW-01",
    )
    assert rows[0]["name"] == renamed.name
    assert rows[0]["detail"] == "avant changement"


def test_resolve_local_device_versions_dir_returns_expected_path(tmp_path: Path) -> None:
    resolved = resolve_local_device_versions_dir(
        local_versions_root=tmp_path / "versions",
        device_type_label="Switch",
        device_name="SW-01",
    )
    assert resolved == tmp_path / "versions" / "Switch" / "SW-01"


def test_config_storage_service_prefers_smb_backup_dir() -> None:
    settings = NotificationSettings(
        switch_configs_dir="C:/configs/local",
        config_storage_mode="smb3",
        config_smb_unc_path=r"\\srv\share\configs",
    )
    svc = ConfigStorageService(settings_provider=lambda: settings)
    assert str(svc.backup_root_dir()).rstrip("\\/") == r"\\srv\share\configs"


def test_config_storage_service_downloads_latest_backup(tmp_path: Path) -> None:
    backup_root = tmp_path / "backup"
    backup_root.mkdir()
    latest = backup_root / "SW-1-10.0.0.1.cfg"
    latest.write_text("cfg")
    settings = NotificationSettings(
        switch_configs_dir=str(backup_root),
        config_storage_mode="local",
    )
    svc = ConfigStorageService(settings_provider=lambda: settings)
    target = tmp_path / "downloads" / latest.name
    copied = svc.download_latest_device_backup(
        device_name="SW-1",
        device_ip="10.0.0.1",
        target_path=target,
    )
    assert copied == target
    assert target.read_text() == "cfg"
