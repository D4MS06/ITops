#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pwd
import re
import subprocess
import sys
from pathlib import Path


MOUNT_ROOT = Path("/mnt/itops-storage")
SYSTEMD_DIR = Path("/etc/systemd/system")
CREDENTIALS_DIR = Path("/etc/itops/smb")
ALLOWED_ACTIONS = {"ensure_smb_mount", "remove_mount", "status_mount", "store_smb_credentials"}


class HelperError(Exception):
    pass


def main() -> int:
    try:
        if os.geteuid() != 0:
            raise HelperError("Le helper stockage ITops doit etre execute en root via sudo.")
        action = sys.argv[1] if len(sys.argv) > 1 else ""
        if action not in ALLOWED_ACTIONS:
            raise HelperError("Action helper stockage non autorisee.")
        payload = _read_payload()
        if action == "ensure_smb_mount":
            result = ensure_smb_mount(payload)
        elif action == "remove_mount":
            result = remove_mount(payload)
        elif action == "status_mount":
            result = status_mount(payload)
        else:
            result = store_smb_credentials(payload)
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
        return 0
    except HelperError as exc:
        print(json.dumps({"ok": False, "message": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:  # pragma: no cover - helper defensive boundary
        print(json.dumps({"ok": False, "message": f"Erreur helper stockage: {exc}"}, ensure_ascii=False))
        return 1


def _read_payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HelperError(f"Payload JSON invalide: {exc}") from exc
    if not isinstance(payload, dict):
        raise HelperError("Payload JSON invalide.")
    return payload


def ensure_smb_mount(payload: dict) -> dict:
    target_id = _safe_id(payload.get("target_id") or "")
    unc = _normalize_unc(payload.get("remote_path") or "")
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    mount_path = _validated_mount_path(payload.get("mount_path") or "")
    app_user = _safe_user(payload.get("app_user") or "root")
    uid = pwd.getpwnam(app_user).pw_uid
    gid = pwd.getpwnam(app_user).pw_gid
    share_source, rest = _split_unc_for_linux(unc)
    final_path = mount_path
    for part in rest:
        final_path = final_path / part

    mount_path.mkdir(parents=True, exist_ok=True)
    os.chown(mount_path, uid, gid)
    mount_path.chmod(0o770)

    credentials_path = _write_credentials(target_id=target_id, username=username, password=password, allow_existing=True)
    unit_name = _systemd_mount_unit_name(mount_path)
    automount_name = unit_name.replace(".mount", ".automount")
    mount_unit = SYSTEMD_DIR / unit_name
    automount_unit = SYSTEMD_DIR / automount_name
    options = ",".join(
        [
            f"credentials={credentials_path}",
            "iocharset=utf8",
            "vers=3.0",
            "sec=ntlmssp",
            f"uid={uid}",
            f"gid={gid}",
            "file_mode=0660",
            "dir_mode=0770",
            "noperm",
            "nofail",
            "x-systemd.automount",
            "x-systemd.idle-timeout=60",
        ]
    )
    mount_unit.write_text(
        "\n".join(
            [
                "[Unit]",
                f"Description=ITops SMB storage {target_id}",
                "After=network-online.target",
                "Wants=network-online.target",
                "",
                "[Mount]",
                f"What={share_source}",
                f"Where={mount_path}",
                "Type=cifs",
                f"Options={options}",
                "",
                "[Install]",
                "WantedBy=multi-user.target",
                "",
            ]
        ),
        encoding="utf-8",
    )
    mount_unit.chmod(0o644)
    automount_unit.write_text(
        "\n".join(
            [
                "[Unit]",
                f"Description=ITops SMB automount {target_id}",
                "After=network-online.target",
                "",
                "[Automount]",
                f"Where={mount_path}",
                "TimeoutIdleSec=60",
                "",
                "[Install]",
                "WantedBy=multi-user.target",
                "",
            ]
        ),
        encoding="utf-8",
    )
    automount_unit.chmod(0o644)
    _run(["systemctl", "daemon-reload"])
    _run(["systemctl", "enable", "--now", automount_name])
    _run(["systemctl", "start", unit_name])
    check = _probe_path(final_path, uid=uid, gid=gid)
    return {
        "message": f"Montage systemd actif: {final_path}",
        "unit": unit_name,
        "automount_unit": automount_name,
        "mount_path": str(mount_path),
        "target_path": str(final_path),
        "accessible": check,
    }


def store_smb_credentials(payload: dict) -> dict:
    target_id = _safe_id(payload.get("target_id") or "")
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    credentials_path = _write_credentials(target_id=target_id, username=username, password=password, allow_existing=False)
    return {"message": f"Identifiants SMB enregistres: {credentials_path}", "credentials_path": str(credentials_path)}


def remove_mount(payload: dict) -> dict:
    target_id = _safe_id(payload.get("target_id") or "")
    mount_path = _validated_mount_path(payload.get("mount_path") or "")
    unit_name = _systemd_mount_unit_name(mount_path)
    automount_name = unit_name.replace(".mount", ".automount")
    _run(["systemctl", "disable", "--now", automount_name], check=False)
    _run(["systemctl", "disable", "--now", unit_name], check=False)
    for path in (SYSTEMD_DIR / automount_name, SYSTEMD_DIR / unit_name):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    try:
        (CREDENTIALS_DIR / f"{target_id}.cred").unlink()
    except FileNotFoundError:
        pass
    _run(["systemctl", "daemon-reload"])
    return {"message": "Montage systemd supprime.", "unit": unit_name, "automount_unit": automount_name}


def status_mount(payload: dict) -> dict:
    mount_path = _validated_mount_path(payload.get("mount_path") or "")
    unit_name = _systemd_mount_unit_name(mount_path)
    automount_name = unit_name.replace(".mount", ".automount")
    active = _run(["systemctl", "is-active", automount_name], check=False).returncode == 0
    mounted = _run(["mountpoint", "-q", str(mount_path)], check=False).returncode == 0
    return {
        "message": "Automount actif." if active else "Automount inactif.",
        "unit": unit_name,
        "automount_unit": automount_name,
        "mount_path": str(mount_path),
        "active": active,
        "mounted": mounted,
    }


def _write_credentials(*, target_id: str, username: str, password: str, allow_existing: bool) -> Path:
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_DIR.chmod(0o700)
    path = CREDENTIALS_DIR / f"{target_id}.cred"
    if not password and allow_existing and path.is_file():
        return path
    if not password:
        raise HelperError("Mot de passe SMB absent pour cette cible. Recréez l'emplacement en renseignant le mot de passe.")
    domain = ""
    user = username
    if "\\" in username:
        domain, user = username.split("\\", 1)
    elif "/" in username:
        domain, user = username.split("/", 1)
    lines = [f"username={user.strip()}", f"password={password}"]
    if domain.strip():
        lines.append(f"domain={domain.strip()}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def _probe_path(path: Path, *, uid: int, gid: int) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".itops_write_test"
    probe.write_text("ok", encoding="utf-8")
    os.chown(probe, uid, gid)
    probe.unlink(missing_ok=True)
    return True


def _run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, capture_output=True, text=True, shell=False, timeout=30)
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        if len(args) >= 3 and args[0] == "systemctl" and args[1] == "start":
            detail = _systemd_failure_detail(args[2], fallback=detail)
        raise HelperError(f"Commande systeme echouee ({' '.join(args)}): {detail}")
    return proc


def _systemd_failure_detail(unit_name: str, *, fallback: str) -> str:
    details: list[str] = []
    for cmd in (
        ["systemctl", "--no-pager", "--full", "status", unit_name],
        ["journalctl", "-u", unit_name, "-n", "30", "--no-pager"],
    ):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, shell=False, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        text = (proc.stdout or proc.stderr or "").strip()
        if text:
            details.append(text)
    return "\n".join(details).strip() or fallback


def _systemd_mount_unit_name(path: Path) -> str:
    proc = _run(["systemd-escape", "--path", "--suffix=mount", str(path)])
    unit_name = proc.stdout.strip()
    if not unit_name.endswith(".mount"):
        raise HelperError("Nom unite systemd invalide.")
    return unit_name


def _split_unc_for_linux(unc: str) -> tuple[str, list[str]]:
    parts = [part for part in unc.split("\\") if part]
    if len(parts) < 2:
        raise HelperError("Chemin UNC invalide.")
    return f"//{parts[0]}/{parts[1]}", parts[2:]


def _normalize_unc(value: object) -> str:
    raw = str(value or "").strip()
    if raw.startswith("//"):
        parts = [part for part in raw.split("/") if part]
        if len(parts) >= 2:
            raw = "\\\\" + "\\".join(parts)
    if not raw.startswith("\\\\"):
        raise HelperError("Chemin SMB attendu au format \\\\serveur\\partage\\dossier.")
    return raw


def _validated_mount_path(value: object) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise HelperError("Point de montage local manquant.")
    path = Path(raw).resolve()
    root = MOUNT_ROOT.resolve()
    if path == root or root not in path.parents:
        raise HelperError(f"Point de montage refuse: doit etre sous {root}.")
    return path


def _safe_id(value: object) -> str:
    raw = str(value or "").strip()
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", raw)
    if not safe:
        raise HelperError("Identifiant cible stockage manquant.")
    return safe[:120]


def _safe_user(value: object) -> str:
    raw = str(value or "").strip() or "root"
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", raw):
        raise HelperError("Utilisateur applicatif invalide.")
    return raw


if __name__ == "__main__":
    raise SystemExit(main())
