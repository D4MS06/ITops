import asyncio
import subprocess
from unittest.mock import patch

from monitoring.models.devices_model import DevicesModel
from monitoring.services.monitoring_service import MonitoringService


def _build_model_with_data(data):
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.read_devices_map",
        return_value=data,
    ):
        return DevicesModel()


def test_monitoring_service_emits_event_and_notification_without_tkinter():
    model = _build_model_with_data(
        {
            "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc", "notify": True}],
            "switch": [],
        }
    )
    device = model.device_data["server"]["srv1"]
    device.status = "online"
    model.do_run["server"] = True

    service = MonitoringService(model, notifier=lambda title, message: None)
    service.set_offline_delay_seconds(1)
    service.set_failures_for_offline(1)
    service.set_probe_interval_ms(1000)
    clock_values = iter([0.0, 1.2])
    service._clock = lambda: next(clock_values)

    reachability = [False, False]
    events = []
    notifications = []
    cycles = []

    async def fake_reachability(_device):
        return reachability.pop(0)

    async def on_event(event):
        events.append(event)

    async def on_notification(title, message, dtype, dev):
        notifications.append((title, message, dtype, dev.id))

    async def on_cycle_complete(dtype, changed):
        cycles.append((dtype, changed))

    with patch.object(service._logs_store, "record_status_log") as record_log:
        real_sleep = asyncio.sleep
        ticks = {"count": 0}

        async def fake_sleep(delay):
            ticks["count"] += 1
            if ticks["count"] >= 2:
                model.do_run["server"] = False
            await real_sleep(0)

        with patch("asyncio.sleep", new=fake_sleep):
            asyncio.run(
                service.monitor_devices(
                    "server",
                    reachability_checker=fake_reachability,
                    on_event=on_event,
                    on_notification=on_notification,
                    on_cycle_complete=on_cycle_complete,
                )
            )

        assert len(events) == 1
        assert events[0].event_kind == "status_change"
        assert len(notifications) == 1
        assert notifications[0][2] == "server"
        assert any(changed is True for _, changed in cycles)
        record_log.assert_called_once()


def test_monitoring_service_marks_cycle_changed_on_idle_to_online_transition():
    model = _build_model_with_data(
        {
            "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc", "notify": True}],
            "switch": [],
        }
    )
    device = model.device_data["server"]["srv1"]
    device.status = "idle"
    model.do_run["server"] = True

    service = MonitoringService(model, notifier=lambda title, message: None)
    service.set_successes_for_online(2)
    service.set_probe_interval_ms(1000)

    cycles = []
    reachability = [True, True]

    async def fake_reachability(_device):
        return reachability.pop(0)

    async def on_cycle_complete(dtype, changed):
        cycles.append((dtype, changed, device.status))

    real_sleep = asyncio.sleep
    ticks = {"count": 0}

    async def fake_sleep(delay):
        ticks["count"] += 1
        if ticks["count"] >= 2:
            model.do_run["server"] = False
        await real_sleep(0)

    with patch("asyncio.sleep", new=fake_sleep):
        asyncio.run(
            service.monitor_devices(
                "server",
                reachability_checker=fake_reachability,
                on_cycle_complete=on_cycle_complete,
            )
        )

    assert cycles == [("server", False, "idle"), ("server", True, "online")]


def test_monitoring_service_requires_multiple_successes_before_idle_to_online():
    model = _build_model_with_data(
        {
            "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc", "notify": True}],
            "switch": [],
        }
    )
    device = model.device_data["server"]["srv1"]
    device.status = "idle"
    model.do_run["server"] = True

    service = MonitoringService(model, notifier=lambda title, message: None)
    service.set_successes_for_online(2)
    service.set_probe_interval_ms(1000)

    async def fake_reachability(_device):
        return True

    real_sleep = asyncio.sleep

    async def fake_sleep(delay):
        model.do_run["server"] = False
        await real_sleep(0)

    with patch("asyncio.sleep", new=fake_sleep):
        asyncio.run(
            service.monitor_devices(
                "server",
                reachability_checker=fake_reachability,
            )
        )

    assert device.status == "idle"


def test_monitoring_service_respects_notification_cooldown():
    model = _build_model_with_data(
        {
            "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc", "notify": True}],
            "switch": [],
        }
    )
    device = model.device_data["server"]["srv1"]
    device.status = "online"
    model.do_run["server"] = True

    sent_messages = []
    service = MonitoringService(model, notifier=lambda title, message: sent_messages.append((title, message)))
    service.set_offline_delay_seconds(1)
    service.set_online_recovery_delay_seconds(1)
    service.set_notification_cooldown_seconds(30)
    service.set_failures_for_offline(1)
    service.set_successes_for_online(1)
    service.set_probe_interval_ms(1000)

    reachability = [False, False, True, True]

    async def fake_reachability(_device):
        return reachability.pop(0)

    real_sleep = asyncio.sleep
    ticks = {"count": 0}

    async def fake_sleep(delay):
        ticks["count"] += 1
        if ticks["count"] >= 4:
            model.do_run["server"] = False
        await real_sleep(1.05)

    with patch("asyncio.sleep", new=fake_sleep):
        asyncio.run(service.monitor_devices("server", reachability_checker=fake_reachability))

    assert len(sent_messages) == 1


def test_monitoring_service_disables_aioping_on_windows():
    model = _build_model_with_data({"server": [], "switch": []})
    with patch("monitoring.services.monitoring_service.platform.system", return_value="Windows"):
        service = MonitoringService(model, notifier=lambda title, message: None)
    assert service._use_aioping is False


def test_monitoring_service_limits_ping_workers_on_windows():
    model = _build_model_with_data({"server": [], "switch": []})
    with patch("monitoring.services.monitoring_service.platform.system", return_value="Windows"):
        with patch("monitoring.services.monitoring_service.os.cpu_count", return_value=32):
            service = MonitoringService(model, notifier=lambda title, message: None)
    assert service._ping_executor._max_workers == 16
    service._ping_executor.shutdown(wait=False, cancel_futures=True)


def test_ping_with_system_command_discards_subprocess_output():
    completed = subprocess.CompletedProcess(args=["ping"], returncode=0)
    with patch("monitoring.services.monitoring_service.platform.system", return_value="Windows"):
        with patch("monitoring.services.monitoring_service.os.path.isfile", return_value=True):
            with patch("monitoring.services.monitoring_service.subprocess.run", return_value=completed) as run_mock:
                assert MonitoringService.ping_with_system_command("192.168.1.10", timeout_seconds=1.5) is True
    kwargs = run_mock.call_args.kwargs
    assert kwargs["stdout"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.DEVNULL
