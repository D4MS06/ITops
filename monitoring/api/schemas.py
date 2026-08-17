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
    is_technical: bool = False
    icon: str = ""
    color: str = ""
    granted: bool = False
    last_sync_at: str = ""
    item_count: int = 0
    tile_config: dict[str, object] = Field(default_factory=dict)


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
    track_history: bool = False
    inline_editable: bool = False
    batch_editable: bool = False
    quick_filter: bool = False


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
    is_technical: bool = False
    is_system: bool = False
    credentials_enabled: bool = False
    child_enabled: bool = False
    child_label: str = "Elements lies"
    sort_order: int = 0
    icon: str = ""
    color: str = ""
    tile_config: dict[str, object] = Field(default_factory=dict)
    relationship_inheritance: dict[str, object] = Field(default_factory=dict)
    fields: list[CustomServiceFieldResponse] = Field(default_factory=list)
    version_token: str = ""


class CustomServiceRelationResponse(BaseModel):
    id: int = 0
    source_service_code: str
    target_service_code: str
    service_code: str = ""
    verb: str = "est lie a"
    cardinality: str = "many_to_one"
    relation_type: str = "many_to_one"
    direction: str = "out"
    display_label: str = ""
    label: str = ""
    required: bool = False
    is_active: bool = True
    filter_candidates_by_shared_relation: bool = False
    show_indirect_relations: bool = False
    record_display_mode: str = "standard"
    assignment_resource_service_code: str = ""
    unique_value_field_key: str = ""
    source_x: int | None = None
    source_y: int | None = None
    target_x: int | None = None
    target_y: int | None = None
    x: int | None = None
    y: int | None = None
    sort_order: int = 0
    created_at: str = ""
    updated_at: str = ""


class CustomServiceRelationUpsertRequest(BaseModel):
    # `service_code` is kept as a compatibility alias for early relation drafts.
    # The storage layer validates that one of the two fields is present.
    target_service_code: str = ""
    service_code: str = ""
    verb: str = "est lie a"
    cardinality: str = "many_to_one"
    relation_type: str = ""
    direction: str = "out"
    display_label: str = ""
    label: str = ""
    required: bool = False
    is_active: bool = True
    filter_candidates_by_shared_relation: bool = False
    show_indirect_relations: bool = False
    record_display_mode: str = "standard"
    assignment_resource_service_code: str = ""
    unique_value_field_key: str = ""
    source_x: int | None = None
    source_y: int | None = None
    target_x: int | None = None
    target_y: int | None = None
    x: int | None = None
    y: int | None = None
    sort_order: int = 0


class CustomServiceRelationsReplaceRequest(BaseModel):
    relations: list[CustomServiceRelationUpsertRequest] = Field(default_factory=list)
    allow_linked_relation_deletion: bool = False


class CustomServiceRelationImpactResponse(BaseModel):
    relation_id: int = 0
    source_service_code: str = ""
    target_service_code: str = ""
    link_count: int = 0
    source_record_count: int = 0
    target_record_count: int = 0
    can_delete_safely: bool = True
    warnings: list[str] = Field(default_factory=list)


class CustomServiceDeleteImpactResponse(BaseModel):
    service_code: str = ""
    record_count: int = 0
    relation_count: int = 0
    incoming_relation_count: int = 0
    outgoing_relation_count: int = 0
    relation_link_count: int = 0
    can_delete_safely: bool = True
    warnings: list[str] = Field(default_factory=list)


class CustomServiceRelationLinkResponse(BaseModel):
    id: int = 0
    relation_id: int = 0
    source_record_id: str = ""
    target_record_id: str = ""
    linked_service_code: str = ""
    linked_record: dict = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class CustomServiceRelationLinkCreateRequest(BaseModel):
    linked_record_id: str = Field(min_length=1)


class CustomServiceRelationLinksBatchRequest(BaseModel):
    record_ids: list[str] = Field(default_factory=list, max_length=500)


