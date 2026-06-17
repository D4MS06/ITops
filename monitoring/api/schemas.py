from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(default="sa", min_length=1)
    password: str = Field(min_length=1)
    new_password: Optional[str] = None


class BootstrapPasswordRequest(BaseModel):
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str


class MessageResponse(BaseModel):
    message: str
    redirect_url: str = ""


class AuthStatusResponse(BaseModel):
    has_admin_password: bool
    first_start_required: bool = False


class SetupStatusResponse(BaseModel):
    setup_required: bool = True
    setup_completed: bool = False
    has_setup_token: bool = False
    has_admin_password: bool = False
    app_version: str = ""
    hebergement_config_path: str = ""
    install_env_path: str = ""
    server_access_host: str = ""
    server_hint_ip: str = ""


class SetupFinalizeRequest(BaseModel):
    setup_token: str = ""
    admin_password: str = Field(min_length=8)
    hote_ecoute: str = "0.0.0.0"
    port_ecoute: int = Field(default=8080, ge=1, le=65535)
    reverse_proxy_type: str = "aucun"
    url_publique: str = ""
    db_host: str = "127.0.0.1"
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_user: str = "itops"
    db_password: str = ""
    db_name: str = "itops"
    mariadb_root_password: str = Field(min_length=8)


class SessionInfoResponse(BaseModel):
    subject: str
    expires_at: str


class SessionProfileResponse(BaseModel):
    subject: str
    label: str = ""
    role_code: str = ""
    role_label: str = ""


class ModuleAccessResponse(BaseModel):
    code: str
    label: str
    route_path: str
    is_active: bool = True
    granted: bool = False


class SessionContextResponse(BaseModel):
    subject: str
    label: str = ""
    role_code: str = ""
    role_label: str = ""
    modules: list[ModuleAccessResponse] = Field(default_factory=list)


class AdminModuleResponse(BaseModel):
    code: str
    label: str
    route_path: str
    is_active: bool = True
    sort_order: int = 0


class AdminModuleActivationRequest(BaseModel):
    is_active: bool = True


class AdminRoleResponse(BaseModel):
    code: str
    label: str
    is_system: bool = False
    sort_order: int = 0
    module_codes: list[str] = Field(default_factory=list)
    version_token: str = ""


class AdminRoleUpsertRequest(BaseModel):
    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    module_codes: list[str] = Field(default_factory=list)
    is_system: bool = False
    sort_order: int = 0
    version_token: str = ""


class AdminUserResponse(BaseModel):
    subject: str
    label: str
    is_active: bool = True
    must_change_password: bool = False
    role_codes: list[str] = Field(default_factory=list)
    version_token: str = ""


class AdminUserCreateRequest(BaseModel):
    subject: str = Field(min_length=1)
    label: str = ""
    password: str = Field(min_length=1)
    is_active: bool = True
    must_change_password: bool = False
    role_codes: list[str] = Field(default_factory=list)


class AdminUserUpdateRequest(BaseModel):
    label: str = ""
    password: str = ""
    is_active: bool = True
    must_change_password: bool = False
    role_codes: list[str] = Field(default_factory=list)
    version_token: str = ""


class CustomServiceFieldResponse(BaseModel):
    field_key: str
    label: str
    field_kind: str = "text"
    required: bool = False
    options: str = ""
    default_value: str = ""
    sort_order: int = 0
    list_source_kind: str = "local"
    shared_list_code: str = ""


class SharedListResponse(BaseModel):
    code: str
    label: str
    is_system: bool = False
    sort_order: int = 0
    item_count: int = 0
    version_token: str = ""


class SharedListUpsertRequest(BaseModel):
    code: str = ""
    label: str = Field(min_length=1)
    is_system: bool = False
    sort_order: int = 100
    version_token: str = ""


class SharedListItemResponse(BaseModel):
    list_code: str
    code: str
    label: str
    is_active: bool = True
    sort_order: int = 0
    version_token: str = ""


