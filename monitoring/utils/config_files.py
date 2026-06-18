from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.utils.app_paths import app_data_root

DEFAULT_CONFIG_DIR_NAME = "switch_configs"
DEFAULT_LOCAL_VERSIONS_DIR_NAME = "config_versions"
DEFAULT_LINUX_SMB_MOUNT_ROOT = Path("/mnt/itops-smb")
_CONFIG_VERSIONS_STORE: MariaDBFileManager | None = None
_CONFIG_VERSIONS_STORE_LOCK = threading.Lock()


def default_switch_configs_dir() -> Path:
    return app_data_root() / DEFAULT_CONFIG_DIR_NAME


def resolve_switch_configs_dir(configured_dir: str | None) -> Path:
    raw = str(configured_dir or "").strip()
    if raw:
        return Path(raw).expanduser()
    return default_switch_configs_dir()


def resolve_active_config_source_dir(settings) -> Path:
    mode = str(getattr(settings, "config_storage_mode", "local") or "local").strip().lower()
    if mode == "smb3":
        unc = str(getattr(settings, "config_smb_unc_path", "") or "").strip()
        if unc:
            if os.name != "nt" and unc.startswith("\\\\"):
                parsed = _parse_unc_path(unc)
                if parsed is not None:
                    _share_source, _mount_dir, final_path = _linux_unc_mount_paths(parsed)
                    return final_path
            return Path(unc)
    return resolve_switch_configs_dir(str(getattr(settings, "switch_configs_dir", "") or "").strip())


def resolve_config_backup_dir(settings) -> Path:
    return resolve_active_config_source_dir(settings)


def describe_config_remote_mount(settings, *, service_code: str, service_label: str) -> dict[str, object]:
    mode = str(getattr(settings, "config_storage_mode", "local") or "local").strip().lower()
    unc = str(getattr(settings, "config_smb_unc_path", "") or "").strip()
    if mode != "smb3":
        return {
            "service_code": service_code,
            "service_label": service_label,
            "mode": mode or "local",
            "source_path": "",
            "mount_path": "",
            "target_path": "",
            "mounted": False,
            "accessible": False,
            "status": "inactive",
            "message": "Aucun stockage distant actif pour ce service.",
        }
    if not unc:
        return {
            "service_code": service_code,
            "service_label": service_label,
            "mode": "smb3",
            "source_path": "",
            "mount_path": "",
            "target_path": "",
            "mounted": False,
            "accessible": False,
            "status": "missing_config",
            "message": "Destination SMB non renseignee.",
        }
    mounted = False
    source_path = unc
    mount_path = ""
    if os.name != "nt" and unc.startswith("\\\\"):
        parsed = _parse_unc_path(unc)
        if parsed is not None:
            source_path, mount_dir, target_path = _linux_unc_mount_paths(parsed)
            mount_path = str(mount_dir)
            mounted = _is_linux_mountpoint(mount_dir)
        else:
            target_path = Path(unc)
    else:
        target_path = Path(unc)
        mounted = target_path.is_dir()
    accessible = False
    try:
        accessible = target_path.is_dir()
    except OSError:
        accessible = False
    if accessible:
        status = "mounted" if mounted else "accessible"
        message = "Destination distante accessible."
    elif mounted:
        status = "mounted_unavailable"
        message = "Point de montage actif mais dossier cible inaccessible."
    else:
        status = "configured"
        message = "Destination distante configuree mais non montee ou inaccessible."
    return {
        "service_code": service_code,
        "service_label": service_label,
        "mode": "smb3",
        "source_path": source_path,
        "mount_path": mount_path,
        "target_path": str(target_path),
        "mounted": mounted,
        "accessible": accessible,
        "status": status,
        "message": message,
    }


