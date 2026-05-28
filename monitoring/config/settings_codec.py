from __future__ import annotations

from typing import Any


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
        "user": settings.user,
        "use_tls": settings.use_tls,
        "recipients": settings.recipients,
        "offline_delay_seconds": max(1, int(settings.offline_delay_seconds or 5)),
        "online_recovery_delay_seconds": max(
            1, int(getattr(settings, "online_recovery_delay_seconds", settings.offline_delay_seconds) or settings.offline_delay_seconds)
        ),
        "notification_cooldown_seconds": max(0, int(getattr(settings, "notification_cooldown_seconds", 120) or 0)),
        "failures_for_offline": max(1, int(getattr(settings, "failures_for_offline", 3) or 3)),
        "successes_for_online": max(1, int(getattr(settings, "successes_for_online", 2) or 2)),
        "ping_timeout_ms": max(250, int(getattr(settings, "ping_timeout_ms", 1500) or 1500)),
        "probe_interval_ms": max(250, int(getattr(settings, "probe_interval_ms", 1000) or 1000)),
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
        "dashboard_cards_order_json": str(getattr(settings, "dashboard_cards_order_json", "") or "").strip(),
        "dashboard_hidden_cards_json": str(getattr(settings, "dashboard_hidden_cards_json", "") or "").strip(),
        "web_server_host": str(getattr(settings, "web_server_host", "127.0.0.1") or "127.0.0.1").strip() or "127.0.0.1",
        "web_server_port": max(1, int(getattr(settings, "web_server_port", 8000) or 8000)),
        "web_server_autostart": bool(getattr(settings, "web_server_autostart", False)),
        "web_server_public_url": str(getattr(settings, "web_server_public_url", "") or "").strip(),
        "web_server_use_public_url": bool(getattr(settings, "web_server_use_public_url", False)),
        "web_server_reverse_proxy_type": reverse_proxy_type,
    }


def build_notification_settings_kwargs(data: dict[str, object]) -> dict[str, object]:
    offline_delay_seconds = safe_int(data.get("offline_delay_seconds", 5) or 5, 5, minimum=1)
    reverse_proxy_type = str(data.get("web_server_reverse_proxy_type", "aucun") or "aucun").strip().lower()
    if reverse_proxy_type not in {"aucun", "nginx", "caddy"}:
        reverse_proxy_type = "aucun"
    return {
        "log_level": str(data.get("log_level", "INFO") or "INFO").strip().upper(),
        "monitoring_log_level": str(data.get("monitoring_log_level", "INFO") or "INFO").strip().upper(),
        "ui_log_level": str(data.get("ui_log_level", "ERROR") or "ERROR").strip().upper(),
        "smtp_host": str(data.get("smtp_host", "")).strip(),
        "smtp_port": int(data.get("smtp_port", 0) or 0),
        "user": str(data.get("user", "")).strip(),
        "use_tls": bool(data.get("use_tls", False)),
        "recipients": str(data.get("recipients", "")).strip(),
        "offline_delay_seconds": offline_delay_seconds,
        "online_recovery_delay_seconds": safe_int(
            data.get("online_recovery_delay_seconds", offline_delay_seconds) or offline_delay_seconds,
            offline_delay_seconds,
            minimum=1,
        ),
        "notification_cooldown_seconds": safe_int(
            data.get("notification_cooldown_seconds", 120) or 0,
            120,
            minimum=0,
        ),
        "failures_for_offline": safe_int(data.get("failures_for_offline", 3) or 3, 3, minimum=1),
        "successes_for_online": safe_int(data.get("successes_for_online", 2) or 2, 2, minimum=1),
        "ping_timeout_ms": safe_int(data.get("ping_timeout_ms", 1500) or 1500, 1500, minimum=250),
        "probe_interval_ms": safe_int(data.get("probe_interval_ms", 1000) or 1000, 1000, minimum=250),
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
        "dashboard_cards_order_json": str(data.get("dashboard_cards_order_json", "") or "").strip(),
        "dashboard_hidden_cards_json": str(data.get("dashboard_hidden_cards_json", "") or "").strip(),
        "web_server_host": str(data.get("web_server_host", "127.0.0.1") or "127.0.0.1").strip() or "127.0.0.1",
        "web_server_port": max(1, int(data.get("web_server_port", 8000) or 8000)),
        "web_server_autostart": bool(data.get("web_server_autostart", False)),
        "web_server_public_url": str(data.get("web_server_public_url", "") or "").strip(),
        "web_server_use_public_url": bool(data.get("web_server_use_public_url", False)),
        "web_server_reverse_proxy_type": reverse_proxy_type,
    }
