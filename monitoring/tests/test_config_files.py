from pathlib import Path

from monitoring.utils.config_files import find_switch_config_files


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


def test_find_switch_config_files_returns_empty_if_folder_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing-dir"
    matches = find_switch_config_files(missing, "SW1", "10.0.0.1")
    assert matches == []
