import json
import threading
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


def test_thread_safety(tmp_path):
    filepath = tmp_path / "thread.json"
    manager = JSONFileManager(str(filepath))

    initial_data = {"a": 1}
    manager.write_to_json_file(initial_data)

    new_data = {"b": 2}
    read_result = {}
    errors = []

    def writer():
        try:
            manager.write_to_json_file(new_data)
        except Exception as exc:  # pragma: no cover - should not happen
            errors.append(exc)

    def reader():
        try:
            read_result["data"] = manager.read_json_file()
        except Exception as exc:  # pragma: no cover - should not happen
            errors.append(exc)

    t_write = threading.Thread(target=writer)
    t_read = threading.Thread(target=reader)
    t_write.start()
    t_read.start()
    t_write.join()
    t_read.join()

    assert not errors
    assert read_result["data"] in (initial_data, new_data)