def ensure_smb3_connection(settings) -> tuple[bool, str]:
    mode = str(getattr(settings, "config_storage_mode", "local") or "local").strip().lower()
    if mode != "smb3":
        return True, "mode_local"
    unc = str(getattr(settings, "config_smb_unc_path", "") or "").strip()
    username = str(getattr(settings, "config_smb_username", "") or "").strip()
    password = str(getattr(settings, "config_smb_password", "") or "").strip()
    if not unc:
        return False, "Chemin UNC SMB3 manquant."
    if os.name != "nt":
        if unc.startswith("\\\\"):
            return _ensure_linux_unc_smb_connection(unc, username=username, password=password)
        path = Path(unc)
        if path.is_dir():
            return True, "Chemin distant monte accessible."
        return False, f"Chemin distant monte inaccessible depuis le serveur: {path}"
    if not unc.startswith("\\\\"):
        return False, "Le chemin SMB doit etre au format UNC (\\\\serveur\\partage)."
    chunks = [part for part in unc.split("\\") if part]
    if len(chunks) < 2:
        return False, "Chemin UNC invalide."
    share_root = "\\\\" + chunks[0] + "\\" + chunks[1]
    try:
        if Path(unc).is_dir():
            return True, "ok_existing"
    except OSError:
        pass
    cmd = ["net", "use", share_root, "/persistent:no"]
    if username:
        cmd.insert(3, f"/user:{username}")
        cmd.insert(4, password)
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    combined = f"{stderr}\n{stdout}".strip().lower()
    if proc.returncode != 0 and "already" not in combined:
        if "1219" in combined:
            try:
                if Path(unc).is_dir():
                    return True, "ok_existing"
            except OSError:
                pass
            return (
                False,
                "Le serveur SMB est deja connecte avec d'autres identifiants sur ce poste. "
                "Fermez les connexions existantes vers ce serveur ou utilisez les memes identifiants.",
            )
        return False, (stderr or stdout or "Connexion SMB3 impossible.").strip()
    try:
        return Path(unc).is_dir(), "ok"
    except OSError as exc:
        return False, str(exc)


def ensure_smb3_connection_to_mount(
    *,
    unc: str,
    username: str = "",
    password: str = "",
    mount_dir: Path | str | None = None,
) -> tuple[bool, str]:
    raw_unc = str(unc or "").strip()
    if not raw_unc:
        return False, "Chemin UNC SMB3 manquant."
    if os.name == "nt":
        settings = type(
            "SmbSettings",
            (),
            {
                "config_storage_mode": "smb3",
                "config_smb_unc_path": raw_unc,
                "config_smb_username": username,
                "config_smb_password": password,
            },
        )()
        return ensure_smb3_connection(settings)
    if not raw_unc.startswith("\\\\"):
        path = Path(raw_unc)
        if path.is_dir():
            return True, f"Chemin distant monte accessible: {path}"
        return False, f"Chemin distant monte inaccessible depuis le serveur: {path}"
    parsed = _parse_unc_path(raw_unc)
    if parsed is None:
        return False, "Chemin UNC SMB invalide. Format attendu: \\\\serveur\\partage\\dossier."
    share_source, _default_mount_dir, _default_final_path = _linux_unc_mount_paths(parsed)
    if mount_dir is None or not str(mount_dir).strip():
        return _ensure_linux_unc_smb_connection(raw_unc, username=username, password=password)
    target_mount_dir = Path(str(mount_dir)).expanduser()
    _host, _share, rest = parsed
    final_path = target_mount_dir
    for part in rest:
        final_path = final_path / part
    return _ensure_linux_unc_smb_connection_at_paths(
        share_source=share_source,
        mount_dir=target_mount_dir,
        final_path=final_path,
        username=username,
        password=password,
    )


def _parse_unc_path(value: str) -> tuple[str, str, tuple[str, ...]] | None:
    raw = str(value or "").strip()
    if not raw.startswith("\\\\"):
        return None
    parts = [part for part in raw.split("\\") if part]
    if len(parts) < 2:
        return None
    return parts[0], parts[1], tuple(parts[2:])


