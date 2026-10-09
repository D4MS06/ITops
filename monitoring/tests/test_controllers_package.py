import sys


def test_controllers_package_exports_web_controllers_only():
    sys.modules.pop("monitoring.controllers", None)

    import monitoring.controllers as controllers

    assert sorted(list(getattr(controllers, "__all__", []))) == ["DeviceTypeController", "NetworkToolsController"]
    assert not hasattr(controllers, "AppController")
