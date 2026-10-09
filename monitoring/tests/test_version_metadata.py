from pathlib import Path
import re

import monitoring


def test_monitoring_package_version_matches_root_metadata():
    root_init = Path(__file__).resolve().parents[2] / "__init__.py"
    content = root_init.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    assert match is not None
    assert monitoring.__version__ == match.group(1)