def _linux_unc_mount_paths(parsed_unc: tuple[str, str, tuple[str, ...]]) -> tuple[str, Path, Path]:
    host, share, rest = parsed_unc
    mount_dir = DEFAULT_LINUX_SMB_MOUNT_ROOT / _safe_mount_part(host) / _safe_mount_part(share)
    final_path = mount_dir
    for part in rest:
        final_path = final_path / part
    return f"//{host}/{share}", mount_dir, final_path


def _ensure_linux_unc_smb_connection(unc: str, *, username: str, password: str) -> tuple[bool, str]:
    parsed = _parse_unc_path(unc)
    if parsed is None:
        return False, "Chemin UNC SMB invalide. Format attendu: \\\\serveur\\partage\\dossier."
    share_source, mount_dir, final_path = _linux_unc_mount_paths(parsed)
    return _ensure_linux_unc_smb_connection_at_paths(
        share_source=share_source,
        mount_dir=mount_dir,
        final_path=final_path,
        username=username,
        password=password,
    )


def _ensure_linux_unc_smb_connection_at_paths(
    *,
    share_source: str,
    mount_dir: Path,
    final_path: Path,
    username: str,
    password: str,
) -> tuple[bool, str]:
    try:
        mount_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"Creation du point de montage impossible ({mount_dir}): {exc}"

    if _is_linux_mountpoint(mount_dir):
        return _ensure_linux_backup_target_dir(final_path, mounted=True)

    mount_binary = shutil.which("mount")
    if not mount_binary:
        return False, "Commande mount introuvable sur le serveur Linux."
    mount_cifs_binary = _find_mount_cifs_binary()
    if mount_cifs_binary is None:
        return (
            False,
            "Support CIFS absent sur le serveur Linux: /sbin/mount.cifs introuvable. "
            "Installez le paquet cifs-utils puis relancez le test.",
        )

    credentials_file: Path | None = None
    try:
        options = ["iocharset=utf8", "vers=3.0", "sec=ntlmssp"]
        if username or password:
            smb_domain, smb_username = _split_smb_username(username)
            handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
            credentials_file = Path(handle.name)
            with handle:
                handle.write(f"username={smb_username}\n")
                handle.write(f"password={password}\n")
                if smb_domain:
                    handle.write(f"domain={smb_domain}\n")
            credentials_file.chmod(0o600)
            options.append(f"credentials={credentials_file}")
        else:
            options.append("guest")
        proc = subprocess.run(
            [mount_binary, "-t", "cifs", share_source, str(mount_dir), "-o", ",".join(options)],
            capture_output=True,
            text=True,
            shell=False,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return False, f"Montage SMB trop long: {share_source}"
    except OSError as exc:
        return False, f"Montage SMB impossible: {exc}"
    finally:
        if credentials_file is not None:
            try:
                credentials_file.unlink(missing_ok=True)
            except OSError:
                pass

    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    if proc.returncode != 0:
        detail = stderr or stdout or "Erreur mount.cifs inconnue."
        lowered_detail = detail.lower()
        if "permission denied" in lowered_detail or "error(13)" in lowered_detail:
            retry_proc = _retry_linux_cifs_mount_with_inline_credentials(
                mount_binary=mount_binary,
                share_source=share_source,
                mount_dir=mount_dir,
                username=username,
                password=password,
            )
            if retry_proc is not None and retry_proc.returncode == 0:
                return _ensure_linux_backup_target_dir(final_path, mounted=False)
            if retry_proc is not None:
                retry_detail = ((retry_proc.stderr or "").strip() or (retry_proc.stdout or "").strip())
                if retry_detail:
                    detail = retry_detail
            return (
                False,
                f"Acces refuse par le serveur SMB pour {share_source}: {detail}. "
                "Verifiez le mot de passe, le compte, le domaine/workgroup eventuel, "
                "et les droits du compte sur le partage et le dossier cible. "
                "Si le compte est un compte de domaine, saisissez l'utilisateur sous la forme DOMAINE\\utilisateur.",
            )
        return (
            False,
            f"Montage SMB impossible pour {share_source} vers {mount_dir}: {detail}. "
            "Verifiez que cifs-utils est installe et que le service ITops a le droit de monter des partages CIFS.",
        )
    return _ensure_linux_backup_target_dir(final_path, mounted=False)


def _retry_linux_cifs_mount_with_inline_credentials(
    *,
    mount_binary: str,
    share_source: str,
    mount_dir: Path,
    username: str,
    password: str,
) -> subprocess.CompletedProcess[str] | None:
    if not (username or password):
        return None
    smb_domain, smb_username = _split_smb_username(username)
    options = ["iocharset=utf8", "vers=3.0", "sec=ntlmssp"]
    if smb_username:
        options.append(f"username={smb_username}")
    if password:
        options.append(f"password={password}")
    if smb_domain:
        options.append(f"domain={smb_domain}")
    try:
        return subprocess.run(
            [mount_binary, "-t", "cifs", share_source, str(mount_dir), "-o", ",".join(options)],
            capture_output=True,
            text=True,
            shell=False,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _split_smb_username(username: str) -> tuple[str, str]:
    raw = str(username or "").strip()
    if "\\" in raw:
        domain, user = raw.split("\\", 1)
        return domain.strip(), user.strip()
    if "/" in raw:
        domain, user = raw.split("/", 1)
        return domain.strip(), user.strip()
    return "", raw


def _find_mount_cifs_binary() -> str | None:
    found = shutil.which("mount.cifs")
    if found:
        return found
    for candidate in ("/sbin/mount.cifs", "/usr/sbin/mount.cifs"):
        if Path(candidate).is_file():
            return candidate
    return None


def _ensure_linux_backup_target_dir(path: Path, *, mounted: bool) -> tuple[bool, str]:
    try:
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        probe = path / ".itops_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return False, f"Destination SMB montee mais non accessible en ecriture ({path}): {exc}"
    prefix = "Partage SMB deja monte" if mounted else "Partage SMB monte"
    return True, f"{prefix} et accessible: {path}"


def _is_linux_mountpoint(path: Path) -> bool:
    try:
        proc = subprocess.run(
            ["mountpoint", "-q", str(path)],
            capture_output=True,
            text=True,
            shell=False,
            timeout=5,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _safe_mount_part(value: str) -> str:
    raw = str(value or "").strip()
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in raw)
    return cleaned.strip("._-") or "unknown"


def default_local_config_versions_dir() -> Path:
    return app_data_root() / DEFAULT_LOCAL_VERSIONS_DIR_NAME


def resolve_local_type_versions_dir(*, device_type: str) -> Path:
    dtype = str(device_type or "").strip().lower()
    if not dtype:
        dtype = "unknown"
    return default_local_config_versions_dir() / dtype


def _normalize_token(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return "".join(ch if ch.isalnum() else "_" for ch in text)


def find_switch_config_files(
    root_dir: Path,
    switch_name: str,
    switch_ip: str,
    *,
    max_results: int = 20,
) -> list[Path]:
    root = Path(root_dir)
    try:
        is_dir = root.is_dir()
    except OSError:
        return []
    if not is_dir:
        return []

    name_token = _normalize_token(switch_name)
    ip_token = str(switch_ip or "").strip().lower()
    ip_flat = "".join(ch for ch in ip_token if ch.isalnum())
    require_ip_match = bool(ip_token)

    matches: list[tuple[int, float, Path]] = []
    try:
        iterator = root.rglob("*")
    except OSError:
        return []
    for candidate in iterator:
        try:
            if not candidate.is_file():
                continue
        except OSError:
            continue

        file_name = candidate.name.lower()
        stem_token = _normalize_token(candidate.stem)
        flat_name = "".join(ch for ch in file_name if ch.isalnum())
        has_ip_match = bool(ip_token and ip_token in file_name) or bool(ip_flat and ip_flat in flat_name)
        if require_ip_match and not has_ip_match:
            continue

        score = 0
        if ip_token and ip_token in file_name:
            score += 120
        if ip_flat and ip_flat and ip_flat in flat_name:
            score += 60
        if name_token and name_token in stem_token:
            score += 90
        if name_token and name_token in _normalize_token(str(candidate.parent)):
            score += 40
        if (ip_token or ip_flat) and name_token and score:
            score += 30

        if score <= 0:
            continue
        try:
            mtime = candidate.stat().st_mtime
        except OSError:
            mtime = 0.0
        matches.append((score, mtime, candidate))

    matches.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [item[2] for item in matches[:max_results]]


def open_path_with_default_app(path: Path) -> None:
    target = str(Path(path))
    if os.name == "nt":
        os.startfile(target)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", target], shell=False)
        return
    subprocess.Popen(["xdg-open", target], shell=False)


def _load_sync_index(index_file: Path) -> dict[str, dict]:
    if not index_file.is_file():
        return {}
    try:
        raw = json.loads(index_file.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_sync_index(index_file: Path, index: dict[str, dict]) -> None:
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _source_signature(path: Path) -> str:
    stat = path.stat()
    return f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"


def file_creation_datetime(source_file: Path) -> datetime:
    src = Path(source_file)
    stat = src.stat()
    # On Windows, st_ctime est la creation; ailleurs c'est metadata change time.
    return datetime.fromtimestamp(float(stat.st_ctime))


def build_versioned_filename(source_file: Path, *, stamp_dt: datetime | None = None) -> str:
    src = Path(source_file)
    dt = stamp_dt or file_creation_datetime(src)
    stamp = dt.strftime("%Y%m%d-%H%M%S")
    return f"{src.stem}_{stamp}{src.suffix}"


def _ensure_unique_target(path: Path) -> Path:
    target = Path(path)
    if not target.exists():
        return target
    idx = 2
    while True:
        candidate = target.with_name(f"{target.stem}_{idx}{target.suffix}")
        if not candidate.exists():
            return candidate
        idx += 1


def _sanitize_path_part(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "unknown"
    cleaned = "".join(ch if ch.isalnum() or ch in {" ", "-", "_", "."} else "_" for ch in raw)
    cleaned = " ".join(cleaned.split()).strip(" .")
    return cleaned or "unknown"


def _sanitize_filename_token(value: str) -> str:
    return _sanitize_path_part(value).replace(" ", "_")


def build_device_config_filename(
    *,
    device_type_label: str,
    device_name: str,
    source_file: Path,
    stamp_dt: datetime | None = None,
) -> str:
    src = Path(source_file)
    dt = stamp_dt or file_creation_datetime(src)
    stamp = dt.strftime("%Y-%m-%d_%H-%M-%S")
    suffix = src.suffix or ".cfg"
    type_token = _sanitize_filename_token(device_type_label)
    dev_token = _sanitize_filename_token(device_name)
    return f"{type_token}_{dev_token}_{stamp}{suffix}"


def _device_versions_dir(*, local_versions_root: Path, device_type_label: str, device_name: str) -> Path:
    return (
        Path(local_versions_root)
        / _sanitize_path_part(device_type_label)
        / _sanitize_path_part(device_name)
    )


def resolve_local_device_versions_dir(
    *,
    local_versions_root: Path,
    device_type_label: str,
    device_name: str,
) -> Path:
    return _device_versions_dir(
        local_versions_root=Path(local_versions_root),
        device_type_label=device_type_label,
        device_name=device_name,
    )


def _config_versions_store() -> MariaDBFileManager:
    global _CONFIG_VERSIONS_STORE
    with _CONFIG_VERSIONS_STORE_LOCK:
        if _CONFIG_VERSIONS_STORE is None:
            _CONFIG_VERSIONS_STORE = MariaDBFileManager()
        return _CONFIG_VERSIONS_STORE


def sync_latest_config_versions_for_type(
    *,
    source_root: Path,
    local_versions_root: Path,
    device_type: str,
    device_type_label: str | None = None,
    devices: list[dict],
    max_matches_per_device: int = 3,
) -> dict[str, int]:
    source = Path(source_root)
    local_root = Path(local_versions_root)
    if not source.is_dir():
        return {"scanned": 0, "copied": 0}
    dtype = str(device_type or "").strip().lower() or "unknown"
    type_label = _sanitize_path_part(str(device_type_label or dtype))
    type_root = local_root / type_label
    index_file = type_root / ".sync_index.json"
    index = _load_sync_index(index_file)
    copied = 0
    scanned = 0

    for dev in devices:
        did = str(dev.get("id", "")).strip()
        name = str(dev.get("name", "")).strip()
        ip = str(dev.get("ip", "")).strip()
        if not did:
            continue
        matches = find_switch_config_files(source, name, ip, max_results=max_matches_per_device)
        scanned += len(matches)
        device_folder = _sanitize_path_part(name or did)
        dev_dir = type_root / device_folder
        dev_dir.mkdir(parents=True, exist_ok=True)
        for src in matches:
            src_key = f"{did}|{str(src.resolve())}"
            try:
                sig = _source_signature(src)
            except Exception:
                continue
            if str(index.get(src_key, {}).get("sig", "")) == sig:
                continue
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = dev_dir / f"{src.stem}_{stamp}{src.suffix}"
            try:
                target.write_bytes(src.read_bytes())
            except Exception:
                continue
            index[src_key] = {"sig": sig, "last_target": str(target)}
            copied += 1
    _save_sync_index(index_file, index)
    return {"scanned": scanned, "copied": copied}


def store_imported_config_version(
    *,
    local_versions_root: Path,
    device_type_label: str,
    device_name: str,
    source_file: Path,
    detail: str = "",
    stamp_dt: datetime | None = None,
) -> Path:
    src = Path(source_file)
    if not src.is_file():
        raise FileNotFoundError(str(src))
    device_dir = _device_versions_dir(
        local_versions_root=Path(local_versions_root),
        device_type_label=device_type_label,
        device_name=device_name,
    )
    device_dir.mkdir(parents=True, exist_ok=True)
    target = device_dir / build_device_config_filename(
        device_type_label=device_type_label,
        device_name=device_name,
        source_file=src,
        stamp_dt=stamp_dt,
    )
    target = _ensure_unique_target(target)
    target.write_bytes(src.read_bytes())
    _config_versions_store().upsert_config_file_version(
        file_path=str(target),
        device_type_label=device_type_label,
        device_name=device_name,
        filename=target.name,
        detail=str(detail or "").strip(),
    )
    return target


def sync_local_versions_to_backup(
    *,
    local_versions_root: Path,
    backup_root: Path,
) -> dict[str, int]:
    source_root = Path(local_versions_root)
    target_root = Path(backup_root)
    if not source_root.is_dir():
        return {"scanned": 0, "copied": 0}

    scanned = 0
    copied = 0
    for src in source_root.rglob("*"):
        if not src.is_file():
            continue
        if src.name.startswith("."):
            continue
        scanned += 1
        rel_path = src.relative_to(source_root)
        dst = target_root / rel_path
        try:
            src_stat = src.stat()
        except OSError:
            continue
        should_copy = True
        if dst.is_file():
            try:
                dst_stat = dst.stat()
                should_copy = (
                    int(dst_stat.st_size) != int(src_stat.st_size)
                    or int(dst_stat.st_mtime_ns) != int(src_stat.st_mtime_ns)
                )
            except OSError:
                should_copy = True
        if not should_copy:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        try:
            os.utime(dst, ns=(src_stat.st_atime_ns, src_stat.st_mtime_ns))
        except Exception:
            pass
        copied += 1
    return {"scanned": scanned, "copied": copied}


def list_local_config_versions(
    *,
    local_versions_root: Path,
    device_type_label: str,
    device_name: str,
) -> list[dict]:
    device_dir = _device_versions_dir(
        local_versions_root=Path(local_versions_root),
        device_type_label=device_type_label,
        device_name=device_name,
    )
    if not device_dir.is_dir():
        return []
    meta_rows = _config_versions_store().list_config_file_versions(
        device_type_label=device_type_label,
        device_name=device_name,
    )
    details_by_path = {str(row.get("file_path", "")): str(row.get("detail", "")) for row in meta_rows}
    details_by_name = {str(row.get("filename", "")): str(row.get("detail", "")) for row in meta_rows}
    rows: list[dict] = []
    for candidate in device_dir.iterdir():
        if not candidate.is_file():
            continue
        if candidate.name.startswith("."):
            continue
        try:
            mtime = candidate.stat().st_mtime
        except OSError:
            mtime = 0.0
        rows.append(
            {
                "name": candidate.name,
                "path": str(candidate),
                "modified_at": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "detail": str(details_by_path.get(str(candidate), details_by_name.get(candidate.name, ""))),
                "mtime": float(mtime),
            }
        )
    rows.sort(key=lambda x: float(x.get("mtime", 0.0)), reverse=True)
    for row in rows:
        row.pop("mtime", None)
    return rows


def has_local_config_versions(
    *,
    local_versions_root: Path,
    device_type_label: str,
    device_name: str,
) -> bool:
    device_dir = _device_versions_dir(
        local_versions_root=Path(local_versions_root),
        device_type_label=device_type_label,
        device_name=device_name,
    )
    try:
        if not device_dir.is_dir():
            return False
    except OSError:
        return False
    try:
        for candidate in device_dir.iterdir():
            try:
                if candidate.is_file() and not candidate.name.startswith("."):
                    return True
            except OSError:
                continue
    except OSError:
        return False
    return False


def delete_local_config_version(
    *,
    local_versions_root: Path,
    device_type_label: str,
    device_name: str,
    filename: str,
) -> bool:
    device_dir = _device_versions_dir(
        local_versions_root=Path(local_versions_root),
        device_type_label=device_type_label,
        device_name=device_name,
    )
    target = device_dir / str(filename or "").strip()
    if not target.is_file():
        return False
    target.unlink(missing_ok=True)
    _config_versions_store().delete_config_file_version(file_path=str(target))
    return True


def rename_local_config_version(
    *,
    local_versions_root: Path,
    device_type_label: str,
    device_name: str,
    filename: str,
    new_filename: str,
) -> Path | None:
    device_dir = _device_versions_dir(
        local_versions_root=Path(local_versions_root),
        device_type_label=device_type_label,
        device_name=device_name,
    )
    source = device_dir / str(filename or "").strip()
    if not source.is_file():
        return None
    clean_name = Path(str(new_filename or "").strip()).name.strip()
    if not clean_name or clean_name in {".", ".."}:
        raise ValueError("Nom de fichier invalide.")
    if source.suffix and Path(clean_name).suffix.lower() != source.suffix.lower():
        clean_name = f"{Path(clean_name).stem}{source.suffix}"
    target = device_dir / clean_name
    if target.exists() and target != source:
        raise FileExistsError(f"Le fichier existe deja: {target.name}")
    source.rename(target)
    store = _config_versions_store()
    updated = store.rename_config_file_version(
        old_file_path=str(source),
        new_file_path=str(target),
        new_filename=target.name,
    )
    if not updated:
        store.upsert_config_file_version(
            file_path=str(target),
            device_type_label=device_type_label,
            device_name=device_name,
            filename=target.name,
            detail="",
        )
    return target