class SharedListItemUpsertRequest(BaseModel):
    code: str = ""
    label: str = Field(min_length=1)
    is_active: bool = True
    sort_order: int = 100
    version_token: str = ""


class SharedListItemImportRow(BaseModel):
    code: str
    label: str
    is_active: bool = True
    sort_order: int = 0


class SharedListImportResponse(BaseModel):
    items: list[SharedListItemImportRow] = Field(default_factory=list)
    detected_rows: int = 0
    detected_columns: int = 0
    source_headers: list[str] = Field(default_factory=list)
    source_rows_preview: list[list[str]] = Field(default_factory=list)
    available_sheets: list[str] = Field(default_factory=list)
    selected_sheet_name: str = ""
    detected_header_row_number: int = 1
    effective_header_mode: str = "auto"


class CustomServiceResponse(BaseModel):
    code: str
    label: str
    is_active: bool = True
    credentials_enabled: bool = False
    child_enabled: bool = False
    child_label: str = "Elements lies"
    sort_order: int = 0
    fields: list[CustomServiceFieldResponse] = Field(default_factory=list)
    version_token: str = ""


class CustomServiceUpsertRequest(BaseModel):
    code: str = ""
    label: str = Field(min_length=1)
    is_active: bool = True
    credentials_enabled: bool = False
    child_enabled: bool = False
    child_label: str = "Elements lies"
    sort_order: int = 100
    fields: list[dict] = Field(default_factory=list)
    version_token: str = ""


class CustomServiceImportRequest(BaseModel):
    filename: str = ""
    content_base64: str = Field(min_length=1)
    sheet_name: str = ""
    header_mode: str = "auto"
    header_row_number: int = 1


class CustomServiceImportResponse(BaseModel):
    fields: list[CustomServiceFieldResponse] = Field(default_factory=list)
    detected_rows: int = 0
    detected_columns: int = 0
    source_headers: list[str] = Field(default_factory=list)
    source_rows_preview: list[list[str]] = Field(default_factory=list)
    available_sheets: list[str] = Field(default_factory=list)
    selected_sheet_name: str = ""
    detected_header_row_number: int = 1
    effective_header_mode: str = "auto"


class CustomServiceRecordImportRequest(BaseModel):
    filename: str = ""
    content_base64: str = Field(min_length=1)
    upsert_existing: bool = True
    credential_mode: str = "preserve_on_blank"
    sheet_name: str = ""
    header_mode: str = "auto"
    header_row_number: int = 1


class CustomServiceRecordImportPreviewRow(BaseModel):
    record_id: str = ""
    values: dict[str, str] = Field(default_factory=dict)
    children: list[dict] = Field(default_factory=list)


class CustomServiceRecordImportPreviewResponse(BaseModel):
    rows: list[CustomServiceRecordImportPreviewRow] = Field(default_factory=list)
    detected_rows: int = 0
    detected_columns: int = 0
    issues: list[str] = Field(default_factory=list)
    source_headers: list[str] = Field(default_factory=list)
    source_rows_preview: list[list[str]] = Field(default_factory=list)
    available_sheets: list[str] = Field(default_factory=list)
    selected_sheet_name: str = ""
    detected_header_row_number: int = 1
    effective_header_mode: str = "auto"


class CustomServiceRecordImportApplyResponse(BaseModel):
    processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    issues: list[str] = Field(default_factory=list)


class DeviceImportRequest(BaseModel):
    filename: str = ""
    content_base64: str = Field(min_length=1)
    default_device_type: str = ""
    upsert_existing: bool = True
    column_mappings: list[dict] = Field(default_factory=list)
    credential_mode: str = "preserve_on_blank"
    sheet_name: str = ""
    header_mode: str = "auto"
    header_row_number: int = 1


class DeviceImportColumnMappingResponse(BaseModel):
    source_column: str
    target_field: str = ""
    custom_key: str = ""


