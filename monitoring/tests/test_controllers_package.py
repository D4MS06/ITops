import sys


def test_controllers_package_does_not_eager_import_tkinter_controller():
    sys.modules.pop("monitoring.controllers", None)
    sys.modules.pop("monitoring.controllers.app_controller", None)

    import monitoring.controllers as controllers  # noqa: F401

    assert "monitoring.controllers.app_controller" not in sys.modules

