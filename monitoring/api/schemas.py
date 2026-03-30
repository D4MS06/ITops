from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


class BootstrapPasswordRequest(BaseModel):
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str


class MessageResponse(BaseModel):
    message: str


class AuthStatusResponse(BaseModel):
    has_admin_password: bool


class SessionInfoResponse(BaseModel):
    subject: str
    expires_at: str


class ModuleAccessResponse(BaseModel):
    code: str
    label: str
    route_path: str
    is_active: bool = True
    granted: bool = False


class DevicePayload(BaseModel):
    name: str
    ip: str
    description: str = ""
    id_Teamviewer: str = ""
    device_subtype: str = ""
    action_double_click: str = ""
    web_url: str = ""
    ssh_user: str = ""
    custom_data: dict[str, str] = Field(default_factory=dict)
    notify: bool = True


class DeviceCreateRequest(DevicePayload):
    device_type: str


class DeviceUpdateRequest(DevicePayload):
    pass


class DeviceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    ip: str
    description: str
    notify: bool
    id_Teamviewer: str = ""
    type: str = ""
    action_double_click: str = ""
    web_url: str = ""
    ssh_user: str = ""
    custom_data: dict[str, str] = Field(default_factory=dict)
    device_type: str
    has_saved_config: bool = False


class DeviceTypeResponse(BaseModel):
    code: str
    label: str
    icon: str = ""
    monitoring_enabled: bool = True
    config_backups_enabled: Optional[bool] = None
    is_system: bool = False
    sort_order: int = 0


class DeviceTypeSchemaResponse(BaseModel):
    fields: list[dict]
    actions: list[dict]


class DeviceTypeCreateRequest(BaseModel):
    label: str
    monitoring_enabled: bool = True
    config_backups_enabled: Optional[bool] = None


class DeviceTypeUpdateRequest(BaseModel):
    label: str
    monitoring_enabled: bool = True
    config_backups_enabled: Optional[bool] = None


class StatusLogResponse(BaseModel):
    created_at: str
    dtype: str
    device_id: str
    device_name: str
    old_status: str
    new_status: str
    event_kind: str
    details: str


class NetworkToolResponse(BaseModel):
    ok: bool
    output: str


class NetworkToolPingRequest(BaseModel):
    ip: str = Field(min_length=1)


class NetworkToolTracerouteRequest(BaseModel):
    ip: str = Field(min_length=1)


class NetworkToolDnsLookupRequest(BaseModel):
    target: str = Field(min_length=1)


class NetworkToolPortCheckRequest(BaseModel):
    ip: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    timeout_seconds: float = Field(default=2.0, ge=0.2, le=20.0)


class NetworkToolHttpCheckRequest(BaseModel):
    url: str = Field(min_length=1)


class NetworkToolSnmpCheckRequest(BaseModel):
    ip: str = Field(min_length=1)
    community: str = Field(min_length=1)
    oid: str = Field(min_length=1)


class NetworkScanRequest(BaseModel):
    mode: str = Field(default="vlan")
    vlan: int = Field(default=1, ge=0, le=255)
    start_ip: str = ""
    end_ip: str = ""
    allow_vendor_online: bool = False
    timeout_ms: int = Field(default=800, ge=100, le=5000)
    max_workers: int = Field(default=16, ge=4, le=128)


class NetworkScanRowResponse(BaseModel):
    ip: str
    hostname: str = ""
    vendor: str = ""
    mac: str = ""
    status: str = ""


class MonitoringTypeStateResponse(BaseModel):
    type_code: str
    label: str
    monitoring_enabled: bool
    config_backups_enabled: Optional[bool] = None
    running: bool
    total: int
    online: int
    offline: int
    idle: int


class MonitoringSummaryResponse(BaseModel):
    running_types: list[str]
    monitored_types: list[str]
    running_any: bool
    running_all: bool
    total: int
    online: int
    offline: int
    idle: int


class MonitoringSnapshotResponse(BaseModel):
    summary: MonitoringSummaryResponse
    types: list[MonitoringTypeStateResponse]
    devices: dict[str, list[dict]]


class MonitoringCapabilitiesResponse(BaseModel):
    websocket_supported: bool
    recommended_transport: str


class UiConfigResponse(BaseModel):
    app_version: str
    ui_theme: str
    theme_colors: dict[str, str]
    watermark_enabled: bool
    watermark_opacity: float
    watermark_url: str = ""


class ConfigFileResponse(BaseModel):
    name: str
    path: str
    modified_at: str
    detail: str = ""


class ConfigStorageStateResponse(BaseModel):
    mode: str
    can_open_backup_folder: bool
    has_smb_password: bool = False
    message: str = ""


class ConfigFileImportRequest(BaseModel):
    device_type: str
    device_name: str
    filename: str = "import.cfg"
    content_base64: str
    detail: str = ""


class SettingsResponse(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 0
    user: str = ""
    use_tls: bool = False
    recipients: str = ""
    offline_delay_seconds: int = 5
    online_recovery_delay_seconds: int = 5
    notification_cooldown_seconds: int = 120
    failures_for_offline: int = 3
    successes_for_online: int = 2
    ping_timeout_ms: int = 1500
    probe_interval_ms: int = 1000
    log_diagnostic_events: bool = False
    show_status_popup: bool = True
    updates_enabled: bool = False
    github_owner: str = ""
    github_repo: str = ""
    include_prerelease: bool = False
    update_target_tag: str = "latest"
    updates_connection_validated: bool = False
    watermark_image_path: str = ""
    watermark_source_path: str = ""
    watermark_opacity: float = 0.16
    ui_theme: str = "light"
    theme_overrides_json: str = ""
    status_indicator_style: str = "badge"
    switch_configs_dir: str = ""
    config_storage_mode: str = "local"
    config_smb_unc_path: str = ""
    config_smb_username: str = ""
    config_auto_sync_enabled: bool = False
    config_auto_sync_interval_seconds: int = 3600
    dashboard_cards_order_json: str = ""
    dashboard_hidden_cards_json: str = ""
    web_server_host: str = "127.0.0.1"
    web_server_port: int = 8000
    web_server_autostart: bool = False
    web_server_public_url: str = ""
    web_server_use_public_url: bool = False


class SettingsUpdateRequest(SettingsResponse):
    pass