class DeviceImportPreviewRow(BaseModel):
    device_type: str
    name: str
    ip: str
    description: str = ""
    id_Teamviewer: str = ""
    device_subtype: str = ""
    action_double_click: str = ""
    web_url: str = ""
    ssh_user: str = ""
    device_login: str = ""
    device_password: str = ""
    notify: bool = True
    custom_data: dict[str, str] = Field(default_factory=dict)


class DeviceImportPreviewResponse(BaseModel):
    rows: list[DeviceImportPreviewRow] = Field(default_factory=list)
    detected_rows: int = 0
    detected_columns: int = 0
    issues: list[str] = Field(default_factory=list)
    source_headers: list[str] = Field(default_factory=list)
    source_rows_preview: list[list[str]] = Field(default_factory=list)
    available_sheets: list[str] = Field(default_factory=list)
    selected_sheet_name: str = ""
    detected_header_row_number: int = 1
    effective_header_mode: str = "auto"
    effective_mapping: list[DeviceImportColumnMappingResponse] = Field(default_factory=list)


class DeviceImportApplyResponse(BaseModel):
    processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    issues: list[str] = Field(default_factory=list)


class CustomServiceRecordChildRequest(BaseModel):
    name: str = ""
    code: str = ""
    sort_order: int = 0


class CustomServiceRecordChildResponse(BaseModel):
    id: str = ""
    name: str
    code: str
    sort_order: int = 0


class CustomServiceRecordUpsertRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)
    children: list[CustomServiceRecordChildRequest] = Field(default_factory=list)
    version_token: str = ""


class CustomServiceRecordResponse(BaseModel):
    id: str
    service_code: str
    values: dict[str, str] = Field(default_factory=dict)
    children: list[CustomServiceRecordChildResponse] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    version_token: str = ""


class DevicePayload(BaseModel):
    name: str
    ip: str
    description: str = ""
    id_Teamviewer: str = ""
    device_subtype: str = ""
    action_double_click: str = ""
    web_url: str = ""
    ssh_user: str = ""
    device_login: Optional[str] = None
    device_password: Optional[str] = None
    custom_data: dict[str, str] = Field(default_factory=dict)
    notify: bool = True
    version_token: str = ""


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
    device_subtype: str = ""
    action_double_click: str = ""
    web_url: str = ""
    ssh_user: str = ""
    device_login: str = ""
    has_device_password: bool = False
    device_password_masked: str = ""
    custom_data: dict[str, str] = Field(default_factory=dict)
    device_type: str
    has_saved_config: bool = False
    version_token: str = ""


class DeviceCredentialRevealRequest(BaseModel):
    session_password: str = Field(min_length=1)


class DeviceCredentialRevealResponse(BaseModel):
    device_login: str = ""
    device_password: str = ""


class DeviceTypeResponse(BaseModel):
    code: str
    label: str
    icon: str = ""
    monitoring_enabled: bool = True
    config_backups_enabled: Optional[bool] = None
    credentials_enabled: bool = False
    is_system: bool = False
    sort_order: int = 0
    version_token: str = ""


class DeviceTypeSchemaResponse(BaseModel):
    fields: list[dict]
    actions: list[dict]
    version_token: str = ""


class DeviceTypeSchemaUpdateRequest(BaseModel):
    fields: list[dict] = Field(default_factory=list)
    actions: list[dict] = Field(default_factory=list)
    version_token: str = ""


class DeviceTypeCreateRequest(BaseModel):
    label: str
    monitoring_enabled: bool = True
    config_backups_enabled: Optional[bool] = None


class DeviceTypeUpdateRequest(BaseModel):
    label: str
    monitoring_enabled: bool = True
    config_backups_enabled: Optional[bool] = None
    version_token: str = ""


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
    theme_palettes: dict[str, dict[str, str]] = Field(default_factory=dict)
    theme_editor_color_keys: list[str] = Field(default_factory=list)
    watermark_enabled: bool
    watermark_opacity: float
    watermark_offset_x: int = 0
    watermark_offset_y: int = 0
    watermark_zoom_percent: int = 100
    watermark_url: str = ""


