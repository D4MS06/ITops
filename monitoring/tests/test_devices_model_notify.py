from __future__ import annotations

from monitoring.models.device import Device
from monitoring.models.devices_model import DevicesModel


class _StubDeviceService:
    def __init__(self, *, set_notify_result: bool = True) -> None:
        self._set_notify_result = bool(set_notify_result)
        self.set_notify_calls: list[tuple[str, bool]] = []
        self.write_map_calls = 0
        self._device = Device(
            ip="192.168.1.10",
            name="sw-core",
            description="Core switch",
            device_type="switch",
            device_id="dev-1",
        )

    @staticmethod
    def list_type_definitions() -> dict[str, dict]:
        return {
            "switch": {
                "code": "switch",
                "label": "Switch",
                "icon": "switch",
                "monitoring_enabled": True,
            }
        }

    def build_device_inventory(self, *, type_definitions: dict[str, dict]):
        _ = type_definitions
        return (
            {"switch": {"dev-1": self._device}},
            {"switch": {"dev-1": True}},
        )

    def set_device_notify(self, *, device_id: str, notify: bool) -> bool:
        self.set_notify_calls.append((str(device_id), bool(notify)))
        return self._set_notify_result

    def write_devices_map(self, *, device_data, notify_flags) -> None:
        _ = (device_data, notify_flags)
        self.write_map_calls += 1


def test_set_notify_flag_uses_targeted_storage_update():
    service = _StubDeviceService(set_notify_result=True)
    model = DevicesModel(manager=object(), device_service=service)

    changed = model.set_notify_flag("switch", "dev-1", False)

    assert changed is True
    assert service.set_notify_calls == [("dev-1", False)]
    assert service.write_map_calls == 0
    assert model.notify_flags["switch"]["dev-1"] is False


def test_set_notify_flag_keeps_state_unchanged_when_storage_update_fails():
    service = _StubDeviceService(set_notify_result=False)
    model = DevicesModel(manager=object(), device_service=service)

    changed = model.set_notify_flag("switch", "dev-1", False)

    assert changed is False
    assert service.set_notify_calls == [("dev-1", False)]
    assert service.write_map_calls == 0
    assert model.notify_flags["switch"]["dev-1"] is True
