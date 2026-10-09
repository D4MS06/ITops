from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from monitoring import __version__ as PACKAGE_VERSION

_PRE_RELEASE_BRANCH_RE = re.compile(r"^(?:pre-release|prerelease)/(\d+\.\d+(?:\.\d+)?)$", re.IGNORECASE)


def _extract_branch_version(branch_name: str) -> str:
    raw = str(branch_name or "").strip()
    if not raw:
        return ""
    match = _PRE_RELEASE_BRANCH_RE.match(raw)
    if match is None:
        return ""
    return str(match.group(1))


def detect_git_branch() -> str:
    env_branch = str(os.environ.get("NMP_GIT_BRANCH") or "").strip()
    if env_branch:
        return env_branch

    project_root = Path(__file__).resolve().parents[1]
    try:
        completed = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=0.8,
            check=False,
        )
    except Exception:
        return ""
    return_code = int(completed.returncode) if completed.returncode is not None else 1
    if return_code != 0:
        return ""
    return str(completed.stdout or "").strip()


def resolve_display_version(base_version: str | None = None, branch_name: str | None = None) -> str:
    base = str(base_version if base_version is not None else PACKAGE_VERSION).strip() or "unknown"
    branch = str(branch_name if branch_name is not None else detect_git_branch()).strip()
    branch_version = _extract_branch_version(branch)
    if not branch_version:
        return base
    suffix = "-pre-release" if "pre-release" in base.lower() else ""
    return f"{branch_version}{suffix}"