class ConfigFileResponse(BaseModel):
    id: str = ""
    name: str
    path: str
    modified_at: str
    detail: str = ""
    size_bytes: int = 0
    sha256: str = ""
    sync_status: str = "local_only"
    sync_error: str = ""
    device_type: str = ""
    device_type_label: str = ""
    device_name: str = ""
    device_ip: str = ""


class ConfigStorageStateResponse(BaseModel):
    mode: str
    can_open_backup_folder: bool
    has_smb_password: bool = False
    local_storage_path: str = ""
    backup_path: str = ""
    message: str = ""


class ConfigFileImportRequest(BaseModel):
    device_type: str
    device_id: str = ""
    device_name: str
    device_ip: str = ""
    filename: str = "import.cfg"
    content_base64: str
    detail: str = ""


class WatermarkApplyRequest(BaseModel):
    filename: str = "watermark.png"
    content_base64: str = ""
    opacity: float = 0.16
    offset_x: int = 0
    offset_y: int = 0
    zoom_percent: int = 100


class WatermarkStateResponse(BaseModel):
    enabled: bool = False
    opacity: float = 0.16
    offset_x: int = 0
    offset_y: int = 0
    zoom_percent: int = 100
    image_url: str = ""


class SettingsResponse(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 0
    smtp_auth_enabled: bool = False
    user: str = ""
    use_tls: bool = False
    recipients: str = ""
    offline_delay_seconds: int = 20
    online_recovery_delay_seconds: int = 10
    notification_cooldown_seconds: int = 120
    monitoring_notify_on_outage: bool = True
    monitoring_notify_on_recovery: bool = True
    monitoring_notification_subject_template: str = "[Monitoring] {device_type} {device_name}: {old_status} -> {new_status}"
    monitoring_notification_body_template: str = (
        "Equipement: {device_name}\n"
        "Type: {device_type}\n"
        "IP: {device_ip}\n"
        "Statut: {old_status} -> {new_status}"
    )
    failures_for_offline: int = 5
    successes_for_online: int = 3
    ping_timeout_ms: int = 2500
    probe_interval_ms: int = 2000
    credential_reveal_unlock_seconds: int = 300
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
    watermark_offset_x: int = 0
    watermark_offset_y: int = 0
    watermark_zoom_percent: int = 100
    ui_theme: str = "light"
    theme_overrides_json: str = ""
    status_indicator_style: str = "badge"
    switch_configs_dir: str = ""
    config_storage_mode: str = "local"
    config_smb_unc_path: str = ""
    config_smb_username: str = ""
    config_auto_sync_enabled: bool = False
    config_auto_sync_interval_seconds: int = 3600
    web_server_host: str = "127.0.0.1"
    web_server_port: int = 8000
    web_server_autostart: bool = False
    web_server_public_url: str = ""
    web_server_use_public_url: bool = False
    web_server_reverse_proxy_type: str = "aucun"
    web_session_ttl_seconds: int = 3600
    web_revoke_sessions_on_startup: bool = True
    version_token: str = ""


class SettingsUpdateRequest(SettingsResponse):
    smtp_password: str = ""
    config_smb_password: str = ""


class DashboardPreferencesResponse(BaseModel):
    scope: str = ""
    cards_order: list[str] = Field(default_factory=list)
    hidden_cards: list[str] = Field(default_factory=list)


class DashboardPreferencesUpdateRequest(BaseModel):
    cards_order: list[str] = Field(default_factory=list)
    hidden_cards: list[str] = Field(default_factory=list)


class DatabaseImportRequest(BaseModel):
    filename: str = ""
    content_base64: str = Field(min_length=1)
    confirm_replace: bool = False
