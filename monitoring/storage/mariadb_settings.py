from __future__ import annotations

import json
from dataclasses import replace
from typing import Callable

from monitoring.config.settings import (
    ACTIVE_DIRECTORY_PASSWORD_ACCOUNT,
    CONFIG_SMB_PASSWORD_ACCOUNT,
    NotificationSettings,
    UPDATER_TOKEN_ACCOUNT,
    _secrets_store,
    load_settings,
)
from monitoring.config.settings_codec import build_notification_settings_kwargs, build_settings_payload


class MariaDBSettingsStore:
    SETTINGS_KEY = "notification_settings"

    def __init__(
        self,
        manager,
        *,
        fallback_loader: Callable[[], NotificationSettings] = load_settings,
    ) -> None:
        self._manager = manager
        self._fallback_loader = fallback_loader

    def load(self) -> NotificationSettings:
        payload = self._load_payload()
        if payload is None:
            migrated = self._fallback_loader()
            self.save(migrated)
            return replace(migrated)

        kwargs = build_notification_settings_kwargs(payload)
        secrets = _secrets_store()
        user = str(kwargs.get("user", "") or "").strip()
        kwargs["password"] = secrets.get_password(user) if user else ""
        kwargs["github_token"] = secrets.get_password(UPDATER_TOKEN_ACCOUNT)
        kwargs["config_smb_password"] = secrets.get_password(CONFIG_SMB_PASSWORD_ACCOUNT)
        kwargs["active_directory_bind_password"] = secrets.get_password(ACTIVE_DIRECTORY_PASSWORD_ACCOUNT)
        return NotificationSettings(**kwargs)

    def save(self, settings: NotificationSettings) -> None:
        previous_user = ""
        previous_payload = self._load_payload()
        if previous_payload is not None:
            previous_user = str(previous_payload.get("user", "") or "").strip()

        updated = replace(settings)
        self._save_payload(build_settings_payload(updated))

        secrets = _secrets_store()
        if previous_user and previous_user != updated.user:
            secrets.delete_password(previous_user)

        if updated.user and updated.password:
            secrets.set_or_delete_password(updated.user, updated.password)
        elif previous_user:
            secrets.delete_password(previous_user)

        token = str(getattr(updated, "github_token", "") or "").strip()
        secrets.set_or_delete_password(UPDATER_TOKEN_ACCOUNT, token)
        smb_password = str(getattr(updated, "config_smb_password", "") or "").strip()
        secrets.set_or_delete_password(CONFIG_SMB_PASSWORD_ACCOUNT, smb_password)
        ad_password = str(getattr(updated, "active_directory_bind_password", "") or "")
        if ad_password:
            secrets.set_or_delete_password(ACTIVE_DIRECTORY_PASSWORD_ACCOUNT, ad_password)

    def _load_payload(self) -> dict[str, object] | None:
        self._manager._ensure_database()
        with self._manager._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT payload_json FROM app_settings WHERE setting_key = %s",
                    (self.SETTINGS_KEY,),
                )
                row = cursor.fetchone()
        if not row:
            return None
        try:
            payload = json.loads(str(row[0] or "{}"))
        except Exception:
            payload = {}
        return payload if isinstance(payload, dict) else {}

    def _save_payload(self, payload: dict[str, object]) -> None:
        self._manager._ensure_database()
        serialized = json.dumps(dict(payload or {}), ensure_ascii=False)
        with self._manager._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_settings(setting_key, payload_json)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE
                        payload_json = VALUES(payload_json),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (self.SETTINGS_KEY, serialized),
                )
            conn.commit()
