from __future__ import annotations

import shutil
import subprocess
import webbrowser
import re
from typing import Callable

from monitoring.shared.action_compat import action_allows_os


class DeviceActionService:
    """Centralise les actions natives lancees depuis les vues devices."""

    def available_actions(self, *, action_rows: list[dict], subtype: str) -> list[str]:
        normalized_subtype = str(subtype or "").strip().lower()
        return [
            str(item.get("action_key", "")).strip().lower()
            for item in action_rows
            if action_allows_os(str(item.get("os_scope", "")), normalized_subtype)
        ]

    @staticmethod
    def can_run_action(device, action_key: str) -> bool:
        ip = str(getattr(device, "ip", "")).strip()
        teamviewer_id = str(getattr(device, "id_Teamviewer", "")).strip()
        if action_key == "teamviewer":
            return bool(teamviewer_id)
        if action_key in {"web", "ssh", "remote_desktop"}:
            return bool(ip)
        return False

    @staticmethod
    def default_action(*, device_type: str, subtype: str, available_actions: list[str], teamviewer_id: str) -> str:
        if available_actions:
            return available_actions[0]
        normalized_subtype = str(subtype or "").strip().lower()
        if normalized_subtype == "windows":
            return "teamviewer" if teamviewer_id else "remote_desktop"
        if normalized_subtype == "linux":
            return "ssh"
        if device_type == "server" and normalized_subtype == "dsm":
            return "web"
        return "web"

    @staticmethod
    def fallback_web_url(*, ip: str, subtype: str, web_url: str) -> str:
        normalized_ip = str(ip or "").strip()
        raw_url = str(web_url or "").strip()
        if raw_url:
            numeric = re.fullmatch(r":?(\d{1,5})", raw_url)
            if numeric:
                port = int(numeric.group(1))
                if normalized_ip and 1 <= port <= 65535:
                    return f"http://{normalized_ip}:{port}"
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw_url):
                return raw_url
            if re.match(r"^[^/\s:]+:\d{1,5}(?:[/?#]|$)", raw_url):
                return f"http://{raw_url}"
            if raw_url.startswith("/") and normalized_ip:
                return f"http://{normalized_ip}{raw_url}"
            return f"http://{raw_url}" if re.match(r"^[^\s/]+(?:[/?#].*)?$", raw_url) else raw_url
        normalized_subtype = str(subtype or "").strip().lower()
        if normalized_subtype == "dsm":
            return f"http://{normalized_ip}:5000"
        return f"http://{normalized_ip}"

    def resolve_action(
        self,
        *,
        device_type: str,
        device,
        configured_action: str,
        action_rows: list[dict],
    ) -> str:
        subtype = str(getattr(device, "type", "")).strip().lower()
        available = self.available_actions(action_rows=action_rows, subtype=subtype)
        action = str(configured_action or "").strip().lower()
        if action and action in available:
            return action
        return self.default_action(
            device_type=device_type,
            subtype=subtype,
            available_actions=available,
            teamviewer_id=str(getattr(device, "id_Teamviewer", "")).strip(),
        )

    def run_action(
        self,
        *,
        device,
        action_key: str,
        prompt_ssh_login: Callable[[str], str | None] | None = None,
    ) -> None:
        ip = str(getattr(device, "ip", "")).strip()
        subtype = str(getattr(device, "type", "")).strip().lower()
        teamviewer_id = str(getattr(device, "id_Teamviewer", "")).strip()
        web_url = str(getattr(device, "web_url", "")).strip()
        ssh_user = str(getattr(device, "ssh_user", "")).strip()

        if action_key == "teamviewer":
            if teamviewer_id:
                webbrowser.open(f"https://start.teamviewer.com/{teamviewer_id}")
            elif ip:
                subprocess.Popen(["mstsc", f"/v:{ip}"])
            return

        if action_key == "remote_desktop":
            subprocess.Popen(["mstsc", f"/v:{ip}"])
            return

        if action_key == "ssh":
            target_user = ssh_user
            if not target_user and prompt_ssh_login is not None:
                target_user = str(prompt_ssh_login(ip) or "").strip()
            if not target_user:
                subprocess.Popen(["cmd.exe", "/k", f"set /p u=SSH login: && ssh %u%@{ip}"])
                return
            target = f"{target_user}@{ip}"
            if shutil.which("wt"):
                subprocess.Popen(["wt", "ssh", target])
            else:
                subprocess.Popen(["cmd", "/c", "start", "ssh", target])
            return

        webbrowser.open(self.fallback_web_url(ip=ip, subtype=subtype, web_url=web_url))
