from __future__ import annotations

import asyncio

from monitoring.models.device import Device
from monitoring.models.device_inventory_state import DeviceInventoryState
from monitoring.services.device_deployment import is_deployed_device
from monitoring.services.monitoring_service import MonitoringService


class _Model:
    def __init__(self, *devices: Device) -> None:
        from threading import RLock

        self.lock = RLock()
        self.do_run = {"switch": True}
        self.device_data = {"switch": {str(device.id): device for device in devices}}
        self.notify_flags = {"switch": {}}


def _device(device_id: str, deployment_status: str) -> Device:
    device = Device(ip="192.0.2.1", name=device_id, description="", device_type="switch", device_id=device_id)
    device.deployment_status = deployment_status
    return device


def test_only_deployed_status_is_eligible_for_monitoring():
    assert is_deployed_device(_device("deployed", "Déployé")) is True
    assert is_deployed_device(_device("test", "À tester")) is False
    assert is_deployed_device(_device("legacy", "")) is False


def test_monitoring_skips_non_deployed_equipment():
    deployed = _device("deployed", "Déployé")
    stored = _device("stored", "Stocké")
    model = _Model(deployed, stored)
    checked: list[str] = []

    async def checker(device: Device) -> bool:
        checked.append(str(device.id))
        model.do_run["switch"] = False
        return True

    service = MonitoringService(model=model)
    asyncio.run(service.monitor_devices("switch", reachability_checker=checker))

    assert checked == ["deployed"]


def test_deployed_only_snapshot_hides_non_deployed_equipment():
    deployed = _device("deployed", "Déployé")
    stored = _device("stored", "Stocké")
    state = DeviceInventoryState(device_data={"switch": {"deployed": deployed, "stored": stored}})

    snapshot = state.build_status_snapshot(deployed_only=True)

    assert [row["id"] for row in snapshot["switch"]] == ["deployed"]
