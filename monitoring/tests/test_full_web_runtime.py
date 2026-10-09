import subprocess
import sys


def test_api_import_does_not_load_desktop_modules():
    script = (
        "import sys;"
        "import monitoring.api.app;"
        "mods=[m for m in sys.modules if m=='tkinter' or m.startswith('monitoring.ui')];"
        "print(','.join(mods));"
        "raise SystemExit(1 if mods else 0)"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, f"Desktop modules loaded in web runtime: {result.stdout}{result.stderr}"
