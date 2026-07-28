from __future__ import annotations

from typing import Any


LEGACY_MONITORING_DEFAULTS = {
    "offline_delay_seconds": 5,
    "online_recovery_delay_seconds": 5,
    "failures_for_offline": 3,
    "successes_for_online": 2,
    "ping_timeout_ms": 1500,
    "probe_interval_ms": 1000,
}
RECOMMENDED_MONITORING_DEFAULTS = {
    "offline_delay_seconds": 20,
    "online_recovery_delay_seconds": 10,
    "failures_for_offline": 5,
    "successes_for_online": 3,
    "ping_timeout_ms": 2500,
    "probe_interval_ms": 2000,
}


def safe_int(value: object, default: int, minimum: int | None = None) -> int:
    try:
        result = int(value if value is not None else default)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    return result


def safe_float(
    value: object,
    default: float,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        result = float(value if value is not None else default)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def build_settings_payload(settings: Any) -> dict[str, object]:
    reverse_proxy_type = str(getattr(settings, "web_server_reverse_proxy_type", "aucun") or "aucun").strip().lower()
    if reverse_proxy_type not in {"aucun", "nginx", "caddy"}:
        reverse_proxy_type = "aucun"
    return {
        "log_level": str(getattr(settings, "log_level", "INFO") or "INFO").strip().upper(),
        "monitoring_log_level": str(getattr(settings, "monitoring_log_level", "INFO") or "INFO").strip().upper(),
        "ui_log_level": str(getattr(settings, "ui_log_level", "ERROR") or "ERROR").strip().upper(),
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_auth_enabled": bool(getattr(settings, "smtp_auth_enabled", False)),
        "user": settings.user,
        "use_tls": settings.use_tls,
        "recipients": settings.recipients,
        "offline_delay_seconds": max(1, int(settings.offline_delay_seconds or 20)),
        "online_recovery_delay_seconds": max(
            1, int(getattr(settings, "online_recovery_delay_seconds", 10) or 10)
        ),
        "notification_cooldown_seconds": max(0, int(getattr(settings, "notification_cooldown_seconds", 120) or 0)),
        "monitoring_notify_on_outage": bool(getattr(settings, "monitoring_notify_on_outage", True)),
        "monitoring_notify_on_recovery": bool(getattr(settings, "monitoring_notify_on_recovery", True)),
        "monitoring_notification_subject_template": str(
            getattr(
                settings,
                "monitoring_notification_subject_template",
                "[Monitoring] {device_type} {device_name}: {old_status} -> {new_status}",
            ) or ""
        ).strip(),
        "monitoring_notification_body_template": str(
            getattr(
                settings,
                "monitoring_notification_body_template",
                "Equipement: {device_name}\nType: {device_type}\nIP: {device_ip}\nStatut: {old_status} -> {new_status}",
            ) or ""
        ).strip(),
        "failures_for_offline": max(1, int(getattr(settings, "failures_for_offline", 5) or 5)),
        "successes_for_online": max(1, int(getattr(settings, "successes_for_online", 3) or 3)),
        "ping_timeout_ms": max(250, int(getattr(settings, "ping_timeout_ms", 2500) or 2500)),
        "probe_interval_ms": max(250, int(getattr(settings, "probe_interval_ms", 2000) or 2000)),
        "credential_reveal_unlock_seconds": max(
            30,
            min(3600, int(getattr(settings, "credential_reveal_unlock_seconds", 300) or 300)),
        ),
        "log_diagnostic_events": bool(getattr(settings, "log_diagnostic_events", False)),
        "show_status_popup": bool(settings.show_status_popup),
        "updates_enabled": bool(getattr(settings, "updates_enabled", False)),
        "github_owner": str(getattr(settings, "github_owner", "") or "").strip(),
        "github_repo": str(getattr(settings, "github_repo", "") or "").strip(),
        "include_prerelease": bool(getattr(settings, "include_prerelease", False)),
        "update_target_tag": str(getattr(settings, "update_target_tag", "latest") or "latest").strip(),
        "updates_connection_validated": bool(getattr(settings, "updates_connection_validated", False)),
        "watermark_image_path": str(getattr(settings, "watermark_image_path", "") or "").strip(),
        "watermark_source_path": str(getattr(settings, "watermark_source_path", "") or "").strip(),
        "watermark_opacity": min(1.0, max(0.0, float(getattr(settings, "watermark_opacity", 0.16) or 0.16))),
        "watermark_offset_x": int(getattr(settings, "watermark_offset_x", 0) or 0),
        "watermark_offset_y": int(getattr(settings, "watermark_offset_y", 0) or 0),
        "watermark_zoom_percent": max(40, min(220, int(getattr(settings, "watermark_zoom_percent", 100) or 100))),
        "ui_theme": str(getattr(settings, "ui_theme", "light") or "light").strip().lower(),
        "theme_overrides_json": str(getattr(settings, "theme_overrides_json", "") or "").strip(),
        "status_indicator_style": str(getattr(settings, "status_indicator_style", "badge") or "badge").strip().lower(),
        "switch_configs_dir": str(getattr(settings, "switch_configs_dir", "") or "").strip(),
        "config_storage_mode": str(getattr(settings, "config_storage_mode", "local") or "local").strip().lower(),
        "config_smb_unc_path": str(getattr(settings, "config_smb_unc_path", "") or "").strip(),
        "config_smb_username": str(getattr(settings, "config_smb_username", "") or "").strip(),
        "config_auto_sync_enabled": bool(getattr(settings, "config_auto_sync_enabled", False)),
        "config_auto_sync_interval_seconds": max(
            5, int(getattr(settings, "config_auto_sync_interval_seconds", 3600) or 3600)
        ),
        "active_directory_enabled": bool(getattr(settings, "active_directory_enabled", False)),
        "active_directory_host": str(getattr(settings, "active_directory_host", "") or "").strip(),
        "active_directory_port": max(1, min(65535, int(getattr(settings, "active_directory_port", 636) or 636))),
        "active_directory_use_ssl": bool(getattr(settings, "active_directory_use_ssl", True)),
        "active_directory_validate_certificates": bool(getattr(settings, "active_directory_validate_certificates", True)),
        "active_directory_ca_certificate_path": str(getattr(settings, "active_directory_ca_certificate_path", "") or "").strip(),
        "active_directory_ca_certificate_file_id": str(getattr(settings, "active_directory_ca_certificate_file_id", "") or "").strip(),
        "active_directory_bind_username": str(getattr(settings, "active_directory_bind_username", "") or "").strip(),
        "active_directory_base_dn": str(getattr(settings, "active_directory_base_dn", "") or "").strip(),
        "active_directory_user_filter": str(getattr(settings, "active_directory_user_filter", "") or "").strip() or "(&(objectCategory=person)(objectClass=user))",
        "active_directory_sync_interval_seconds": max(60, int(getattr(settings, "active_directory_sync_interval_seconds", 3600) or 3600)),
        "active_directory_sync_email_accounts": bool(getattr(settings, "active_directory_sync_email_accounts", False)),
        "web_server_host": str(getattr(settings, "web_server_host", "127.0.0.1") or "127.0.0.1").strip() or "127.0.0.1",
        "web_server_port": max(1, int(getattr(settings, "web_server_port", 8000) or 8000)),
        "web_server_autostart": bool(getattr(settings, "web_server_autostart", False)),
        "web_server_public_url": str(getattr(settings, "web_server_public_url", "") or "").strip(),
        "web_server_use_public_url": bool(getattr(settings, "web_server_use_public_url", False)),
        "web_server_reverse_proxy_type": reverse_proxy_type,
        "web_session_ttl_seconds": max(300, int(getattr(settings, "web_session_ttl_seconds", 3600) or 3600)),
        "web_revoke_sessions_on_startup": bool(getattr(settings, "web_revoke_sessions_on_startup", True)),
    }


def build_notification_settings_kwargs(data: dict[str, object]) -> dict[str, object]:
    monitoring_values = _monitoring_settings_from_payload(data)
    offline_delay_seconds = monitoring_values["offline_delay_seconds"]
    reverse_proxy_type = str(data.get("web_server_reverse_proxy_type", "aucun") or "aucun").strip().lower()
    if reverse_proxy_type not in {"aucun", "nginx", "caddy"}:
        reverse_proxy_type = "aucun"
    return {
        "log_level": str(data.get("log_level", "INFO") or "INFO").strip().upper(),
        "monitoring_log_level": str(data.get("monitoring_log_level", "INFO") or "INFO").strip().upper(),
        "ui_log_level": str(data.get("ui_log_level", "ERROR") or "ERROR").strip().upper(),
        "smtp_host": str(data.get("smtp_host", "")).strip(),
        "smtp_port": int(data.get("smtp_port", 0) or 0),
        "smtp_auth_enabled": bool(data.get("smtp_auth_enabled", False)),
        "user": str(data.get("user", "")).strip(),
        "use_tls": bool(data.get("use_tls", False)),
        "recipients": str(data.get("recipients", "")).strip(),
        "offline_delay_seconds": offline_delay_seconds,
        "online_recovery_delay_seconds": monitoring_values["online_recovery_delay_seconds"],
        "notification_cooldown_seconds": safe_int(
            data.get("notification_cooldown_seconds", 120) or 0,
            120,
            minimum=0,
        ),
        "monitoring_notify_on_outage": bool(data.get("monitoring_notify_on_outage", True)),
        "monitoring_notify_on_recovery": bool(data.get("monitoring_notify_on_recovery", True)),
        "monitoring_notification_subject_template": str(
            data.get(
                "monitoring_notification_subject_template",
                "[Monitoring] {device_type} {device_name}: {old_status} -> {new_status}",
            ) or ""
        ).strip(),
        "monitoring_notification_body_template": str(
            data.get(
                "monitoring_notification_body_template",
                "Equipement: {device_name}\nType: {device_type}\nIP: {device_ip}\nStatut: {old_status} -> {new_status}",
            ) or ""
        ).strip(),
        "failures_for_offline": monitoring_values["failures_for_offline"],
        "successes_for_online": monitoring_values["successes_for_online"],
        "ping_timeout_ms": monitoring_values["ping_timeout_ms"],
        "probe_interval_ms": monitoring_values["probe_interval_ms"],
        "credential_reveal_unlock_seconds": min(
            3600,
            safe_int(data.get("credential_reveal_unlock_seconds", 300) or 300, 300, minimum=30),
        ),
        "log_diagnostic_events": bool(data.get("log_diagnostic_events", False)),
        "show_status_popup": bool(data.get("show_status_popup", True)),
        "updates_enabled": bool(data.get("updates_enabled", False)),
        "github_owner": str(data.get("github_owner", "D4MS06")).strip(),
        "github_repo": str(data.get("github_repo", "NetworkMonitoringProject")).strip(),
        "include_prerelease": bool(data.get("include_prerelease", False)),
        "update_target_tag": str(data.get("update_target_tag", "latest") or "latest").strip(),
        "updates_connection_validated": bool(data.get("updates_connection_validated", False)),
        "watermark_image_path": str(data.get("watermark_image_path", "")).strip(),
        "watermark_source_path": str(data.get("watermark_source_path", "")).strip(),
        "watermark_opacity": safe_float(data.get("watermark_opacity", 0.16) or 0.16, 0.16, minimum=0.0, maximum=1.0),
        "watermark_offset_x": safe_int(data.get("watermark_offset_x", 0) or 0, 0),
        "watermark_offset_y": safe_int(data.get("watermark_offset_y", 0) or 0, 0),
        "watermark_zoom_percent": min(220, safe_int(data.get("watermark_zoom_percent", 100) or 100, 100, minimum=40)),
        "ui_theme": str(data.get("ui_theme", "light") or "light").strip().lower(),
        "theme_overrides_json": str(data.get("theme_overrides_json", "") or "").strip(),
        "status_indicator_style": str(data.get("status_indicator_style", "badge") or "badge").strip().lower(),
        "switch_configs_dir": str(data.get("switch_configs_dir", "") or "").strip(),
        "config_storage_mode": str(data.get("config_storage_mode", "local") or "local").strip().lower(),
        "config_smb_unc_path": str(data.get("config_smb_unc_path", "") or "").strip(),
        "config_smb_username": str(data.get("config_smb_username", "") or "").strip(),
        "config_auto_sync_enabled": bool(data.get("config_auto_sync_enabled", False)),
        "config_auto_sync_interval_seconds": safe_int(
            data.get("config_auto_sync_interval_seconds", 3600) or 3600,
            3600,
            minimum=5,
        ),
        "active_directory_enabled": bool(data.get("active_directory_enabled", False)),
        "active_directory_host": str(data.get("active_directory_host", "") or "").strip(),
        "active_directory_port": min(65535, safe_int(data.get("active_directory_port", 636) or 636, 636, minimum=1)),
        "active_directory_use_ssl": bool(data.get("active_directory_use_ssl", True)),
        "active_directory_validate_certificates": bool(data.get("active_directory_validate_certificates", True)),
        "active_directory_ca_certificate_path": str(data.get("active_directory_ca_certificate_path", "") or "").strip(),
        "active_directory_ca_certificate_file_id": str(data.get("active_directory_ca_certificate_file_id", "") or "").strip(),
        "active_directory_bind_username": str(data.get("active_directory_bind_username", "") or "").strip(),
        "active_directory_base_dn": str(data.get("active_directory_base_dn", "") or "").strip(),
        "active_directory_user_filter": str(data.get("active_directory_user_filter", "") or "").strip() or "(&(objectCategory=person)(objectClass=user))",
        "active_directory_sync_interval_seconds": safe_int(data.get("active_directory_sync_interval_seconds", 3600) or 3600, 3600, minimum=60),
        "active_directory_sync_email_accounts": bool(data.get("active_directory_sync_email_accounts", False)),
        "web_server_host": str(data.get("web_server_host", "127.0.0.1") or "127.0.0.1").strip() or "127.0.0.1",
        "web_server_port": max(1, int(data.get("web_server_port", 8000) or 8000)),
        "web_server_autostart": bool(data.get("web_server_autostart", False)),
        "web_server_public_url": str(data.get("web_server_public_url", "") or "").strip(),
        "web_server_use_public_url": bool(data.get("web_server_use_public_url", False)),
        "web_server_reverse_proxy_type": reverse_proxy_type,
        "web_session_ttl_seconds": safe_int(data.get("web_session_ttl_seconds", 3600) or 3600, 3600, minimum=300),
        "web_revoke_sessions_on_startup": bool(data.get("web_revoke_sessions_on_startup", True)),
    }


def _monitoring_settings_from_payload(data: dict[str, object]) -> dict[str, int]:
    values = {
        key: safe_int(data.get(key, default) or default, default, minimum=1 if not key.endswith("_ms") else 250)
        for key, default in RECOMMENDED_MONITORING_DEFAULTS.items()
    }
    has_all_legacy_keys = all(key in data for key in LEGACY_MONITORING_DEFAULTS)
    if has_all_legacy_keys and values == LEGACY_MONITORING_DEFAULTS:
        return dict(RECOMMENDED_MONITORING_DEFAULTS)
    return values
