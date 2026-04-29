from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SetupInstallationState:
    completed: bool = False
    completed_at: str = ""
    completed_by: str = ""
    reverse_proxy_type: str = ""
    public_url: str = ""


def default_setup_state_path() -> Path:
    override = str(os.environ.get("NMP_SETUP_CONFIG") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "setup_installation.json"


def default_setup_token_file() -> Path:
    override = str(os.environ.get("NMP_SETUP_TOKEN_FILE") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "setup.token"


def default_install_env_file() -> Path:
    override = str(os.environ.get("NMP_INSTALL_ENV_PATH") or "").strip()
    if override:
        return Path(override)
    return Path("/etc/default/itops")


def load_setup_state(path: str | Path | None = None) -> SetupInstallationState:
    target = Path(path) if path is not None else default_setup_state_path()
    data: dict[str, object] = {}
    if target.is_file():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    return SetupInstallationState(
        completed=bool(data.get("completed", False)),
        completed_at=str(data.get("completed_at") or "").strip(),
        completed_by=str(data.get("completed_by") or "").strip(),
        reverse_proxy_type=str(data.get("reverse_proxy_type") or "").strip(),
        public_url=str(data.get("public_url") or "").strip(),
    )


def save_setup_state(state: SetupInstallationState, path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else default_setup_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "completed": bool(state.completed),
        "completed_at": str(state.completed_at or "").strip(),
        "completed_by": str(state.completed_by or "").strip(),
        "reverse_proxy_type": str(state.reverse_proxy_type or "").strip(),
        "public_url": str(state.public_url or "").strip(),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def read_setup_token(path: str | Path | None = None) -> str:
    target = Path(path) if path is not None else default_setup_token_file()
    if not target.is_file():
        return ""
    try:
        return str(target.read_text(encoding="utf-8") or "").strip()
    except Exception:
        return ""


def remove_setup_token(path: str | Path | None = None) -> None:
    target = Path(path) if path is not None else default_setup_token_file()
    try:
        if target.is_file():
            target.unlink()
    except Exception:
        return


def update_install_env(updates: dict[str, str], *, path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else default_install_env_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    current: dict[str, str] = {}
    if target.is_file():
        for raw in target.read_text(encoding="utf-8").splitlines():
            line = str(raw or "").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            current[str(key).strip()] = str(value).strip()
    for key, value in dict(updates or {}).items():
        normalized_key = str(key or "").strip()
        if not normalized_key:
            continue
        current[normalized_key] = _shell_quote(str(value or ""))
    lines = [f"{key}={value}" for key, value in sorted(current.items())]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _shell_quote(value: str) -> str:
    raw = str(value or "")
    escaped = raw.replace("'", "'\"'\"'")
    return f"'{escaped}'"