class CustomServiceUpsertRequest(BaseModel):
    code: str = ""
    label: str = Field(min_length=1)
    is_active: bool = True
    is_technical: bool = False
    credentials_enabled: bool = False
    child_enabled: bool = False
    child_label: str = "Elements lies"
    sort_order: int = 100
    icon: str = ""
    color: str = ""
    tile_config: dict[str, object] = Field(default_factory=dict)
    relationship_inheritance: dict[str, object] = Field(default_factory=dict)
    fields: list[dict] = Field(default_factory=list)
    version_token: str = ""


class CustomServiceImportRequest(BaseModel):
    filename: str = ""
    content_base64: str = Field(min_length=1)
    sheet_name: str = ""
    header_mode: str = "auto"
    header_row_number: int = 1
    import_until_row_number: int = 0
    column_mappings: list[dict] = Field(default_factory=list)


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
    import_until_row_number: int = 0
    column_mappings: list[dict] = Field(default_factory=list)
    relaxed_validation: bool = False
    duplicate_policy: str = "skip"
    duplicate_field_key: str = ""
    history_date_field_key: str = ""
    history_date_source_column: str = ""


class CustomServiceRecordDuplicateMergeRequest(BaseModel):
    field_key: str = Field(min_length=1)
    keeper_record_id: str = Field(min_length=1)
    duplicate_record_ids: list[str] = Field(min_length=1)


class CustomServiceRecordActiveDirectoryImportRequest(BaseModel):
    target_kind: str = "organizational_units"
    field_mappings: list[dict] = Field(default_factory=list)
    upsert_existing: bool = True
    relaxed_validation: bool = False
    limit: int = 5000


class CustomServiceRecordImportPreviewRow(BaseModel):
    record_id: str = ""
    values: dict[str, str] = Field(default_factory=dict)
    children: list[dict] = Field(default_factory=list)


class CustomServiceRecordImportPreviewResponse(BaseModel):
    rows: list[CustomServiceRecordImportPreviewRow] = Field(default_factory=list)
    fields: list[dict] = Field(default_factory=list)
    detected_rows: int = 0
    detected_columns: int = 0
    issues: list[str] = Field(default_factory=list)
    source_headers: list[str] = Field(default_factory=list)
    source_rows_preview: list[list[str]] = Field(default_factory=list)
    available_sheets: list[str] = Field(default_factory=list)
    selected_sheet_name: str = ""
    detected_header_row_number: int = 1
    effective_header_mode: str = "auto"
    effective_mapping: list[dict] = Field(default_factory=list)
    effective_mapping: list[dict] = Field(default_factory=list)
    effective_mapping: list[dict] = Field(default_factory=list)


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
    relation_links: dict[str, list[str]] = Field(default_factory=dict)
    confirm_history_changes: bool = False
    skip_history_changes: bool = False
    history_changed_at: str = ""
    reminder_due_at: str = ""
    version_token: str = ""


class CustomServiceRecordResponse(BaseModel):
    id: str
    service_code: str
    values: dict[str, str] = Field(default_factory=dict)
    children: list[CustomServiceRecordChildResponse] = Field(default_factory=list)
    history_summary: dict[str, dict[str, str]] = Field(default_factory=dict)
    has_credential_password: bool = False
    credential_password_masked: str = ""
    created_at: str = ""
    updated_at: str = ""
    version_token: str = ""


class CustomServiceRecordQueryResponse(BaseModel):
    items: list[CustomServiceRecordResponse] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


class CustomServiceRecordHistoryResponse(BaseModel):
    id: int = 0
    service_code: str
    record_id: str
    field_key: str
    old_value: str = ""
    new_value: str = ""
    changed_at: str = ""
    changed_by: str = ""
    change_source: str = ""


class NotificationTaskResponse(BaseModel):
    id: str
    source_service_code: str = ""
    source_record_id: str = ""
    trigger_field_key: str = ""
    trigger_value: str = ""
    title: str = ""
    message: str = ""
    due_at: str = ""
    status: str = "pending"
    sent_at: str = ""
    completed_at: str = ""
    created_at: str = ""
    updated_at: str = ""


class NotificationTaskStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1)


class NotificationTemplateResponse(BaseModel):
    code: str
    label: str = ""
    module_code: str = ""
    task_type: str = ""
    subject_template: str = ""
    body_template: str = ""
    is_active: bool = True
    is_default: bool = False
    created_at: str = ""
    updated_at: str = ""


class NotificationTemplateUpsertRequest(BaseModel):
    code: str = ""
    label: str = Field(min_length=1)
    module_code: str = ""
    task_type: str = ""
    subject_template: str = Field(min_length=1)
    body_template: str = Field(min_length=1)
    is_active: bool = True
    is_default: bool = False


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


class RemoteStorageMountResponse(BaseModel):
    id: str = ""
    label: str = ""
    service_code: str
    service_label: str
    kind: str = "smb3"
    remote_path: str = ""
    username: str = ""
    local_mount_path: str = ""
    auto_mount_enabled: bool = True
    managed_by: str = ""
    mode: str = ""
    source_path: str = ""
    mount_path: str = ""
    target_path: str = ""
    mounted: bool = False
    automount_active: bool = False
    accessible: bool = False
    status: str = "inactive"
    message: str = ""
    last_error: str = ""
    last_checked_at: str = ""
    systemd_unit: str = ""
    systemd_automount_unit: str = ""


class StorageTargetResponse(BaseModel):
    id: str
    label: str
    service_code: str
    service_label: str
    kind: str = "smb3"
    remote_path: str = ""
    username: str = ""
    local_mount_path: str = ""
    auto_mount_enabled: bool = True
    status: str = "configured"
    last_error: str = ""
    last_checked_at: str = ""
    created_at: str = ""
    updated_at: str = ""


class StorageTargetUpsertRequest(BaseModel):
    id: str = ""
    label: str
    service_code: str = "platform.storage"
    service_label: str = "Stockage ITops"
    kind: str = "smb3"
    remote_path: str
    username: str = ""
    password: str = ""
    local_mount_path: str = ""
    auto_mount_enabled: bool = True


class StorageExplorerRootResponse(BaseModel):
    id: str
    label: str
    service_code: str = "platform.storage"
    service_label: str = "Stockage ITops"
    kind: str = "local"
    path: str = ""
    accessible: bool = False


class StorageExplorerItemResponse(BaseModel):
    name: str
    path: str = ""
    kind: str = "file"
    size_bytes: int = 0
    modified_at: str = ""


class StorageExplorerListResponse(BaseModel):
    root_id: str
    root_label: str = ""
    path: str = ""
    parent_path: str = ""
    items: list[StorageExplorerItemResponse] = Field(default_factory=list)


class StorageExplorerFolderCreateRequest(BaseModel):
    root_id: str
    path: str = ""
    name: str


class StorageExplorerUploadRequest(BaseModel):
    root_id: str
    path: str = ""
    filename: str
    content_base64: str


class StorageExplorerDeleteRequest(BaseModel):
    root_id: str
    path: str


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
    active_directory_enabled: bool = False
    active_directory_host: str = ""
    active_directory_dns_servers: str = ""
    active_directory_port: int = 636
    active_directory_use_ssl: bool = True
    active_directory_validate_certificates: bool = True
    active_directory_ca_certificate_path: str = ""
    active_directory_ca_certificate_file_id: str = ""
    active_directory_bind_username: str = ""
    active_directory_base_dn: str = ""
    active_directory_user_filter: str = "(&(objectCategory=person)(objectClass=user))"
    active_directory_sync_interval_seconds: int = 3600
    active_directory_sync_email_accounts: bool = False
    active_directory_sources_json: str = "[]"
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
    active_directory_bind_password: str = ""


class ActiveDirectoryCertificateImportRequest(BaseModel):
    filename: str = Field(min_length=1)
    content_base64: str = Field(min_length=1)


