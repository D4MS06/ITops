from __future__ import annotations

import os
import json
import subprocess
import uuid
import getpass
from pathlib import Path
from types import SimpleNamespace

from monitoring.config.settings import NotificationSettings, _secrets_store
from monitoring.models.storage_target import StorageTarget
from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.utils.config_files import describe_config_remote_mount, ensure_smb3_connection_to_mount


DEFAULT_STORAGE_MOUNT_ROOT = Path("/mnt/itops-storage")
DEFAULT_STORAGE_HELPER = Path("/usr/local/sbin/itops-storage-helper")


class StorageTargetService:
    def __init__(
        self,
        manager: MariaDBFileManager | None = None,
        *,
        settings_provider=None,
    ) -> None:
        self._manager = manager or MariaDBFileManager()
        self._settings_provider = settings_provider

    def list_targets(self, *, service_code: str = "", limit: int = 500) -> list[StorageTarget]:
        return [self._row_to_model(row) for row in self._manager.list_storage_targets(service_code=service_code, limit=limit)]

    def get_target(self, target_id: str) -> StorageTarget | None:
        row = self._manager.get_storage_target(target_id=str(target_id or "").strip())
        return self._row_to_model(row) if row else None

    def upsert_target(
        self,
        *,
        target_id: str = "",
        label: str,
        service_code: str,
        service_label: str,
        kind: str = "smb3",
        remote_path: str,
        username: str = "",
        password: str = "",
        local_mount_path: str = "",
        auto_mount_enabled: bool = True,
    ) -> StorageTarget:
        normalized_id = str(target_id or "").strip() or uuid.uuid4().hex
        normalized_kind = self._normalize_kind(kind)
        normalized_service_code = self._normalize_service_code(service_code)
        normalized_label = str(label or "").strip() or "Stockage distant"
        normalized_remote_path = self._normalize_remote_path(remote_path)
        normalized_mount = str(local_mount_path or "").strip() or self._default_mount_path(
            service_code=normalized_service_code,
            label=normalized_label,
        )
        existing = self.get_target(normalized_id)
        secret_ref = str(existing.secret_ref if existing else "").strip()
        if str(password or "").strip():
            secret_ref = secret_ref or f"storage_target:{normalized_id}"
            _secrets_store().set_or_delete_password(secret_ref, str(password or ""))
        row = self._manager.upsert_storage_target(
            target_id=normalized_id,
            label=normalized_label,
            service_code=normalized_service_code,
            service_label=str(service_label or "").strip() or normalized_service_code,
            kind=normalized_kind,
            remote_path=normalized_remote_path,
            username=str(username or "").strip(),
            secret_ref=secret_ref,
            local_mount_path=normalized_mount,
            auto_mount_enabled=bool(auto_mount_enabled),
            status="configured",
            last_error="",
        )
        return self._row_to_model(row)

    def delete_target(self, target_id: str) -> bool:
        target = self.get_target(target_id)
        if target is not None:
            self._run_storage_helper(
                "remove_mount",
                {
                    "target_id": target.id,
                    "mount_path": target.local_mount_path,
                },
            )
            if target.secret_ref:
                _secrets_store().delete_password(target.secret_ref)
        return bool(self._manager.delete_storage_target(target_id=str(target_id or "").strip()))

    def describe_remote_mounts(self, *, include_legacy_monitoring: bool = True) -> list[dict[str, object]]:
        descriptors = [self._describe_target(target) for target in self.list_targets(limit=2000)]
        if include_legacy_monitoring and self._settings_provider is not None:
            legacy = self._legacy_monitoring_descriptor()
            if legacy is not None:
                descriptors.append(legacy)
        return descriptors

    def test_target(self, target_id: str) -> dict[str, object]:
        target = self.get_target(target_id)
        if target is None:
            raise KeyError("Cible de stockage introuvable.")
        password = _secrets_store().get_password(target.secret_ref) if target.secret_ref else ""
        helper_result = self._ensure_target_with_helper(target, password=password)
        if helper_result is not None:
            ok = bool(helper_result.get("ok"))
            message = str(helper_result.get("message") or "")
        else:
            ok, message = ensure_smb3_connection_to_mount(
                unc=target.remote_path,
                username=target.username,
                password=password,
                mount_dir=target.local_mount_path,
            )
        descriptor = self._describe_target(target)
        descriptor["accessible"] = bool(ok)
        descriptor["mounted"] = bool(ok)
        status = "mounted" if ok else "mount_failed"
        descriptor["status"] = status
        descriptor["message"] = str(message or "")
        if helper_result:
            descriptor["mount_path"] = str(helper_result.get("mount_path") or descriptor.get("mount_path") or "")
            descriptor["target_path"] = str(helper_result.get("target_path") or descriptor.get("target_path") or "")
            descriptor["systemd_unit"] = str(helper_result.get("unit") or "")
            descriptor["systemd_automount_unit"] = str(helper_result.get("automount_unit") or "")
        error = "" if ok else str(message or "")
        self._manager.update_storage_target_status(target_id=target.id, status=status, last_error=error)
        descriptor["last_error"] = error
        return descriptor

    def _ensure_target_with_helper(self, target: StorageTarget, *, password: str) -> dict[str, object] | None:
        return self._run_storage_helper(
            "ensure_smb_mount",
            {
                "target_id": target.id,
                "remote_path": target.remote_path,
                "username": target.username,
                "password": password,
                "mount_path": target.local_mount_path,
                "app_user": str(os.environ.get("NMP_APP_USER") or "").strip() or getpass.getuser(),
            },
        )

    def _run_storage_helper(self, action: str, payload: dict[str, object]) -> dict[str, object] | None:
        if os.name == "nt":
            return None
        helper_path = Path(str(os.environ.get("NMP_STORAGE_HELPER") or DEFAULT_STORAGE_HELPER)).expanduser()
        if not helper_path.is_file():
            return None
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            cmd = [str(helper_path), action]
        else:
            cmd = ["sudo", "-n", str(helper_path), action]
        try:
            proc = subprocess.run(
                cmd,
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                shell=False,
                timeout=45,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "message": f"Helper stockage indisponible: {exc}"}
        try:
            parsed = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            parsed = {}
        if proc.returncode != 0:
            message = str(parsed.get("message") or proc.stderr or proc.stdout or "Helper stockage en echec.").strip()
            return {"ok": False, "message": message}
        if not isinstance(parsed, dict):
            return {"ok": False, "message": "Reponse helper stockage invalide."}
        return parsed

    def _legacy_monitoring_descriptor(self) -> dict[str, object] | None:
        settings = self._settings_provider()
        if not isinstance(settings, NotificationSettings):
            return None
        mode = str(getattr(settings, "config_storage_mode", "local") or "local").strip().lower()
        remote_path = str(getattr(settings, "config_smb_unc_path", "") or "").strip()
        if mode != "smb3" and not remote_path:
            return None
        descriptor = describe_config_remote_mount(
            settings,
            service_code="monitoring.device_config_files",
            service_label="Monitoring - fichiers de configuration",
        )
        descriptor["id"] = "legacy-monitoring-config-storage"
        descriptor["label"] = "Redondance historique monitoring"
        descriptor["managed_by"] = "monitoring_settings"
        return descriptor

    def _describe_target(self, target: StorageTarget) -> dict[str, object]:
        settings = SimpleNamespace(
            config_storage_mode=target.kind,
            config_smb_unc_path=target.remote_path,
            config_smb_username=target.username,
            config_smb_password="",
        )
        descriptor = describe_config_remote_mount(
            settings,
            service_code=target.service_code,
            service_label=target.service_label,
        )
        descriptor.update(
            {
                "id": target.id,
                "label": target.label,
                "kind": target.kind,
                "remote_path": target.remote_path,
                "username": target.username,
                "local_mount_path": target.local_mount_path,
                "auto_mount_enabled": target.auto_mount_enabled,
                "last_error": target.last_error,
                "last_checked_at": target.last_checked_at,
                "managed_by": "storage_targets",
            }
        )
        if target.local_mount_path:
            descriptor["mount_path"] = target.local_mount_path
            descriptor["target_path"] = target.local_mount_path
            try:
                descriptor["accessible"] = Path(target.local_mount_path).is_dir()
            except OSError:
                descriptor["accessible"] = False
        if target.status:
            descriptor["status"] = target.status
        if target.last_error:
            descriptor["message"] = target.last_error
        return descriptor

    @staticmethod
    def _normalize_kind(kind: str) -> str:
        normalized = str(kind or "smb3").strip().lower()
        return "smb3" if normalized in {"smb", "smb3", "cifs"} else "local"

    @staticmethod
    def _normalize_remote_path(remote_path: str) -> str:
        value = str(remote_path or "").strip()
        if os.name != "nt" and value.startswith("//"):
            parts = [part for part in value.split("/") if part]
            if len(parts) >= 2:
                return "\\\\" + "\\".join(parts)
        return value

    @staticmethod
    def _normalize_service_code(service_code: str) -> str:
        raw = str(service_code or "").strip().lower() or "platform.storage"
        return ".".join(
            "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in part).strip("_") or "service"
            for part in raw.split(".")
        )

    @staticmethod
    def _safe_path_part(value: str) -> str:
        raw = str(value or "").strip().lower()
        cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in raw)
        return cleaned.strip("_") or "storage"

    def _default_mount_path(self, *, service_code: str, label: str) -> str:
        root = DEFAULT_STORAGE_MOUNT_ROOT if os.name != "nt" else Path(os.environ.get("LOCALAPPDATA") or str(Path.home())) / "ITops" / "storage-mounts"
        return str(root / self._safe_path_part(service_code) / self._safe_path_part(label))

    @staticmethod
    def _row_to_model(row: dict) -> StorageTarget:
        return StorageTarget(
            id=str(row.get("id", "")),
            label=str(row.get("label", "")),
            service_code=str(row.get("service_code", "")),
            service_label=str(row.get("service_label", "")),
            kind=str(row.get("kind", "smb3")),
            remote_path=str(row.get("remote_path", "")),
            username=str(row.get("username", "")),
            secret_ref=str(row.get("secret_ref", "")),
            local_mount_path=str(row.get("local_mount_path", "")),
            auto_mount_enabled=bool(row.get("auto_mount_enabled", True)),
            status=str(row.get("status", "configured")),
            last_error=str(row.get("last_error", "")),
            last_checked_at=str(row.get("last_checked_at", "")),
            created_at=str(row.get("created_at", "")),
            updated_at=str(row.get("updated_at", "")),
        )
