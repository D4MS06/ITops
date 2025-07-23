import json
import os
import pytest

from monitoring.storage.json_manager import JSONFileManager
from monitoring.utils.exceptions import DeviceReadingError


def test_read_and_write_json(tmp_path):
    filepath = tmp_path / "data.json"
    manager = JSONFileManager(str(filepath))
    data = {"foo": [1, 2, 3]}
    manager.write_to_json_file(data)
    assert json.loads(filepath.read_text()) == data
    read = manager.read_json_file()
    assert read == data


def test_read_missing_file(tmp_path):
    manager = JSONFileManager(str(tmp_path / "missing.json"))
    with pytest.raises(DeviceReadingError):
        manager.read_json_file()


def test_read_invalid_json(tmp_path):
    filepath = tmp_path / "invalid.json"
    filepath.write_text("{ invalid }")
    manager = JSONFileManager(str(filepath))
    with pytest.raises(DeviceReadingError):
        manager.read_json_file()