class ActiveDirectoryCertificateResponse(BaseModel):
    filename: str = ""
    imported: bool = False


class ActiveDirectorySyncNowRequest(BaseModel):
    mode: str = "normal"
    source_id: str = ""


class ActiveDirectorySource(BaseModel):
    id: str = ""
    label: str = ""
    host: str = ""
    dns_servers: list[str] = Field(default_factory=list)
    port: int = 636
    use_ssl: bool = True
    validate_certificates: bool = True
    ca_certificate_path: str = ""
    bind_username: str = ""
    base_dn: str = ""
    user_filter: str = "(&(objectCategory=person)(objectClass=user))"
    sync_interval_seconds: int = 3600
    sync_email_accounts: bool = False
    is_active: bool = True
    has_password: bool = False
    last_sync_at: str = ""


class ActiveDirectorySourceUpsertRequest(ActiveDirectorySource):
    password: str = ""


class ActiveDirectorySourceListResponse(BaseModel):
    sources: list[ActiveDirectorySource] = Field(default_factory=list)
    primary_last_sync_at: str = ""


class ActiveDirectorySyncProfile(BaseModel):
    id: str = ""
    source_kind: str = "active_directory"
    code: str = ""
    label: str = ""
    target_kind: str = "users"
    search_base: str = ""
    search_filter: str = ""
    selected_attributes: list[str] = Field(default_factory=list)
    options: dict = Field(default_factory=dict)
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""


class ActiveDirectorySyncProfileUpsertRequest(BaseModel):
    id: str = ""
    code: str = ""
    label: str = Field(min_length=1)
    target_kind: str = "users"
    search_base: str = ""
    search_filter: str = ""
    selected_attributes: list[str] = Field(default_factory=list)
    options: dict = Field(default_factory=dict)
    is_active: bool = True
    confirm_impact: bool = False


class ActiveDirectorySyncProfileListResponse(BaseModel):
    profiles: list[ActiveDirectorySyncProfile] = Field(default_factory=list)
    available_attributes: dict[str, list[str]] = Field(default_factory=dict)
    # The connection(s) to which a mapping can be assigned.  Keeping this on
    # the profile response lets the UI map one or several domains explicitly.
    available_sources: list[dict] = Field(default_factory=list)
    available_targets: list[dict] = Field(default_factory=list)


class ActiveDirectorySyncProfilePreviewResponse(BaseModel):
    profile: ActiveDirectorySyncProfile
    attributes: list[str] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)
    total_preview_rows: int = 0


class ActiveDirectoryCacheRefreshRequest(BaseModel):
    target_kind: str = "organizational_units"


class ActiveDirectoryCacheRefreshResponse(BaseModel):
    target_kind: str = "organizational_units"
    refreshed: int = 0
    message: str = ""


class ActiveDirectoryCachePreviewResponse(BaseModel):
    target_kind: str = "organizational_units"
    attributes: list[str] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)
    total_rows: int = 0
    synced_at: str = ""


class DashboardPreferencesResponse(BaseModel):
    scope: str = ""
    cards_order: list[str] = Field(default_factory=list)
    hidden_cards: list[str] = Field(default_factory=list)
    pinned_cards: list[str] = Field(default_factory=list)


class DashboardPreferencesUpdateRequest(BaseModel):
    cards_order: list[str] = Field(default_factory=list)
    hidden_cards: list[str] = Field(default_factory=list)
    pinned_cards: list[str] = Field(default_factory=list)


class DatabaseImportRequest(BaseModel):
    filename: str = ""
    content_base64: str = Field(min_length=1)
    confirm_replace: bool = False
    backup_password: str = ""


class DatabaseBackupRequest(BaseModel):
    backup_password: str = Field(min_length=12, max_length=1024)


class SecretsVaultStatusResponse(BaseModel):
    initialized: bool
    uses_external_master_key: bool
    has_local_key: bool
    directory: str
