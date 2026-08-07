from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib.util
import json
from io import BytesIO
import ipaddress
import os
import re
import shutil
import socket
import subprocess
import ssl
import tempfile
import urllib.parse
import uuid
import time
import html as html_lib
import unicodedata
from http.cookies import SimpleCookie
from datetime import datetime, timezone
from queue import Empty, Queue
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
import threading

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.background import BackgroundTask

from monitoring.versioning import resolve_display_version
from monitoring.api.schemas import (
    AuthStatusResponse,
    AdminModuleActivationRequest,
    AdminModuleResponse,
    ActiveDirectoryCertificateImportRequest,
    ActiveDirectoryCertificateResponse,
    ActiveDirectoryCachePreviewResponse,
    ActiveDirectoryCacheRefreshRequest,
    ActiveDirectoryCacheRefreshResponse,
    ActiveDirectorySyncNowRequest,
    ActiveDirectorySyncProfile,
    ActiveDirectorySyncProfileListResponse,
    ActiveDirectorySyncProfilePreviewResponse,
    ActiveDirectorySyncProfileUpsertRequest,
    CustomServiceImportRequest,
    CustomServiceImportResponse,
    CustomServiceRecordActiveDirectoryImportRequest,
    CustomServiceRecordImportApplyResponse,
    CustomServiceRecordImportPreviewResponse,
    CustomServiceRecordImportRequest,
    CustomServiceRecordHistoryResponse,
    CustomServiceRecordQueryResponse,
    CustomServiceRelationResponse,
    CustomServiceRelationLinkCreateRequest,
    CustomServiceRelationLinksBatchRequest,
    CustomServiceRelationLinkResponse,
    CustomServiceRelationsReplaceRequest,
    CustomServiceRelationUpsertRequest,
    SharedListResponse,
    SharedListUpsertRequest,
    SharedListItemResponse,
    SharedListItemUpsertRequest,
    SharedListImportResponse,
    AdminRoleResponse,
    AdminRoleUpsertRequest,
    AdminUserCreateRequest,
    AdminUserResponse,
    AdminUserUpdateRequest,
    BootstrapPasswordRequest,
    CustomServiceRecordResponse,
    CustomServiceRecordUpsertRequest,
    CustomServiceResponse,
    CustomServiceDeleteImpactResponse,
    CustomServiceRelationImpactResponse,
    CustomServiceUpsertRequest,
    ConfigFileResponse,
    ConfigFileImportRequest,
    DashboardPreferencesResponse,
    DashboardPreferencesUpdateRequest,
    DatabaseImportRequest,
    WatermarkApplyRequest,
    WatermarkStateResponse,
    ConfigStorageStateResponse,
    DeviceCreateRequest,
    DeviceCredentialRevealRequest,
    DeviceCredentialRevealResponse,
    DeviceImportApplyResponse,
    DeviceImportPreviewResponse,
    DeviceImportRequest,
    DeviceResponse,
    DeviceTypeCreateRequest,
    DeviceTypeResponse,
    DeviceTypeSchemaResponse,
    DeviceTypeSchemaUpdateRequest,
    DeviceTypeUpdateRequest,
    DeviceUpdateRequest,
    LoginRequest,
    MessageResponse,
    NotificationTemplateResponse,
    NotificationTemplateUpsertRequest,
    NotificationTaskResponse,
    NotificationTaskStatusUpdateRequest,
    SetupFinalizeRequest,
    SetupStatusResponse,
    ModuleAccessResponse,
    MonitoringCapabilitiesResponse,
    MonitoringSnapshotResponse,
    MonitoringSummaryResponse,
    MonitoringTypeStateResponse,
    NetworkToolDnsLookupRequest,
    NetworkToolHttpCheckRequest,
    NetworkToolPingRequest,
    NetworkToolPortCheckRequest,
    NetworkScanRequest,
    NetworkScanRowResponse,
    NetworkToolResponse,
    NetworkToolSnmpCheckRequest,
    NetworkToolTracerouteRequest,
    RemoteStorageMountResponse,
    SessionContextResponse,
    SessionInfoResponse,
    SessionProfileResponse,
    SettingsResponse,
    SettingsUpdateRequest,
    StatusLogResponse,
    StorageTargetResponse,
    StorageTargetUpsertRequest,
    StorageExplorerDeleteRequest,
    StorageExplorerFolderCreateRequest,
    StorageExplorerItemResponse,
    StorageExplorerListResponse,
    StorageExplorerRootResponse,
    StorageExplorerUploadRequest,
    TokenResponse,
    UiConfigResponse,
)
from monitoring.backend.app_backend import ApplicationBackend, build_application_backend
from monitoring.config.settings import NotificationSettings, load_settings, save_settings
from monitoring.config.hebergement_web import HebergementWebConfig, default_hebergement_web_path, save_hebergement_web_config
from monitoring.config.setup_installation import (
    default_install_env_file,
    default_setup_state_path,
    load_setup_state,
    read_setup_token,
    remove_setup_token,
    save_setup_state,
    update_install_env,
    SetupInstallationState,
)
from monitoring.models.devices_model import DevicesModel
from monitoring.services.auth_service import AuthService
from monitoring.services.auth_service import PasswordChangeRequiredError
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.services.device_config_file_service import DeviceConfigFileService
from monitoring.services.device_type_service import DeviceTypeService
from monitoring.services.linked_file_service import LinkedFileService
from monitoring.services.monitoring_runtime_service import MonitoringRuntimeService
from monitoring.services.monitoring_service import MonitoringService
from monitoring.services.settings_service import ActiveDirectorySyncEngine, SettingsService
from monitoring.services.storage_target_service import StorageTargetService
from monitoring.services.caddy_manager import CaddyManager
from monitoring.services.custom_service_schema import (
    normalize_child_rows,
    normalize_field_key,
    normalize_service_code,
    normalize_service_fields,
    validate_record_values,
)
from monitoring.services.custom_service_history import build_field_history_events
from monitoring.services.custom_service_index import backfill_record_index
from monitoring.services.service_fields_import import (
    infer_service_fields_from_rows,
    infer_shared_list_items_from_rows,
    resolve_service_field_import_mapping,
)
from monitoring.services.device_inventory_tabular import (
    infer_devices_from_rows,
    export_devices_to_csv,
    resolve_effective_column_mapping,
)
from monitoring.services.custom_service_records_tabular import (
    infer_custom_service_records_from_rows,
    export_custom_service_records_to_csv,
    resolve_effective_record_column_mapping,
)
from monitoring.services.import_credentials_policy import (
    normalize_credential_import_mode,
    resolve_credential_import_values,
)
from monitoring.services.tabular_io import (
    encode_csv_bytes,
    parse_tabular_file_with_metadata,
    resolve_tabular_sheet_selection,
)
from monitoring.services.device_action_policy import validate_action_double_click
from monitoring.controllers.network_tools_controller import NetworkToolsController
from monitoring.services.network_scan_service import NetworkScanService
from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.shared.theme_manager import list_editor_color_keys, resolve_theme
from monitoring.utils.config_files import open_path_with_default_app
from monitoring.utils.logger import log_with_timestamp
from monitoring.utils.notifications import send_alert_email
from monitoring.utils.process_runner import windows_no_window_kwargs

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
FAVICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "app.ico"
APP_VERSION = resolve_display_version()


def _safe_int_env(key: str, default: int, *, minimum: int = 1) -> int:
    try:
        value = int(str(os.environ.get(key) or "").strip() or int(default))
    except Exception:
        value = int(default)
    return max(int(minimum), int(value))


_MAX_NETWORK_SCAN_HOSTS = _safe_int_env("NMP_NETWORK_SCAN_MAX_IPS", 4096, minimum=64)


class WebStaticFiles(StaticFiles):
    CACHEABLE_EXTENSIONS = (
        ".js",
        ".css",
        ".png",
        ".jpg",
        ".jpeg",
        ".svg",
        ".ico",
        ".woff",
        ".woff2",
    )
    LEGACY_PROXY_PREFIX_COOKIE = "itops_switch_proxy_prefix"
    LEGACY_PROXY_PATH_ROOTS = {
        "web",
        "hpe",
        "device",
        "htdocs",
        "html",
        "cgi",
        "cgi-bin",
        "xsl",
        "wcn",
        "wnm",
        "en",
        "cn",
        "images",
        "nextgen",
        "customdir",
        "skin",
    }

    @classmethod
    def _cookie_value(cls, scope, key: str) -> str:
        raw_cookie_header = ""
        for header_key, header_value in list(scope.get("headers") or []):
            if bytes(header_key or b"").lower() == b"cookie":
                raw_cookie_header = bytes(header_value or b"").decode("latin-1", errors="ignore")
                break
        if not raw_cookie_header:
            return ""
        jar = SimpleCookie()
        try:
            jar.load(raw_cookie_header)
        except Exception:
            return ""
        morsel = jar.get(str(key or ""))
        return str(morsel.value or "").strip() if morsel else ""

    @classmethod
    def _build_legacy_switch_proxy_redirect(cls, *, path: str, scope) -> str | None:
        normalized = str(path or "").replace("\\", "/").lstrip("/")
        if not normalized:
            return None
        root = normalized.split("/", 1)[0].strip().lower()
        if root not in cls.LEGACY_PROXY_PATH_ROOTS:
            return None
        proxy_prefix = cls._cookie_value(scope, cls.LEGACY_PROXY_PREFIX_COOKIE)
        if not proxy_prefix.startswith("/devices/") or "/web-ui" not in proxy_prefix:
            return None
        query = bytes(scope.get("query_string") or b"").decode("latin-1", errors="ignore")
        target = f"{proxy_prefix}/web/{normalized}"
        return f"{target}?{query}" if query else target

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if int(exc.status_code or 0) != status.HTTP_404_NOT_FOUND:
                raise
            redirect_url = self._build_legacy_switch_proxy_redirect(path=path, scope=scope)
            if redirect_url:
                return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
            raise
        if response.status_code == status.HTTP_404_NOT_FOUND:
            redirect_url = self._build_legacy_switch_proxy_redirect(path=path, scope=scope)
            if redirect_url:
                return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        lowered = str(path or "").lower()
        if response.status_code == status.HTTP_200_OK and lowered.endswith(self.CACHEABLE_EXTENSIONS):
            response.headers.setdefault("Cache-Control", "public, max-age=604800, stale-while-revalidate=86400")
        return response


@dataclass
class ApiServices:
    model: DevicesModel
    auth: AuthService
    device_types: DeviceTypeService
    monitoring: MonitoringService
    monitoring_runtime: MonitoringRuntimeService
    config_storage: ConfigStorageService
    linked_files: LinkedFileService
    device_config_files: DeviceConfigFileService
    network_tools: NetworkToolsController
    logs: MariaDBFileManager
    storage_targets: StorageTargetService
    settings_service: SettingsService
    settings_loader: Callable[[], NotificationSettings]
    settings_saver: Callable[[NotificationSettings], None]


def create_app(
    *,
    backend: Optional[ApplicationBackend] = None,
    model: Optional[DevicesModel] = None,
    auth_service: Optional[AuthService] = None,
    device_type_service: Optional[DeviceTypeService] = None,
    monitoring_runtime_service: Optional[MonitoringRuntimeService] = None,
    config_storage_service: Optional[ConfigStorageService] = None,
    logs_manager: Optional[MariaDBFileManager] = None,
    settings_loader: Callable[[], NotificationSettings] = load_settings,
    settings_saver: Callable[[NotificationSettings], None] = save_settings,
    stop_runtime_on_shutdown: bool = True,
) -> FastAPI:
    services = _build_api_services(
        backend=backend,
        model=model,
        auth_service=auth_service,
        device_type_service=device_type_service,
        monitoring_runtime_service=monitoring_runtime_service,
        config_storage_service=config_storage_service,
        logs_manager=logs_manager,
        settings_loader=settings_loader,
        settings_saver=settings_saver,
    )

    app = FastAPI(
        title="Network Monitoring API",
        version=APP_VERSION,
        lifespan=_build_lifespan(services, stop_runtime_on_shutdown),
    )
    app.state.services = services
    app.mount("/web", WebStaticFiles(directory=str(WEB_DIR)), name="web")

    def get_services() -> ApiServices:
        return app.state.services

    def get_bearer_token(authorization: Optional[str] = Header(default=None)) -> str:
        raw = str(authorization or "").strip()
        if not raw.lower().startswith("bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Bearer manquant.")
        token = raw[7:].strip()
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Bearer vide.")
        return token

    def require_session(
        token: str = Depends(get_bearer_token),
        api: ApiServices = Depends(get_services),
    ):
        session = api.auth.get_session(token)
        if session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expiree.")
        return session

    def require_module_access(module_code: str):
        normalized = str(module_code or "").strip().lower()

        def _dependency(
            session=Depends(require_session),
            api: ApiServices = Depends(get_services),
        ):
            checker = getattr(api.logs, "subject_has_module", None)
            if callable(checker):
                allowed = bool(checker(subject=str(session.subject), module_code=normalized))
            else:
                allowed = str(session.subject).strip().lower() in {"sa", "admin"}
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Acces refuse pour le module '{normalized}'.",
                )
            return session

        return _dependency

    def require_websocket_session(token: str, api: ApiServices):
        session = api.auth.get_session(token)
        if session is None:
            return None
        return session

    require_monitoring_module = require_module_access("monitoring")
    require_admin_module = require_module_access("admin")
    require_directory_agents_module = require_module_access("directory_agents")
    require_directory_services_module = require_module_access("directory_services")

    _register_base_routes(app)
    _register_setup_routes(app, get_services)
    _register_auth_routes(app, get_services, get_bearer_token, require_session)
    _register_devices_routes(app, get_services, require_session, require_websocket_session, require_monitoring_module)
    _register_logs_routes(app, get_services, require_session, require_monitoring_module)
    _register_network_tools_routes(app, get_services, require_session, require_monitoring_module)
    _register_monitoring_routes(app, get_services, require_session, require_websocket_session, require_monitoring_module)
    _register_ui_routes(app, get_services, require_session, require_websocket_session)
    _register_config_routes(app, get_services, require_session, require_monitoring_module)
    _register_directory_routes(app, get_services, require_directory_agents_module, require_directory_services_module)
    _register_settings_routes(app, get_services, require_admin_module)
    _register_admin_routes(app, get_services, require_session)
    return app


def _build_api_services(
    *,
    backend: Optional[ApplicationBackend],
    model: Optional[DevicesModel],
    auth_service: Optional[AuthService],
    device_type_service: Optional[DeviceTypeService],
    monitoring_runtime_service: Optional[MonitoringRuntimeService],
    config_storage_service: Optional[ConfigStorageService],
    logs_manager: Optional[MariaDBFileManager],
    settings_loader: Callable[[], NotificationSettings],
    settings_saver: Callable[[NotificationSettings], None],
) -> ApiServices:
    resolved_manager = logs_manager
    if resolved_manager is None and model is not None:
        resolved_manager = getattr(model, "manager", None)

    backend = backend or build_application_backend(
        manager=resolved_manager,
        settings_loader=settings_loader,
        settings_saver=settings_saver,
    )

    model = model or backend.model
    shared_manager = logs_manager or getattr(model, "manager", None) or backend.manager
    runtime_service = monitoring_runtime_service
    monitoring_service = backend.monitoring_service if model is backend.model else MonitoringService(model, logs_store=shared_manager)
    if runtime_service is None:
        if model is backend.model:
            runtime_service = backend.monitoring_runtime_service
        else:
            runtime_service = MonitoringRuntimeService(
                model,
                monitoring_service,
            )

    return ApiServices(
        model=model,
        auth=auth_service or backend.auth_service,
        device_types=device_type_service or backend.device_type_service,
        monitoring=monitoring_service,
        monitoring_runtime=runtime_service,
        config_storage=config_storage_service or backend.config_storage_service,
        linked_files=backend.linked_file_service,
        device_config_files=backend.device_config_file_service,
        network_tools=NetworkToolsController(),
        logs=shared_manager,
        storage_targets=backend.storage_target_service,
        settings_service=backend.settings_service,
        settings_loader=settings_loader or backend.settings_loader,
        settings_saver=settings_saver or backend.settings_saver,
    )


def _build_lifespan(services: ApiServices, stop_runtime_on_shutdown: bool):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = services
        notification_task_runner = asyncio.create_task(_run_notification_task_processor(services))
        switch_proxy_client = httpx.AsyncClient(
            timeout=httpx.Timeout(45.0, connect=10.0),
            verify=False,
            follow_redirects=False,
            limits=_SWITCH_PROXY_CLIENT_LIMITS,
        )
        _set_switch_proxy_http_client(switch_proxy_client)
        try:
            yield
        finally:
            notification_task_runner.cancel()
            with suppress(asyncio.CancelledError):
                await notification_task_runner
            _set_switch_proxy_http_client(None)
            try:
                await switch_proxy_client.aclose()
            except Exception as exc:
                log_with_timestamp(f"Erreur fermeture client proxy switch: {exc}", level="WARNING")
            if stop_runtime_on_shutdown:
                try:
                    services.monitoring_runtime.stop_all()
                    services.monitoring.shutdown()
                except Exception as exc:
                    log_with_timestamp(f"Erreur arret runtime API: {exc}", level="WARNING")

    return lifespan


def _notification_task_due_at(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("T", " "))
    except ValueError:
        return None


def _notification_task_template_type(task: dict) -> str:
    field = str((task or {}).get("trigger_field_key") or "").strip().lower()
    value = str((task or {}).get("trigger_value") or "").strip().lower()
    if field and value:
        return f"{field}:{value}"
    return field or "generic:reminder"


def _render_notification_template_text(template: str, variables: dict[str, str]) -> str:
    output = str(template or "")
    for key, value in variables.items():
        output = output.replace("{{" + key + "}}", str(value or ""))
        output = output.replace("{" + key + "}", str(value or ""))
    return output


def _render_notification_task_message(services: ApiServices, task: dict) -> tuple[str, str]:
    title = str(task.get("title") or "Rappel ITops").strip() or "Rappel ITops"
    message = str(task.get("message") or "").strip() or title
    finder = getattr(services.logs, "find_notification_template", None)
    if not callable(finder):
        return title, message
    module_code = str(task.get("source_service_code") or "").strip().lower()
    task_type = _notification_task_template_type(task)
    template = finder(module_code=module_code, task_type=task_type)
    if not template:
        return title, message
    variables = {
        "task.id": str(task.get("id") or ""),
        "task.label": title,
        "task.message": message,
        "task.due_at": str(task.get("due_at") or ""),
        "task.status": str(task.get("status") or ""),
        "task.type": task_type,
        "module.code": module_code,
        "record.id": str(task.get("source_record_id") or ""),
        "trigger.field": str(task.get("trigger_field_key") or ""),
        "trigger.value": str(task.get("trigger_value") or ""),
        "app.name": "ITops",
    }
    subject = _render_notification_template_text(str(template.get("subject_template") or ""), variables).strip() or title
    body = _render_notification_template_text(str(template.get("body_template") or ""), variables).strip() or message
    return subject, body


async def _run_notification_task_processor(services: ApiServices) -> None:
    while True:
        try:
            await asyncio.sleep(60)
            lister = getattr(services.logs, "list_notification_tasks", None)
            updater = getattr(services.logs, "set_notification_task_status", None)
            if not callable(lister) or not callable(updater):
                continue
            now = datetime.now()
            pending_tasks = await asyncio.to_thread(lister, status_filter="pending", limit=100)
            due_tasks = [
                dict(task or {})
                for task in list(pending_tasks or [])
                if (due_at := _notification_task_due_at(str((task or {}).get("due_at") or ""))) is not None and due_at <= now
            ]
            if not due_tasks:
                continue
            settings = services.settings_service.get()
            for task in due_tasks:
                task_id = str(task.get("id") or "").strip()
                title, message = _render_notification_task_message(services, task)
                try:
                    await asyncio.to_thread(send_alert_email, title, message, settings=settings)
                    await asyncio.to_thread(updater, task_id=task_id, status="sent")
                except Exception as exc:
                    log_with_timestamp(f"Tache notification non envoyee {task_id}: {exc}", level="WARNING")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_with_timestamp(f"Erreur processeur taches notification: {exc}", level="WARNING")


def _resolve_setup_server_hint_ip(request: Request | None) -> tuple[str, str]:
    access_host = ""
    if request is not None:
        try:
            access_host = str(request.url.hostname or "").strip()
        except Exception:
            access_host = ""
    hint_ip = ""
    if access_host:
        try:
            parsed = ipaddress.ip_address(access_host)
            if getattr(parsed, "version", 0) == 4:
                hint_ip = access_host
        except Exception:
            pass

    if not hint_ip:
        candidates: list[str] = []
        try:
            for item in socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET):
                ip = str(item[4][0] or "").strip()
                if ip and ip != "127.0.0.1":
                    candidates.append(ip)
        except Exception:
            pass
        if candidates:
            hint_ip = candidates[0]
    return access_host, hint_ip


def _build_setup_status(api: ApiServices, request: Request | None = None) -> SetupStatusResponse:
    state = load_setup_state()
    has_admin_password = bool(api.auth.has_admin_password())
    # Once technical installation is marked completed, do not reopen setup wizard.
    # Admin password bootstrap is handled by the auth/portal flow.
    setup_required = not bool(state.completed)
    if str(os.environ.get("NMP_DEV_SKIP_SETUP_WIZARD") or "").strip().lower() in {"1", "true", "yes", "on"}:
        setup_required = False
    has_token = bool(read_setup_token())
    access_host, hint_ip = _resolve_setup_server_hint_ip(request)
    return SetupStatusResponse(
        setup_required=setup_required,
        setup_completed=bool(state.completed),
        has_setup_token=has_token,
        has_admin_password=has_admin_password,
        app_version=APP_VERSION,
        hebergement_config_path=str(default_hebergement_web_path()),
        install_env_path=str(default_install_env_file()),
        server_access_host=access_host,
        server_hint_ip=hint_ip,
    )


_SAFE_DB_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
_SAFE_DB_HOST_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _quote_sql_identifier(name: str) -> str:
    return f"`{str(name or '').replace('`', '``')}`"


def _quote_sql_literal(value: str) -> str:
    return "'" + str(value or "").replace("\\", "\\\\").replace("'", "''") + "'"


def _read_install_env_value(key: str) -> str:
    target = default_install_env_file()
    if not target.is_file():
        return ""
    wanted = str(key or "").strip()
    if not wanted:
        return ""
    try:
        for raw in target.read_text(encoding="utf-8").splitlines():
            line = str(raw or "").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            current_key, value = line.split("=", 1)
            if str(current_key or "").strip() != wanted:
                continue
            parsed = str(value or "").strip()
            if len(parsed) >= 2 and parsed[0] == "'" and parsed[-1] == "'":
                parsed = parsed[1:-1].replace("'\"'\"'", "'")
            return parsed.strip()
    except Exception:
        return ""
    return ""


def _provision_local_mariadb_from_setup(payload: SetupFinalizeRequest) -> None:
    if str(os.environ.get("NMP_SETUP_SKIP_MARIADB_PROVISION") or "").strip() in {"1", "true", "yes", "on"}:
        return

    db_name = str(payload.db_name or "").strip()
    db_user = str(payload.db_user or "").strip()
    db_password = str(payload.db_password or "")
    db_host = str(payload.db_host or "127.0.0.1").strip() or "127.0.0.1"
    root_password = str(payload.mariadb_root_password or "").strip()

    if not _SAFE_DB_IDENTIFIER_RE.match(db_name):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nom de base MariaDB invalide (caracteres autorises: lettres, chiffres, underscore).",
        )
    if not _SAFE_DB_IDENTIFIER_RE.match(db_user):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nom d'utilisateur MariaDB invalide (caracteres autorises: lettres, chiffres, underscore).",
        )
    if not _SAFE_DB_HOST_RE.match(db_host):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Host MariaDB invalide.",
        )

    try:
        import pymysql  # type: ignore
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Client MariaDB Python indisponible: {exc}",
        ) from exc

    current_root_password = str(os.environ.get("NMP_MARIADB_ROOT_PASSWORD") or "").strip()
    persisted_root_password = _read_install_env_value("NMP_MARIADB_ROOT_PASSWORD")
    db_name_sql = _quote_sql_identifier(db_name)
    db_user_sql = _quote_sql_literal(db_user)
    db_password_sql = _quote_sql_literal(db_password)
    grant_hosts: list[str] = []
    for candidate in (db_host, "localhost", "127.0.0.1"):
        host = str(candidate or "").strip()
        if host and host not in grant_hosts:
            grant_hosts.append(host)

    statements = [f"CREATE DATABASE IF NOT EXISTS {db_name_sql} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"]
    for host in grant_hosts:
        host_sql = _quote_sql_literal(host)
        statements.extend(
            [
                f"CREATE USER IF NOT EXISTS {db_user_sql}@{host_sql} IDENTIFIED BY {db_password_sql}",
                f"ALTER USER {db_user_sql}@{host_sql} IDENTIFIED BY {db_password_sql}",
                f"GRANT ALL PRIVILEGES ON {db_name_sql}.* TO {db_user_sql}@{host_sql}",
            ]
        )
    root_password_sql = _quote_sql_literal(root_password)
    statements.extend(
        [
            f"ALTER USER IF EXISTS 'root'@'localhost' IDENTIFIED BY {root_password_sql}",
            f"ALTER USER IF EXISTS 'root'@'127.0.0.1' IDENTIFIED BY {root_password_sql}",
            "FLUSH PRIVILEGES",
        ]
    )

    connection = None
    last_error: Exception | None = None
    attempts: list[str] = []
    socket_candidates = ("/run/mysqld/mysqld.sock", "/var/run/mysqld/mysqld.sock")
    root_password_candidates: list[str] = []
    for candidate in (current_root_password, persisted_root_password, root_password, ""):
        if candidate not in root_password_candidates:
            root_password_candidates.append(candidate)

    for root_candidate in root_password_candidates:
        for socket_path in socket_candidates:
            if not Path(socket_path).exists():
                continue
            try:
                connection = pymysql.connect(
                    unix_socket=socket_path,
                    user="root",
                    password=root_candidate,
                    autocommit=True,
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.Cursor,
                )
                break
            except Exception as exc:
                last_error = exc
                attempts.append(f"socket:{socket_path} user=root password={'YES' if root_candidate else 'NO'} -> {exc}")
        if connection is not None:
            break

    if connection is None:
        for root_candidate in root_password_candidates:
            try:
                connection = pymysql.connect(
                    host="127.0.0.1",
                    port=int(payload.db_port),
                    user="root",
                    password=root_candidate,
                    autocommit=True,
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.Cursor,
                )
                break
            except Exception as exc:
                last_error = exc
                attempts.append(f"tcp:127.0.0.1:{int(payload.db_port)} user=root password={'YES' if root_candidate else 'NO'} -> {exc}")

    if connection is None:
        if _provision_local_mariadb_with_cli(
            payload=payload,
            sql_statements=statements,
            root_password_candidates=root_password_candidates,
        ):
            return
        detail = "Impossible d'appliquer automatiquement la configuration MariaDB locale (connexion root indisponible via socket/TCP local)."
        if attempts:
            detail = f"{detail} Tentatives: {' || '.join(attempts[-4:])}"
        elif last_error is not None:
            detail = f"{detail} Detail: {last_error}"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    try:
        with connection.cursor() as cursor:
            for sql in statements:
                cursor.execute(sql)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Echec de provisionnement MariaDB automatique: {exc}",
        ) from exc
    finally:
        try:
            connection.close()
        except Exception:
            pass


def _provision_local_mariadb_with_cli(
    *,
    payload: SetupFinalizeRequest,
    sql_statements: list[str],
    root_password_candidates: list[str],
) -> bool:
    if not shutil.which("mysql"):
        return False
    sql_text = ";\n".join([str(stmt or "").strip().rstrip(";") for stmt in sql_statements if str(stmt or "").strip()]) + ";\n"
    try:
        candidates: list[list[str]] = []
        for root_candidate in root_password_candidates:
            base = ["mysql", "-u", "root"]
            if root_candidate:
                base.append(f"-p{root_candidate}")
            candidates.append(base + ["--socket=/run/mysqld/mysqld.sock"])
            candidates.append(base + ["--socket=/var/run/mysqld/mysqld.sock"])
            candidates.append(
                base
                + [
                    "-h",
                    "127.0.0.1",
                    "-P",
                    str(int(payload.db_port)),
                ]
            )
        for cmd in candidates:
            completed = subprocess.run(
                cmd,
                input=sql_text,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return_code = int(completed.returncode) if completed.returncode is not None else 1
            if return_code == 0:
                return True
    except Exception:
        return False
    return False


def _verify_mariadb_application_login(payload: SetupFinalizeRequest, *, timeout_seconds: int = 20) -> None:
    if str(os.environ.get("NMP_SETUP_SKIP_MARIADB_PROVISION") or "").strip() in {"1", "true", "yes", "on"}:
        return

    try:
        import pymysql  # type: ignore
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Client MariaDB Python indisponible: {exc}",
        ) from exc

    host = str(payload.db_host or "127.0.0.1").strip() or "127.0.0.1"
    port = int(payload.db_port)
    user = str(payload.db_user or "").strip()
    password = str(payload.db_password or "")
    db_name = str(payload.db_name or "").strip()
    deadline = time.monotonic() + max(1, int(timeout_seconds))
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=db_name,
                charset="utf8mb4",
                autocommit=True,
                cursorclass=pymysql.cursors.Cursor,
                connect_timeout=3,
                read_timeout=3,
                write_timeout=3,
            )
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
            finally:
                try:
                    connection.close()
                except Exception:
                    pass
            return
        except Exception as exc:
            last_error = exc
            time.sleep(1)

    detail = "Validation des identifiants MariaDB applicatifs impossible."
    if last_error is not None:
        detail = f"{detail} Detail: {last_error}"
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


def _extract_public_url_parts(public_url: str) -> tuple[str, str]:
    raw = str(public_url or "").strip()
    if not raw:
        return "", ""
    parsed = urllib.parse.urlparse(raw)
    if str(parsed.scheme or "").lower() != "https":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL publique invalide: le schema doit etre https://",
        )
    host = str(parsed.hostname or "").strip().lower()
    if not host:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL publique invalide: hostname manquant.",
        )
    if not _SAFE_DB_HOST_RE.match(host):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL publique invalide: hostname non supporte.",
        )
    return raw, host


def _run_subprocess_checked(args: list[str], *, timeout: int = 90, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=int(timeout),
        check=False,
        env=env,
    )
    return_code = int(completed.returncode) if completed.returncode is not None else 1
    if return_code == 0:
        return
    stderr = str(completed.stderr or "").strip()
    stdout = str(completed.stdout or "").strip()
    if stderr and stdout:
        detail = f"stdout: {stdout} | stderr: {stderr}"
    else:
        detail = stderr or stdout or f"exit code {return_code}"
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Echec commande systeme ({' '.join(args)}): {detail}",
    )


def _assert_binary_available(binary_name: str, package_hint: str) -> None:
    if shutil.which(binary_name):
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Binaire '{binary_name}' introuvable. Installez le paquet '{package_hint}' via le bootstrap "
            "avant de relancer la finalisation du wizard."
        ),
    )


def _normalize_reverse_proxy_type(value: object) -> str:
    normalized = str(value or "aucun").strip().lower()
    if normalized in {"nginx", "caddy"}:
        return normalized
    return "aucun"


def _should_skip_reverse_proxy_setup() -> bool:
    return str(os.environ.get("NMP_SETUP_SKIP_REVERSE_PROXY_SETUP") or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_systemctl_available() -> bool:
    return os.name == "posix" and shutil.which("systemctl") is not None


def _systemd_service_exists(service_name: str) -> bool:
    if not _is_systemctl_available():
        return False
    completed = subprocess.run(
        ["systemctl", "list-unit-files", "--no-legend", "--no-pager", f"{service_name}.service"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return_code = int(completed.returncode) if completed.returncode is not None else 1
    if return_code != 0:
        return False
    target = f"{service_name}.service"
    return any(
        str(line or "").strip().startswith(target)
        for line in str(completed.stdout or "").splitlines()
    )


def _disable_reverse_proxy_service_if_present(service_name: str) -> None:
    if not _is_systemctl_available() or not _systemd_service_exists(service_name):
        return
    _run_subprocess_checked(["systemctl", "disable", "--now", service_name], timeout=90)


def _enable_reverse_proxy_service_if_needed(service_name: str) -> None:
    if not _is_systemctl_available() or not _systemd_service_exists(service_name):
        return
    completed = subprocess.run(
        ["systemctl", "enable", service_name],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    return_code = int(completed.returncode) if completed.returncode is not None else 1
    if return_code == 0:
        return
    probe = subprocess.run(
        ["systemctl", "is-enabled", service_name],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    state = str(probe.stdout or probe.stderr or "").strip().lower()
    if "enabled" in state:
        return
    stdout = str(completed.stdout or "").strip()
    stderr = str(completed.stderr or "").strip()
    if stderr and stdout:
        detail = f"stdout: {stdout} | stderr: {stderr}"
    else:
        detail = stderr or stdout or f"exit code {return_code}"
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Echec commande systeme (systemctl enable {service_name}): {detail}",
    )


def _sync_reverse_proxy_runtime(*, reverse_proxy: str, public_url: str, upstream_port: int) -> str:
    normalized_proxy = _normalize_reverse_proxy_type(reverse_proxy)
    trimmed_public_url = str(public_url or "").strip()
    if normalized_proxy == "aucun":
        if not _should_skip_reverse_proxy_setup():
            _disable_reverse_proxy_service_if_present("nginx")
            _disable_reverse_proxy_service_if_present("caddy")
        return trimmed_public_url

    target_url, target_host = _extract_public_url_parts(trimmed_public_url)
    if _should_skip_reverse_proxy_setup():
        return target_url

    # Etat deterministe: on coupe les deux avant de relancer uniquement celui choisi.
    _disable_reverse_proxy_service_if_present("nginx")
    _disable_reverse_proxy_service_if_present("caddy")

    if normalized_proxy == "caddy":
        _configure_caddy_reverse_proxy(site_host=target_host, upstream_port=upstream_port)
        return target_url
    if normalized_proxy == "nginx":
        _configure_nginx_reverse_proxy(site_host=target_host, upstream_port=upstream_port)
        return target_url
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Type de reverse proxy non supporte.")


def _reverse_proxy_runtime_changed(
    *,
    current_settings: NotificationSettings,
    reverse_proxy: str,
    public_url: str,
    upstream_port: int,
) -> bool:
    return (
        _normalize_reverse_proxy_type(getattr(current_settings, "web_server_reverse_proxy_type", "aucun"))
        != _normalize_reverse_proxy_type(reverse_proxy)
        or str(getattr(current_settings, "web_server_public_url", "") or "").strip()
        != str(public_url or "").strip()
        or max(1, int(getattr(current_settings, "web_server_port", 8000) or 8000))
        != max(1, int(upstream_port or 8000))
    )


def _web_server_runtime_changed(
    *,
    current_settings: NotificationSettings,
    next_payload: dict,
    reverse_proxy: str,
    public_url: str,
) -> bool:
    return (
        str(getattr(current_settings, "web_server_host", "127.0.0.1") or "127.0.0.1").strip()
        != str(next_payload.get("web_server_host", "127.0.0.1") or "127.0.0.1").strip()
        or max(1, int(getattr(current_settings, "web_server_port", 8000) or 8000))
        != max(1, int(next_payload.get("web_server_port", 8000) or 8000))
        or bool(getattr(current_settings, "web_server_autostart", False))
        != bool(next_payload.get("web_server_autostart", False))
        or _normalize_reverse_proxy_type(getattr(current_settings, "web_server_reverse_proxy_type", "aucun"))
        != _normalize_reverse_proxy_type(reverse_proxy)
        or str(getattr(current_settings, "web_server_public_url", "") or "").strip()
        != str(public_url or "").strip()
    )


def _configure_caddy_reverse_proxy(*, site_host: str, upstream_port: int) -> None:
    _assert_binary_available("caddy", "caddy")
    caddyfile = Path(str(os.environ.get("NMP_CADDYFILE_PATH") or "/etc/caddy/Caddyfile").strip())
    caddyfile.parent.mkdir(parents=True, exist_ok=True)
    caddyfile.write_text(
        (
            f"{site_host} {{\n"
            f"    reverse_proxy 127.0.0.1:{int(upstream_port)}\n"
            f"    tls internal\n"
            f"}}\n"
        ),
        encoding="utf-8",
    )
    _enable_reverse_proxy_service_if_needed("caddy")
    _run_subprocess_checked(["systemctl", "restart", "caddy"], timeout=90)
    _run_subprocess_checked(["systemctl", "is-active", "--quiet", "caddy"], timeout=30)


def _ensure_self_signed_tls_for_nginx(*, site_host: str) -> tuple[Path, Path]:
    cert_dir = Path(str(os.environ.get("NMP_NGINX_TLS_DIR") or "/etc/itops/tls").strip())
    cert_dir.mkdir(parents=True, exist_ok=True)
    safe_host = re.sub(r"[^A-Za-z0-9_.-]", "_", site_host)
    cert_path = cert_dir / f"{safe_host}.crt"
    key_path = cert_dir / f"{safe_host}.key"
    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path
    _assert_binary_available("openssl", "openssl")
    _run_subprocess_checked(
        [
            "openssl",
            "req",
            "-x509",
            "-nodes",
            "-newkey",
            "rsa:2048",
            "-sha256",
            "-days",
            "825",
            "-subj",
            f"/CN={site_host}",
            "-addext",
            f"subjectAltName=DNS:{site_host}",
            "-keyout",
            str(key_path),
            "-out",
            str(cert_path),
        ],
        timeout=90,
    )
    try:
        key_path.chmod(0o600)
        cert_path.chmod(0o644)
    except Exception:
        pass
    return cert_path, key_path


def _configure_nginx_reverse_proxy(*, site_host: str, upstream_port: int) -> None:
    _assert_binary_available("nginx", "nginx")
    cert_path, key_path = _ensure_self_signed_tls_for_nginx(site_host=site_host)
    site_available = Path(str(os.environ.get("NMP_NGINX_SITE_PATH") or "/etc/nginx/sites-available/itops.conf").strip())
    site_enabled = Path(str(os.environ.get("NMP_NGINX_ENABLED_PATH") or "/etc/nginx/sites-enabled/itops.conf").strip())
    site_available.parent.mkdir(parents=True, exist_ok=True)
    site_enabled.parent.mkdir(parents=True, exist_ok=True)
    site_available.write_text(
        (
            "server {\n"
            "    listen 80;\n"
            f"    server_name {site_host};\n"
            "    return 301 https://$host$request_uri;\n"
            "}\n\n"
            "server {\n"
            "    listen 443 ssl;\n"
            f"    server_name {site_host};\n"
            f"    ssl_certificate {cert_path};\n"
            f"    ssl_certificate_key {key_path};\n"
            "    ssl_protocols TLSv1.2 TLSv1.3;\n"
            "    ssl_session_cache shared:SSL:10m;\n"
            "    ssl_session_timeout 1d;\n"
            "    location / {\n"
            f"        proxy_pass http://127.0.0.1:{int(upstream_port)};\n"
            "        proxy_set_header Host $host;\n"
            "        proxy_set_header X-Real-IP $remote_addr;\n"
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
            "        proxy_set_header X-Forwarded-Proto https;\n"
            "    }\n"
            "}\n"
        ),
        encoding="utf-8",
    )
    if site_enabled.exists() or site_enabled.is_symlink():
        try:
            site_enabled.unlink()
        except Exception:
            pass
    site_enabled.symlink_to(site_available)
    default_site = Path("/etc/nginx/sites-enabled/default")
    if default_site.exists() or default_site.is_symlink():
        try:
            default_site.unlink()
        except Exception:
            pass
    _run_subprocess_checked(["nginx", "-t"], timeout=60)
    _enable_reverse_proxy_service_if_needed("nginx")
    _run_subprocess_checked(["systemctl", "restart", "nginx"], timeout=90)
    _run_subprocess_checked(["systemctl", "is-active", "--quiet", "nginx"], timeout=30)


def _configure_reverse_proxy_from_setup(*, reverse_proxy: str, public_url: str, upstream_port: int) -> str:
    return _sync_reverse_proxy_runtime(
        reverse_proxy=reverse_proxy,
        public_url=public_url,
        upstream_port=upstream_port,
    )


def _register_setup_routes(app: FastAPI, get_services) -> None:
    @app.get("/setup/status", response_model=SetupStatusResponse)
    def setup_status(request: Request, api: ApiServices = Depends(get_services)) -> SetupStatusResponse:
        return _build_setup_status(api, request=request)

    @app.post("/setup/finalize", response_model=MessageResponse)
    def setup_finalize(payload: SetupFinalizeRequest, api: ApiServices = Depends(get_services)) -> MessageResponse:
        status_payload = _build_setup_status(api)
        if not status_payload.setup_required:
            return MessageResponse(message="Installation deja finalisee.", redirect_url="/portal")

        expected_token = read_setup_token()
        provided_token = str(payload.setup_token or "").strip()
        if expected_token and provided_token != expected_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token d'installation invalide.")

        admin_password = str(payload.admin_password or "").strip()
        if len(admin_password) < 8:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Mot de passe admin trop court (min 8).")
        root_password = str(payload.mariadb_root_password or "").strip()
        if len(root_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Mot de passe root MariaDB obligatoire (min 8).",
            )

        if not api.auth.has_admin_password():
            api.auth.set_admin_password(admin_password)

        _provision_local_mariadb_from_setup(payload)
        _verify_mariadb_application_login(payload, timeout_seconds=20)

        reverse_proxy = _normalize_reverse_proxy_type(payload.reverse_proxy_type)

        public_url = str(payload.url_publique or "").strip()
        if reverse_proxy != "aucun" and not public_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="URL publique obligatoire quand un reverse proxy est active.",
            )
        hebergement = HebergementWebConfig(
            hote_ecoute=str(payload.hote_ecoute or "0.0.0.0").strip() or "0.0.0.0",
            port_ecoute=int(payload.port_ecoute),
            demarrage_auto_service=True,
            utiliser_url_publique_reverse_proxy=bool(public_url),
            url_publique=public_url,
            reverse_proxy_actif=reverse_proxy != "aucun",
            reverse_proxy_type=reverse_proxy,
        )
        save_hebergement_web_config(hebergement)
        redirect_url = _configure_reverse_proxy_from_setup(
            reverse_proxy=reverse_proxy,
            public_url=public_url,
            upstream_port=int(payload.port_ecoute),
        )

        current_settings = api.settings_service.get()
        updated_settings = NotificationSettings(**current_settings.__dict__)
        updated_settings.web_server_host = hebergement.hote_ecoute
        updated_settings.web_server_port = hebergement.port_ecoute
        updated_settings.web_server_autostart = bool(hebergement.demarrage_auto_service)
        updated_settings.web_server_public_url = public_url
        updated_settings.web_server_use_public_url = reverse_proxy != "aucun"
        updated_settings.web_server_reverse_proxy_type = reverse_proxy
        api.settings_service.save(updated_settings)
        api.monitoring.apply_notification_settings(updated_settings)

        env_updates = {
            "NMP_MARIADB_HOST": str(payload.db_host or "127.0.0.1").strip() or "127.0.0.1",
            "NMP_MARIADB_PORT": str(int(payload.db_port)),
            "NMP_MARIADB_USER": str(payload.db_user or "itops").strip() or "itops",
            "NMP_MARIADB_PASSWORD": str(payload.db_password or "").strip(),
            "NMP_MARIADB_DATABASE": str(payload.db_name or "itops").strip() or "itops",
            "NMP_MARIADB_ROOT_PASSWORD": root_password,
            "NMP_HEBERGEMENT_CONFIG": str(default_hebergement_web_path()),
            "NMP_SETUP_CONFIG": str(default_setup_state_path()),
        }
        update_install_env(env_updates)

        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        save_setup_state(
            SetupInstallationState(
                completed=True,
                completed_at=now_iso,
                completed_by="wizard-web",
                reverse_proxy_type=reverse_proxy,
                public_url=public_url,
            )
        )
        remove_setup_token()
        resolved_redirect = str(redirect_url or "").strip() or "/portal"
        return MessageResponse(
            message=(
                "Installation finalisee (config ITops + MariaDB + reverse proxy appliquee). "
                "Vous pouvez ouvrir ITops via l'URL publique configuree."
            ),
            redirect_url=resolved_redirect,
        )


def _register_base_routes(app: FastAPI) -> None:
    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def web_portal_index(request: Request) -> Response:
        proxy_prefix = _resolve_switch_proxy_prefix_from_request(request)
        if proxy_prefix:
            switch_redirect_url = _resolve_switch_proxy_root_redirect_url(request=request, proxy_prefix=proxy_prefix)
            if switch_redirect_url:
                return RedirectResponse(
                    url=switch_redirect_url,
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                )
            return RedirectResponse(
                url="/portal",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            )
        services = app.state.services
        if _build_setup_status(services).setup_required:
            return FileResponse(WEB_DIR / "setup.html")
        return FileResponse(WEB_DIR / "portal.html")

    @app.get("/portal", include_in_schema=False)
    def web_portal_alias() -> FileResponse:
        services = app.state.services
        if _build_setup_status(services).setup_required:
            return RedirectResponse(url="/setup", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        return FileResponse(WEB_DIR / "portal.html")

    @app.get("/setup", include_in_schema=False)
    def web_setup_page() -> FileResponse:
        services = app.state.services
        if not _build_setup_status(services).setup_required:
            return RedirectResponse(url="/portal", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        return FileResponse(WEB_DIR / "setup.html")

    @app.get("/monitoring", include_in_schema=False)
    def web_app_index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/monitoring/", include_in_schema=False)
    def web_app_index_slash() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(FAVICON_PATH)


def _register_auth_routes(app: FastAPI, get_services, get_bearer_token, require_session) -> None:
    @app.get("/auth/status", response_model=AuthStatusResponse)
    def auth_status(api: ApiServices = Depends(get_services)) -> AuthStatusResponse:
        return AuthStatusResponse(
            has_admin_password=api.auth.has_admin_password(),
            first_start_required=api.auth.first_start_required(),
        )

    @app.post("/auth/bootstrap", response_model=MessageResponse)
    def bootstrap_admin_password(
        payload: BootstrapPasswordRequest,
        api: ApiServices = Depends(get_services),
        authorization: Optional[str] = Header(default=None),
    ) -> MessageResponse:
        if api.auth.has_admin_password():
            token = get_bearer_token(authorization)
            session = api.auth.get_session(token)
            if session is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Initialisation deja effectuee.")
        api.auth.set_admin_password(payload.password)
        return MessageResponse(message="Mot de passe administrateur configure.")

    @app.post("/auth/login", response_model=TokenResponse)
    def login(payload: LoginRequest, api: ApiServices = Depends(get_services)) -> TokenResponse:
        try:
            session = api.auth.login(
                payload.password,
                username=payload.username,
                new_password=payload.new_password,
            )
        except PasswordChangeRequiredError as exc:
            raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        if session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides.")
        return TokenResponse(access_token=session.token, expires_at=session.expires_at.isoformat())

    @app.post("/auth/logout", response_model=MessageResponse)
    def logout(
        token: str = Depends(get_bearer_token),
        api: ApiServices = Depends(get_services),
    ) -> MessageResponse:
        if not api.auth.logout(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expiree.")
        return MessageResponse(message="Deconnexion effectuee.")

    @app.get("/auth/me", response_model=SessionInfoResponse)
    def auth_me(session=Depends(require_session)) -> SessionInfoResponse:
        return SessionInfoResponse(subject=session.subject, expires_at=session.expires_at.isoformat())

    def _resolve_session_profile(*, api: ApiServices, subject: str) -> SessionProfileResponse:
        normalized_subject = str(subject or "").strip().lower()
        label = normalized_subject
        role_code = ""
        role_label = ""
        list_users = getattr(api.logs, "list_auth_users", None)
        list_roles = getattr(api.logs, "list_auth_roles", None)
        try:
            if callable(list_users):
                users = list_users()
                user = next((row for row in users if str(row.get("subject") or "").strip().lower() == normalized_subject), None)
                if isinstance(user, dict):
                    label = str(user.get("label") or label).strip() or label
                    role_code = str((user.get("role_codes") or [""])[0] or "").strip().lower()
            if callable(list_roles) and role_code:
                roles = list_roles()
                role = next((row for row in roles if str(row.get("code") or "").strip().lower() == role_code), None)
                if isinstance(role, dict):
                    role_label = str(role.get("label") or "").strip()
        except Exception:
            pass
        if not role_code:
            checker = getattr(api.logs, "subject_has_module", None)
            if callable(checker):
                try:
                    if bool(checker(subject=normalized_subject, module_code="admin")):
                        role_code = "admin"
                except Exception:
                    pass
        if not role_code:
            role_code = "admin" if normalized_subject in {"sa", "admin"} else "user"
        if not role_label:
            role_label = role_code.capitalize()
        return SessionProfileResponse(
            subject=normalized_subject,
            label=label,
            role_code=role_code,
            role_label=role_label,
        )

    def _resolve_session_modules(*, api: ApiServices, subject: str) -> list[ModuleAccessResponse]:
        lister = getattr(api.logs, "list_subject_modules", None)
        if callable(lister):
            rows = lister(subject=str(subject))
        else:
            rows = [
                {
                    "code": "monitoring",
                    "label": "Monitoring",
                    "route_path": "/monitoring",
                    "is_active": True,
                    "granted": str(subject).strip().lower() in {"sa", "admin"},
                }
            ]
        latest_cache = getattr(api.logs, "latest_sync_source_cache_timestamp", None)
        latest_records = getattr(api.logs, "latest_custom_service_record_sync_timestamp", None)
        counter_cache = getattr(api.logs, "count_sync_source_cache_entries", None)
        counter_records = getattr(api.logs, "count_custom_service_records", None)
        if callable(latest_cache) or callable(latest_records) or callable(counter_cache) or callable(counter_records):
            sync_targets = {
                "directory_agents": ("cache", "users"),
                "directory_services": ("cache", "organizational_units"),
                "service_emails": ("records", "emails"),
            }
            enriched_rows = []
            for row in list(rows or []):
                payload = dict(row or {})
                code = str(payload.get("code") or "").strip().lower()
                sync_kind, sync_target = sync_targets.get(code, ("", ""))
                service_code = ""
                route_path = str(payload.get("route_path") or "")
                if route_path.startswith("/#service="):
                    service_code = route_path.removeprefix("/#service=").strip().lower()
                elif code.startswith("service_") and code != "service_emails":
                    service_code = code.removeprefix("service_").strip().lower()
                try:
                    if sync_kind == "cache" and callable(latest_cache):
                        payload["last_sync_at"] = latest_cache(source_kind="active_directory", target_kind=sync_target)
                    elif sync_kind == "records" and callable(latest_records):
                        payload["last_sync_at"] = latest_records(
                            service_code=sync_target,
                            source_kind="active_directory",
                            target_kind="email_accounts",
                        )
                except Exception:
                    payload["last_sync_at"] = ""
                try:
                    if sync_kind == "cache" and callable(counter_cache):
                        payload["item_count"] = counter_cache(source_kind="active_directory", target_kind=sync_target)
                    elif sync_kind == "records" and callable(counter_records):
                        payload["item_count"] = counter_records(service_code=sync_target)
                    elif service_code and callable(counter_records):
                        payload["item_count"] = counter_records(service_code=service_code)
                except Exception:
                    payload["item_count"] = 0
                try:
                    raw_tile_config = str(payload.pop("treeview_config", "") or "")
                    tile_config = json.loads(raw_tile_config) if raw_tile_config else {}
                    payload["tile_config"] = tile_config.get("tile") if isinstance(tile_config.get("tile"), dict) else {}
                except Exception:
                    payload["tile_config"] = {}
                enriched_rows.append(payload)
            rows = enriched_rows
        return [ModuleAccessResponse(**row) for row in rows]

    @app.get("/auth/me/profile", response_model=SessionProfileResponse)
    def auth_me_profile(
        session=Depends(require_session),
        api: ApiServices = Depends(get_services),
    ) -> SessionProfileResponse:
        return _resolve_session_profile(api=api, subject=str(session.subject or ""))

    @app.get("/auth/me/modules", response_model=list[ModuleAccessResponse])
    def auth_me_modules(
        session=Depends(require_session),
        api: ApiServices = Depends(get_services),
    ) -> list[ModuleAccessResponse]:
        return _resolve_session_modules(api=api, subject=str(session.subject or ""))

    @app.get("/auth/me/context", response_model=SessionContextResponse)
    def auth_me_context(
        session=Depends(require_session),
        api: ApiServices = Depends(get_services),
    ) -> SessionContextResponse:
        profile = _resolve_session_profile(api=api, subject=str(session.subject or ""))
        modules = _resolve_session_modules(api=api, subject=str(session.subject or ""))
        return SessionContextResponse(
            subject=profile.subject,
            label=profile.label,
            role_code=profile.role_code,
            role_label=profile.role_label,
            modules=modules,
        )


def _stable_version_token(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]


def _assert_version_token(*, expected: str, received: str, resource_label: str) -> None:
    normalized_received = str(received or "").strip()
    if not normalized_received:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflit de modification: token de version manquant pour {resource_label}. Recharge la vue puis recommence.",
        )
    if normalized_received == str(expected or "").strip():
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Conflit de modification: {resource_label} a ete modifie par un autre utilisateur. Recharge la vue puis recommence.",
    )


def _device_version_source(row: dict) -> dict:
    payload = dict(row or {})
    return {
        "id": str(payload.get("id") or ""),
        "device_type": str(payload.get("device_type") or payload.get("type") or ""),
        "name": str(payload.get("name") or ""),
        "ip": str(payload.get("ip") or ""),
        "description": str(payload.get("description") or ""),
        "notify": bool(payload.get("notify", True)),
        "id_Teamviewer": str(payload.get("id_Teamviewer") or ""),
        "device_subtype": str(payload.get("device_subtype") or payload.get("type") or ""),
        "action_double_click": str(payload.get("action_double_click") or ""),
        "web_url": str(payload.get("web_url") or ""),
        "ssh_user": str(payload.get("ssh_user") or ""),
        "custom_data": {
            str(key): str(value or "")
            for key, value in dict(payload.get("custom_data") or {}).items()
        },
    }


def _device_version_token(row: dict) -> str:
    return _stable_version_token(_device_version_source(row))


def _with_device_version_token(row: dict) -> dict:
    payload = dict(row or {})
    payload["device_subtype"] = str(payload.get("device_subtype") or payload.get("type") or "")
    payload["version_token"] = _device_version_token(payload)
    return payload


def _type_version_source(row: dict) -> dict:
    payload = dict(row or {})
    return {
        "code": str(payload.get("code") or ""),
        "label": str(payload.get("label") or ""),
        "icon": str(payload.get("icon") or ""),
        "monitoring_enabled": bool(payload.get("monitoring_enabled", True)),
        "config_backups_enabled": payload.get("config_backups_enabled", None),
        "is_system": bool(payload.get("is_system", False)),
        "sort_order": int(payload.get("sort_order") or 0),
    }


def _type_version_token(row: dict) -> str:
    return _stable_version_token(_type_version_source(row))


def _with_type_version_token(row: dict) -> dict:
    payload = dict(row or {})
    payload["version_token"] = _type_version_token(payload)
    return payload


def _schema_version_token(*, fields: list[dict], actions: list[dict]) -> str:
    normalized = {
        "fields": [dict(item or {}) for item in list(fields or [])],
        "actions": [dict(item or {}) for item in list(actions or [])],
    }
    return _stable_version_token(normalized)


def _role_version_token(row: dict) -> str:
    payload = dict(row or {})
    return _stable_version_token(
        {
            "code": str(payload.get("code") or ""),
            "label": str(payload.get("label") or ""),
            "is_system": bool(payload.get("is_system", False)),
            "sort_order": int(payload.get("sort_order") or 0),
            "module_codes": sorted(str(item or "") for item in list(payload.get("module_codes") or [])),
        }
    )


def _with_role_version_token(row: dict) -> dict:
    payload = dict(row or {})
    payload["version_token"] = _role_version_token(payload)
    return payload


def _user_version_token(row: dict) -> str:
    payload = dict(row or {})
    return _stable_version_token(
        {
            "subject": str(payload.get("subject") or ""),
            "label": str(payload.get("label") or ""),
            "is_active": bool(payload.get("is_active", True)),
            "must_change_password": bool(payload.get("must_change_password", False)),
            "role_codes": sorted(str(item or "") for item in list(payload.get("role_codes") or [])),
        }
    )


def _with_user_version_token(row: dict) -> dict:
    payload = dict(row or {})
    payload["version_token"] = _user_version_token(payload)
    return payload


def _custom_service_version_token(row: dict) -> str:
    payload = dict(row or {})
    fields = [dict(item or {}) for item in list(payload.get("fields") or [])]
    return _stable_version_token(
        {
            "code": str(payload.get("code") or ""),
            "label": str(payload.get("label") or ""),
            "is_active": bool(payload.get("is_active", True)),
            "is_technical": bool(payload.get("is_technical", False)),
            "credentials_enabled": bool(payload.get("credentials_enabled", False)),
            "child_enabled": bool(payload.get("child_enabled", False)),
            "child_label": str(payload.get("child_label") or ""),
            "sort_order": int(payload.get("sort_order") or 0),
            "icon": str(payload.get("icon") or ""),
            "color": str(payload.get("color") or ""),
            "tile_config": dict(payload.get("tile_config") or {}),
            "relationship_inheritance": dict(payload.get("relationship_inheritance") or {}),
            "fields": fields,
        }
    )


def _with_custom_service_version_token(row: dict) -> dict:
    payload = dict(row or {})
    payload["version_token"] = _custom_service_version_token(payload)
    return payload


def _custom_service_record_version_token(row: dict) -> str:
    payload = dict(row or {})
    values = {
        str(key): value
        for key, value in dict(payload.get("values") or {}).items()
        if str(key) not in {"agents_lies", "services_deduits"}
    }
    return _stable_version_token(
        {
            "id": str(payload.get("id") or ""),
            "service_code": str(payload.get("service_code") or ""),
            "values": values,
            "children": [dict(item or {}) for item in list(payload.get("children") or [])],
            "created_at": str(payload.get("created_at") or ""),
            "updated_at": str(payload.get("updated_at") or ""),
        }
    )


def _with_custom_service_record_version_token(row: dict) -> dict:
    payload = dict(row or {})
    payload["version_token"] = _custom_service_record_version_token(payload)
    return payload


CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY = "device_login"
CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY = "device_password"
CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS = (
    CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY,
    CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY,
    "login",
    "password",
)


def _extract_custom_service_credential_values(values: dict[str, object] | None, *, enabled: bool) -> dict[str, str]:
    if not enabled or not isinstance(values, dict):
        return {}
    output: dict[str, str] = {}
    if CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY in values or "login" in values:
        output[CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY] = str(values.get(CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY) or values.get("login") or "").strip()
    if CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY in values or "password" in values:
        raw_password = str(values.get(CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY) or values.get("password") or "")
        if raw_password:
            output[CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY] = raw_password
    return output


def _custom_service_record_response_payload(row: dict, *, credentials_enabled: bool) -> dict:
    payload = _with_custom_service_record_version_token(row)
    values = dict(payload.get("values") or {})
    has_password = False
    if credentials_enabled:
        has_password = bool(str(values.get(CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY) or values.get("password") or "").strip())
        values.pop(CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY, None)
        values.pop("password", None)
    payload["values"] = values
    payload["has_credential_password"] = has_password
    payload["credential_password_masked"] = "********" if has_password else ""
    return payload


def _device_schema_supports_credentials(fields: list[dict]) -> bool:
    keys = {
        str(field.get("field_key") or "").strip().lower()
        for field in list(fields or [])
        if isinstance(field, dict)
    }
    return "device_login" in keys and "device_password" in keys


def _sanitize_device_import_preview_rows(rows: list[dict]) -> list[dict]:
    sanitized_rows: list[dict] = []
    for row in list(rows or []):
        payload = dict(row or {})
        if "device_password" in payload:
            payload["device_password"] = ""
        sanitized_rows.append(payload)
    return sanitized_rows


def _format_device_import_row_error(*, name: str, ip: str, exc: Exception) -> str:
    label = str(name or ip or "Ligne").strip()
    raw = str(exc or "").strip()
    lowered = raw.lower()
    if "adresse ip deja utilisee" in lowered or "duplicate" in lowered:
        reason = "adresse IP deja utilisee par un autre equipement"
    elif "incorrect string value" in lowered or "data too long" in lowered:
        reason = "une valeur est trop longue ou contient un caractere non accepte par la base"
    elif "cannot add or update" in lowered or "foreign key" in lowered:
        reason = "reference invalide dans la base"
    elif raw:
        reason = raw
    else:
        reason = "erreur d'enregistrement inconnue"
    return f"{label} ({ip}): import impossible - {reason}."


def _sync_imported_device_custom_fields_to_schema(
    *,
    api: ApiServices,
    device_type: str,
    custom_data: dict[str, object],
    schema_cache: dict[str, tuple[list[dict], list[dict]]],
) -> int:
    normalized_type = str(device_type or "").strip().lower()
    if not normalized_type or not isinstance(custom_data, dict) or not custom_data:
        return 0
    fields, actions = schema_cache.get(normalized_type) or api.device_types.load_schema(normalized_type)
    existing_keys = {
        str(field.get("field_key") or "").strip().lower()
        for field in list(fields or [])
        if isinstance(field, dict)
    }
    next_sort = max([int(field.get("sort_order") or 0) for field in list(fields or []) if isinstance(field, dict)] or [0])
    added = 0
    next_fields = [dict(field or {}) for field in list(fields or [])]
    for index, key in enumerate(dict(custom_data or {}).keys()):
        label = str(key or "").strip()
        if not label:
            continue
        field_key = normalize_field_key(field_key=key, label=label, index=index)
        if not field_key or field_key.lower() in existing_keys:
            continue
        next_sort += 10
        next_fields.append(
            {
                "field_key": field_key,
                "label": field_key.replace("_", " ").strip().capitalize() or field_key,
                "field_kind": "text",
                "required": False,
                "options": "",
                "default_value": "",
                "show_in_table": True,
                "sort_order": next_sort,
            }
        )
        existing_keys.add(field_key.lower())
        added += 1
    if added:
        api.device_types.replace_schema(type_code=normalized_type, fields=next_fields, actions=actions)
        schema_cache[normalized_type] = api.device_types.load_schema(normalized_type)
    else:
        schema_cache[normalized_type] = (fields, actions)
    return added


def _custom_service_import_contains_credentials(values: dict[str, object] | None) -> bool:
    source = values if isinstance(values, dict) else {}
    for key in (
        CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY,
        CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY,
        "login",
        "password",
    ):
        if str(source.get(key) or "").strip():
            return True
    return False


def _shared_list_version_token(row: dict) -> str:
    payload = dict(row or {})
    return _stable_version_token(
        {
            "code": str(payload.get("code") or ""),
            "label": str(payload.get("label") or ""),
            "is_system": bool(payload.get("is_system", False)),
            "sort_order": int(payload.get("sort_order") or 0),
            "item_count": int(payload.get("item_count") or 0),
        }
    )


def _with_shared_list_version_token(row: dict) -> dict:
    payload = dict(row or {})
    payload["version_token"] = _shared_list_version_token(payload)
    return payload


def _shared_list_item_version_token(row: dict) -> str:
    payload = dict(row or {})
    return _stable_version_token(
        {
            "list_code": str(payload.get("list_code") or ""),
            "code": str(payload.get("code") or ""),
            "label": str(payload.get("label") or ""),
            "is_active": bool(payload.get("is_active", True)),
            "sort_order": int(payload.get("sort_order") or 0),
        }
    )


def _with_shared_list_item_version_token(row: dict) -> dict:
    payload = dict(row or {})
    payload["version_token"] = _shared_list_item_version_token(payload)
    return payload


def _decode_base64_payload(*, content_base64: object) -> bytes:
    try:
        return base64.b64decode(str(content_base64 or ""), validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Contenu base64 invalide: {exc}") from exc


def _backup_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _safe_unlink(path: str | Path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


def _database_cli_env(manager) -> dict[str, str]:
    env = dict(os.environ)
    password = str(getattr(manager, "password", "") or "")
    if password:
        env["MYSQL_PWD"] = password
    return env


def _database_cli_base_args(manager) -> list[str]:
    db_name = str(getattr(manager, "db_name", "") or "").strip()
    if not db_name:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Nom de base MariaDB indisponible.")
    return [
        "--host",
        str(getattr(manager, "host", "127.0.0.1") or "127.0.0.1"),
        "--port",
        str(int(getattr(manager, "port", 3306) or 3306)),
        "--user",
        str(getattr(manager, "user", "root") or "root"),
        "--default-character-set=utf8mb4",
    ]


def _database_cli_candidates(binary_name: str) -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        normalized = str(path).lower()
        if normalized in seen:
            return
        seen.add(normalized)
        candidates.append(path)

    aliases = {
        "mysqldump": ["mysqldump", "mariadb-dump"],
        "mysql": ["mysql", "mariadb"],
    }.get(binary_name, [binary_name])
    suffixes: list[str] = []
    for alias in aliases:
        if os.name == "nt" and not alias.lower().endswith(".exe"):
            suffixes.append(f"{alias}.exe")
        suffixes.append(alias)

    for env_key in ("NMP_MARIADB_BIN_DIR", "MARIADB_BIN_DIR", "MYSQL_BIN_DIR"):
        raw_dir = str(os.environ.get(env_key) or "").strip()
        if raw_dir:
            for suffix in suffixes:
                add(Path(raw_dir) / suffix)

    for env_key in ("MARIADB_HOME", "MYSQL_HOME"):
        raw_home = str(os.environ.get(env_key) or "").strip()
        if raw_home:
            for suffix in suffixes:
                add(Path(raw_home) / "bin" / suffix)

    if os.name == "nt":
        roots = [
            Path(os.environ.get("ProgramFiles") or r"C:\Program Files"),
            Path(os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)"),
        ]
        for root in roots:
            for pattern in ("MariaDB *", "MySQL *", "MySQL Server *"):
                try:
                    dirs = sorted(root.glob(pattern), reverse=True)
                except Exception:
                    dirs = []
                for directory in dirs:
                    for suffix in suffixes:
                        add(directory / "bin" / suffix)

    return candidates


def _require_database_cli(binary_name: str) -> str:
    resolved = shutil.which(binary_name)
    if not resolved:
        for candidate in _database_cli_candidates(binary_name):
            if candidate.is_file():
                return str(candidate)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Client MariaDB '{binary_name}' introuvable. "
                "Installe le client MariaDB sur le serveur applicatif ou renseigne NMP_MARIADB_BIN_DIR."
            ),
        )
    return resolved


def _create_database_backup_file(manager) -> Path:
    ensure_database = getattr(manager, "_ensure_database", None)
    if not callable(ensure_database):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Sauvegarde BDD disponible uniquement avec MariaDB.")
    ensure_database()
    try:
        mysqldump = _require_database_cli("mysqldump")
    except HTTPException as exc:
        if exc.status_code != status.HTTP_503_SERVICE_UNAVAILABLE:
            raise
        return _create_database_backup_file_with_pymysql(manager)
    db_name = str(getattr(manager, "db_name", "") or "").strip()
    fd, raw_path = tempfile.mkstemp(prefix="itops-db-", suffix=".sql")
    path = Path(raw_path)
    try:
        with os.fdopen(fd, "wb") as output:
            result = subprocess.run(
                [
                    mysqldump,
                    *_database_cli_base_args(manager),
                    "--single-transaction",
                    "--routines",
                    "--events",
                    "--triggers",
                    db_name,
                ],
                stdout=output,
                stderr=subprocess.PIPE,
                env=_database_cli_env(manager),
                timeout=1800,
                check=False,
                **windows_no_window_kwargs(),
            )
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip() or "mysqldump a echoue."
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
        return path
    except Exception:
        _safe_unlink(path)
        raise


def _sql_dump_value(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, bytes | bytearray):
        return "X'" + bytes(value).hex() + "'"
    if isinstance(value, datetime):
        return _quote_sql_literal(value.strftime("%Y-%m-%d %H:%M:%S"))
    return _quote_sql_literal(str(value))


def _create_database_backup_file_with_pymysql(manager) -> Path:
    connect = getattr(manager, "_connect", None)
    if not callable(connect):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Connexion MariaDB indisponible pour la sauvegarde.")
    db_name = str(getattr(manager, "db_name", "") or "").strip()
    fd, raw_path = tempfile.mkstemp(prefix="itops-db-", suffix=".sql")
    path = Path(raw_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
            output.write("-- ITops database backup\n")
            output.write(f"-- Database: {db_name}\n")
            output.write(f"-- Generated UTC: {_backup_timestamp()}\n\n")
            output.write("SET FOREIGN_KEY_CHECKS=0;\n")
            output.write("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n")
            output.write("SET NAMES utf8mb4;\n\n")
            with connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
                    tables = [str(row[0] or "") for row in cursor.fetchall() if str(row[0] or "")]
                    for table_name in tables:
                        table_sql = _quote_sql_identifier(table_name)
                        cursor.execute(f"SHOW CREATE TABLE {table_sql}")
                        create_row = cursor.fetchone()
                        create_sql = str(create_row[1] if create_row and len(create_row) > 1 else "")
                        if not create_sql:
                            continue
                        output.write(f"DROP TABLE IF EXISTS {table_sql};\n")
                        output.write(f"{create_sql};\n\n")
                        cursor.execute(f"SELECT * FROM {table_sql}")
                        columns = [_quote_sql_identifier(str(column[0] or "")) for column in cursor.description or []]
                        if not columns:
                            continue
                        while True:
                            rows = cursor.fetchmany(250)
                            if not rows:
                                break
                            values = [
                                "(" + ", ".join(_sql_dump_value(value) for value in row) + ")"
                                for row in rows
                            ]
                            output.write(f"INSERT INTO {table_sql} ({', '.join(columns)}) VALUES\n")
                            output.write(",\n".join(values))
                            output.write(";\n")
                        output.write("\n")
            output.write("SET FOREIGN_KEY_CHECKS=1;\n")
        return path
    except Exception:
        _safe_unlink(path)
        raise


def _restore_database_backup(manager, *, raw_bytes: bytes, filename: str) -> None:
    ensure_database = getattr(manager, "_ensure_database", None)
    if not callable(ensure_database):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Import BDD disponible uniquement avec MariaDB.")
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Fichier de sauvegarde vide.")
    safe_filename = str(filename or "backup.sql").strip().lower()
    if safe_filename and not safe_filename.endswith((".sql", ".dump", ".txt")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Format attendu: fichier SQL.")
    ensure_database()
    try:
        mysql = _require_database_cli("mysql")
    except HTTPException as exc:
        if exc.status_code != status.HTTP_503_SERVICE_UNAVAILABLE:
            raise
        _restore_database_backup_with_pymysql(manager, raw_bytes=raw_bytes)
        return
    db_name = str(getattr(manager, "db_name", "") or "").strip()
    fd, raw_path = tempfile.mkstemp(prefix="itops-db-import-", suffix=".sql")
    path = Path(raw_path)
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(raw_bytes)
        with path.open("rb") as input_file:
            result = subprocess.run(
                [mysql, *_database_cli_base_args(manager), db_name],
                stdin=input_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_database_cli_env(manager),
                timeout=1800,
                check=False,
                **windows_no_window_kwargs(),
            )
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip() or "mysql a echoue pendant l'import."
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
    finally:
        _safe_unlink(path)


def _split_sql_script(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    quote = ""
    escape = False
    line_comment = False
    block_comment = False
    index = 0
    while index < len(script):
        char = script[index]
        next_char = script[index + 1] if index + 1 < len(script) else ""
        if line_comment:
            if char in "\r\n":
                line_comment = False
                current.append(char)
            index += 1
            continue
        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote:
            current.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = ""
            index += 1
            continue
        if char == "-" and next_char == "-":
            line_comment = True
            index += 2
            continue
        if char == "/" and next_char == "*":
            block_comment = True
            index += 2
            continue
        if char in {"'", '"', "`"}:
            quote = char
            current.append(char)
            index += 1
            continue
        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def _restore_database_backup_with_pymysql(manager, *, raw_bytes: bytes) -> None:
    connect = getattr(manager, "_connect", None)
    if not callable(connect):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Connexion MariaDB indisponible pour l'import.")
    try:
        script = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        script = raw_bytes.decode("latin-1")
    statements = _split_sql_script(script)
    if not statements:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sauvegarde SQL vide ou invalide.")
    try:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                for statement in statements:
                    normalized = statement.strip()
                    if not normalized:
                        continue
                    if normalized.upper().startswith("DELIMITER "):
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Import SQL avec DELIMITER non supporte sans client mysql.",
                        )
                    cursor.execute(normalized)
                cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Import SQL echoue: {exc}") from exc


def _csv_stream_response(*, csv_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _sanitize_download_stem(value: object, fallback: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return str(fallback or "download")
    normalized = unicodedata.normalize("NFD", raw)
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", without_marks)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or str(fallback or "download")


def _resolve_device_web_url(*, device_ip: str, subtype: str, web_url: str) -> str:
    ip = str(device_ip or "").strip()
    normalized_subtype = str(subtype or "").strip().lower()
    raw = str(web_url or "").strip()
    if not raw:
        if not ip:
            return ""
        return f"http://{ip}:5000" if normalized_subtype == "dsm" else f"http://{ip}"
    numeric = re.fullmatch(r":?(\d{1,5})", raw)
    if numeric:
        port = int(numeric.group(1))
        return f"http://{ip}:{port}" if ip and 1 <= port <= 65535 else ""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        return raw
    if re.match(r"^[^/\s:]+:\d{1,5}(?:[/?#]|$)", raw):
        return f"http://{raw}"
    if raw.startswith("/") and ip:
        return f"http://{ip}{raw}"
    return raw


def _build_rdp_shortcut_content(*, device_name: str, device_ip: str) -> bytes:
    label = str(device_name or device_ip or "Remote Desktop").strip()
    ip = str(device_ip or "").strip()
    content = "\r\n".join(
        [
            "screen mode id:i:2",
            "use multimon:i:0",
            "desktopwidth:i:1920",
            "desktopheight:i:1080",
            "session bpp:i:32",
            "compression:i:1",
            "keyboardhook:i:2",
            "audiocapturemode:i:0",
            "videoplaybackmode:i:1",
            "connection type:i:7",
            "networkautodetect:i:1",
            "bandwidthautodetect:i:1",
            "displayconnectionbar:i:1",
            "disable wallpaper:i:0",
            "allow font smoothing:i:1",
            "allow desktop composition:i:1",
            "prompt for credentials:i:1",
            f"full address:s:{ip}",
            f"alternate full address:s:{ip}",
            f"remoteapplicationname:s:{label}",
        ]
    )
    return content.encode("utf-8")


def _build_rdp_shortcut_filename(*, device_name: str, device_ip: str) -> str:
    name_part = _sanitize_download_stem(device_name, "remote")
    ip_part = _sanitize_download_stem(device_ip, "host")
    return f"{name_part}_{ip_part}.rdp"


_SWITCH_PROXY_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
_SWITCH_PROXY_TOKEN_COOKIE = "itops_switch_proxy_token"
_SWITCH_PROXY_PREFIX_COOKIE = "itops_switch_proxy_prefix"
_SWITCH_PROXY_IMAGE_DOWNLOAD_STARTED_COOKIE = "itops_switch_proxy_image_download_started"
_SWITCH_PROXY_PREFIX_ROOTS = (
    "/web/",
    "/Web/",
    "/htdocs/",
    "/device/",
    "/html/",
    "/cgi/",
    "/cgi-bin/",
    "/xsl/",
    "/wcn/",
    "/wnm/",
    "/[lang]/",
    "/en/",
    "/cn/",
    "/images/",
    "/nextgen/",
    "/customdir/",
    "/skin/",
)
_SWITCH_PROXY_MAX_CONCURRENT_PER_DEVICE = max(1, int(os.getenv("NMP_SWITCH_PROXY_MAX_CONCURRENT_PER_DEVICE", "4")))
_SWITCH_PROXY_DEVICE_SEMAPHORES: dict[str, asyncio.Semaphore] = {}
_SWITCH_PROXY_DEVICE_SEMAPHORES_LOCK = threading.Lock()
_SWITCH_PROXY_CLIENT_LIMITS = httpx.Limits(max_connections=256, max_keepalive_connections=64)
_SWITCH_PROXY_HTTP_CLIENT: httpx.AsyncClient | None = None
_SWITCH_PROXY_HTTP_CLIENT_LOCK = threading.Lock()
_SWITCH_PROXY_RECENT_DOWNLOAD_TTL_SECONDS = 180.0
_SWITCH_PROXY_IMAGE_COMPLETE_DELAY_SECONDS = max(
    1.0,
    float(os.getenv("NMP_SWITCH_PROXY_IMAGE_COMPLETE_DELAY_SECONDS", "60")),
)
_SWITCH_PROXY_RECENT_DOWNLOADS: dict[str, float] = {}
_SWITCH_PROXY_RECENT_DOWNLOADS_LOCK = threading.Lock()


def _set_switch_proxy_http_client(client: httpx.AsyncClient | None) -> None:
    global _SWITCH_PROXY_HTTP_CLIENT
    with _SWITCH_PROXY_HTTP_CLIENT_LOCK:
        _SWITCH_PROXY_HTTP_CLIENT = client


def _get_switch_proxy_http_client() -> httpx.AsyncClient | None:
    with _SWITCH_PROXY_HTTP_CLIENT_LOCK:
        return _SWITCH_PROXY_HTTP_CLIENT


def _get_switch_proxy_device_semaphore(device_key: str) -> asyncio.Semaphore:
    key = str(device_key or "").strip().lower()
    if not key:
        key = "__default__"
    with _SWITCH_PROXY_DEVICE_SEMAPHORES_LOCK:
        existing = _SWITCH_PROXY_DEVICE_SEMAPHORES.get(key)
        if existing is not None:
            return existing
        created = asyncio.Semaphore(_SWITCH_PROXY_MAX_CONCURRENT_PER_DEVICE)
        _SWITCH_PROXY_DEVICE_SEMAPHORES[key] = created
        return created


def _mark_switch_proxy_download_completed(device_key: str) -> None:
    key = str(device_key or "").strip().lower()
    if not key:
        return
    now = time.monotonic()
    with _SWITCH_PROXY_RECENT_DOWNLOADS_LOCK:
        expired = [
            item_key
            for item_key, timestamp in _SWITCH_PROXY_RECENT_DOWNLOADS.items()
            if now - float(timestamp or 0.0) > _SWITCH_PROXY_RECENT_DOWNLOAD_TTL_SECONDS
        ]
        for item_key in expired:
            _SWITCH_PROXY_RECENT_DOWNLOADS.pop(item_key, None)
        _SWITCH_PROXY_RECENT_DOWNLOADS[key] = now


def _has_recent_switch_proxy_download(device_key: str) -> bool:
    key = str(device_key or "").strip().lower()
    if not key:
        return False
    now = time.monotonic()
    with _SWITCH_PROXY_RECENT_DOWNLOADS_LOCK:
        timestamp = _SWITCH_PROXY_RECENT_DOWNLOADS.get(key)
        if timestamp is None:
            return False
        if now - float(timestamp or 0.0) > _SWITCH_PROXY_RECENT_DOWNLOAD_TTL_SECONDS:
            _SWITCH_PROXY_RECENT_DOWNLOADS.pop(key, None)
            return False
        return True


def _resolve_switch_proxy_session(
    *,
    api: ApiServices,
    authorization: str | None,
    token: str | None,
    cookie_token: str | None = None,
):
    bearer = str(authorization or "").strip()
    resolved_token = ""
    if bearer:
        if not bearer.lower().startswith("bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Bearer manquant.")
        resolved_token = bearer[7:].strip()
        if not resolved_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton d'acces manquant.")
        token_candidates = [resolved_token]
    else:
        token_candidates = []
        for candidate in (str(cookie_token or "").strip(), str(token or "").strip()):
            if candidate and candidate not in token_candidates:
                token_candidates.append(candidate)
    if not token_candidates:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton d'acces manquant.")
    session = None
    for candidate in token_candidates:
        session = api.auth.get_session(candidate)
        if session is not None:
            break
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expiree.")
    checker = getattr(api.logs, "subject_has_module", None)
    if callable(checker):
        allowed = bool(checker(subject=str(session.subject), module_code="monitoring"))
    else:
        allowed = str(session.subject).strip().lower() in {"sa", "admin"}
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse pour le module 'monitoring'.")
    return session


def _switch_proxy_session_cookie_value(session) -> str:
    return str(getattr(session, "token", "") or "").strip()


def _resolve_switch_base_url(device: dict) -> urllib.parse.SplitResult:
    ip = str(device.get("ip") or "").strip()
    subtype = str(device.get("device_subtype") or device.get("type") or "").strip().lower()
    configured_web_url = str(device.get("web_url") or "").strip()
    raw = _resolve_device_web_url(device_ip=ip, subtype=subtype, web_url=configured_web_url) if configured_web_url else ""
    if not raw:
        if not ip:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="IP de l'equipement manquante.")
        if subtype == "dsm":
            raw = f"http://{ip}:5000"
        else:
            raw = f"http://{ip}"
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = f"http://{raw}"
    parsed = urllib.parse.urlsplit(raw)
    scheme = str(parsed.scheme or "").strip().lower()
    if scheme not in {"http", "https"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="URL web invalide (http/https uniquement).")
    host = str(parsed.hostname or "").strip().lower()
    if not host:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="URL web invalide (hote manquant).")
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="URL web invalide pour un acces distant.")
    path = str(parsed.path or "/")
    if not path.startswith("/"):
        path = f"/{path}"
    return urllib.parse.SplitResult(
        scheme=scheme,
        netloc=str(parsed.netloc or "").strip(),
        path=path or "/",
        query=str(parsed.query or ""),
        fragment="",
    )


def _build_switch_base_fallback_chain(base: urllib.parse.SplitResult) -> list[urllib.parse.SplitResult]:
    primary = urllib.parse.SplitResult(
        scheme=str(base.scheme or "").strip().lower(),
        netloc=str(base.netloc or "").strip(),
        path=str(base.path or "/"),
        query=str(base.query or ""),
        fragment="",
    )
    chain = [primary]
    if primary.scheme != "https":
        return chain
    host = str(primary.hostname or "").strip()
    if not host:
        return chain
    username = primary.username
    password = primary.password
    userinfo = ""
    if username is not None:
        userinfo = urllib.parse.quote(str(username), safe="")
        if password is not None:
            userinfo = f"{userinfo}:{urllib.parse.quote(str(password), safe='')}"
        userinfo = f"{userinfo}@"
    fallback_port = primary.port if primary.port not in {None, 443} else None
    fallback_netloc = f"{userinfo}{host}"
    if fallback_port is not None:
        fallback_netloc = f"{fallback_netloc}:{int(fallback_port)}"
    fallback = urllib.parse.SplitResult(
        scheme="http",
        netloc=fallback_netloc,
        path=primary.path or "/",
        query=primary.query,
        fragment="",
    )
    if fallback.netloc != primary.netloc or fallback.scheme != primary.scheme:
        chain.append(fallback)
    return chain


def _normalize_switch_proxy_device_locator(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFD", raw)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    underscored = re.sub(r"\s+", "_", without_marks)
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", underscored)
    compacted = re.sub(r"_+", "_", sanitized).strip("_")
    return compacted


def _build_switch_proxy_device_locator(device: dict) -> str:
    preferred = _normalize_switch_proxy_device_locator(device.get("name"))
    if preferred:
        return preferred
    return _normalize_switch_proxy_device_locator(device.get("id"))


def _resolve_switch_proxy_device_row(*, devices: list[dict], device_locator: str) -> dict | None:
    locator = str(device_locator or "").strip()
    if not locator:
        return None

    for row in devices:
        if str(row.get("id") or "").strip() == locator:
            return row

    normalized_locator = _normalize_switch_proxy_device_locator(locator)
    if not normalized_locator:
        return None
    normalized_locator_lower = normalized_locator.lower()
    matches = [
        row
        for row in devices
        if _build_switch_proxy_device_locator(row).lower() == normalized_locator_lower
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _build_switch_target_url(*, base: urllib.parse.SplitResult, proxy_path: str, query_string: str) -> str:
    requested = str(proxy_path or "").lstrip("/")
    root_path = str(base.path or "/")
    if requested:
        join_base = root_path if root_path.endswith("/") else f"{root_path}/"
        target_path = urllib.parse.urljoin(join_base, requested)
    else:
        target_path = root_path
    return urllib.parse.urlunsplit((base.scheme, base.netloc, target_path, str(query_string or ""), ""))


def _build_switch_proxy_fallback_paths(proxy_path: str) -> list[str]:
    normalized = str(proxy_path or "").strip().lstrip("/")
    if not normalized:
        return []
    parts = [segment for segment in normalized.split("/") if str(segment or "").strip()]
    if not parts:
        return []

    fallback_files = {"dictionarylist.xml", "labeldb.xml"}
    candidates: list[str] = []

    def _append_unique(path_value: str) -> None:
        value = str(path_value or "").strip().lstrip("/")
        if value and value not in candidates:
            candidates.append(value)

    if len(parts) >= 2 and str(parts[0]).lower() == "device" and str(parts[1]).lower() in fallback_files:
        filename = str(parts[1]).lower()
        _append_unique(f"hpe/device/{filename}")

    if (
        len(parts) >= 3
        and str(parts[0]).lower().startswith("csced")
        and str(parts[1]).lower() == "device"
        and str(parts[2]).lower() in fallback_files
    ):
        session_prefix = str(parts[0])
        filename = str(parts[2]).lower()
        _append_unique(f"{session_prefix}/hpe/device/{filename}")
        _append_unique(f"hpe/device/{filename}")

    if len(parts) >= 2 and str(parts[0]).lower().startswith("csced") and str(parts[1]).lower() != "hpe":
        session_prefix = str(parts[0])
        tail = [str(segment) for segment in parts[1:]]
        _append_unique("/".join([session_prefix, "hpe", *tail]))
        _append_unique("/".join(["hpe", *tail]))

    return candidates


def _strip_proxy_token_from_query(query_string: str, *, auth_token: str = "") -> str:
    raw = str(query_string or "")
    if not raw:
        return ""
    normalized_auth_token = str(auth_token or "").strip()
    kept: list[str] = []
    for chunk in raw.split("&"):
        part = str(chunk or "")
        if not part:
            continue
        raw_key = part.split("=", 1)[0]
        try:
            key = urllib.parse.unquote_plus(raw_key)
        except Exception:
            key = raw_key
        if str(key or "").strip().lower() == "token":
            raw_value = part.split("=", 1)[1] if "=" in part else ""
            try:
                value = urllib.parse.unquote_plus(raw_value)
            except Exception:
                value = raw_value
            if not normalized_auth_token or str(value or "").strip() == normalized_auth_token:
                continue
        kept.append(part)
    return "&".join(kept)


def _build_switch_proxy_download_retry_queries(query_string: str) -> list[str]:
    raw = str(query_string or "")
    if not raw:
        return []
    chunks = raw.split("&")
    candidates: list[str] = []

    def _append_candidate(updated_chunks: list[str]) -> None:
        candidate = "&".join(updated_chunks)
        if candidate != raw and candidate not in candidates:
            candidates.append(candidate)

    ssd_index: int | None = None
    ssd_key = ""
    ssd_alternates: list[str] = []
    action_index: int | None = None
    action_key = ""
    action_value = ""
    filename_index: int | None = None
    filename_key = ""
    filename_value = ""
    for index, chunk in enumerate(chunks):
        key = str(chunk or "").split("=", 1)[0]
        try:
            decoded_key = urllib.parse.unquote_plus(key)
        except Exception:
            decoded_key = key
        normalized_key = str(decoded_key or "").strip().lower()
        if normalized_key == "ssd":
            ssd_index = index
            ssd_key = key
            value = str(chunk or "").split("=", 1)[1] if "=" in str(chunk or "") else ""
            ssd_alternates = ["2", "4"] if value == "4" else ["4", "2"] if value == "2" else ["2", "4"]
            continue
        if normalized_key == "action":
            action_index = index
            action_key = key
            action_value = str(chunk or "").split("=", 1)[1] if "=" in str(chunk or "") else ""
            continue
        if normalized_key == "filename":
            filename_index = index
            filename_key = key
            raw_value = str(chunk or "").split("=", 1)[1] if "=" in str(chunk or "") else ""
            try:
                filename_value = urllib.parse.unquote_plus(raw_value)
            except Exception:
                filename_value = raw_value

    if ssd_index is not None:
        for alternate in ssd_alternates:
            updated = list(chunks)
            updated[ssd_index] = f"{ssd_key}={alternate}"
            _append_candidate(updated)

    image_alternates = {
        "system/images/inactive-image": "system/images/active-image",
        "system/images/active-image": "system/images/inactive-image",
    }
    alternate_filename = image_alternates.get(str(filename_value or "").strip().lower())
    if filename_index is not None and alternate_filename:
        action_alternates: list[str] = []
        if action_index is not None:
            action_alternates = ["1", "8"] if action_value == "8" else ["8", "1"] if action_value == "1" else ["1", "8"]
        encoded_filename = urllib.parse.quote_plus(alternate_filename, safe="/")
        updated = list(chunks)
        updated[filename_index] = f"{filename_key}={encoded_filename}"
        _append_candidate(updated)
        if ssd_index is not None:
            for alternate in ssd_alternates:
                updated = list(chunks)
                updated[filename_index] = f"{filename_key}={encoded_filename}"
                updated[ssd_index] = f"{ssd_key}={alternate}"
                _append_candidate(updated)
        if action_index is not None:
            for action_alternate in action_alternates:
                updated = list(chunks)
                updated[action_index] = f"{action_key}={action_alternate}"
                _append_candidate(updated)
                if ssd_index is not None:
                    for ssd_alternate in ssd_alternates:
                        updated = list(chunks)
                        updated[action_index] = f"{action_key}={action_alternate}"
                        updated[ssd_index] = f"{ssd_key}={ssd_alternate}"
                        _append_candidate(updated)
                updated = list(chunks)
                updated[action_index] = f"{action_key}={action_alternate}"
                updated[filename_index] = f"{filename_key}={encoded_filename}"
                _append_candidate(updated)
                if ssd_index is not None:
                    for ssd_alternate in ssd_alternates:
                        updated = list(chunks)
                        updated[action_index] = f"{action_key}={action_alternate}"
                        updated[filename_index] = f"{filename_key}={encoded_filename}"
                        updated[ssd_index] = f"{ssd_key}={ssd_alternate}"
                        _append_candidate(updated)
    return candidates


def _is_switch_proxy_login_redirect(upstream: httpx.Response | None) -> bool:
    if upstream is None:
        return False
    if int(upstream.status_code) not in {
        status.HTTP_301_MOVED_PERMANENTLY,
        status.HTTP_302_FOUND,
        status.HTTP_303_SEE_OTHER,
        status.HTTP_307_TEMPORARY_REDIRECT,
        status.HTTP_308_PERMANENT_REDIRECT,
    }:
        return False
    location = str(upstream.headers.get("location") or "").strip().lower()
    return "login" in location


def _prefix_switch_root_paths(*, text: str, proxy_prefix: str) -> str:
    rewritten = str(text or "")
    for root in _SWITCH_PROXY_PREFIX_ROOTS:
        escaped = re.escape(root)
        rewritten = re.sub(rf'(?<![\w\]\)\+])(["\'`]){escaped}', rf"\1{proxy_prefix}{root}", rewritten)
        rewritten = re.sub(
            rf"(?P<prefix>\b(?:href|src|action)\s*=\s*){escaped}",
            rf"\g<prefix>{proxy_prefix}{root}",
            rewritten,
            flags=re.IGNORECASE,
        )
        rewritten = re.sub(
            rf"(?P<prefix>(?:^|[\s(:,])['\"`]?){escaped}",
            rf"\g<prefix>{proxy_prefix}{root}",
            rewritten,
            flags=re.IGNORECASE,
        )
        rewritten = re.sub(rf"(?P<prefix>\burl::){escaped}", rf"\g<prefix>{proxy_prefix}{root}", rewritten, flags=re.IGNORECASE)
    return rewritten


def _is_switch_proxy_html_response(*, content_type: str, proxy_path: str) -> bool:
    normalized_type = str(content_type or "").strip().lower()
    normalized_path = str(proxy_path or "").strip().lower()
    if normalized_path.endswith(".js") or normalized_path.endswith(".css"):
        return False
    if "text/html" in normalized_type:
        return True
    return normalized_path.endswith(".htm") or normalized_path.endswith(".html")


def _is_switch_proxy_attachment_response(headers) -> bool:
    disposition = ""
    try:
        disposition = str(headers.get("content-disposition") or "")
    except Exception:
        disposition = ""
    lowered = disposition.strip().lower()
    return lowered.startswith("attachment") or "filename=" in lowered


def _normalize_switch_proxy_response_content_type(*, content_type: str, proxy_path: str) -> str:
    current = str(content_type or "").strip()
    normalized_path = str(proxy_path or "").strip().lower()
    lowered_type = current.lower()
    if normalized_path.endswith(".js") and "javascript" not in lowered_type and "ecmascript" not in lowered_type:
        return "application/javascript"
    if normalized_path.endswith(".css") and "text/css" not in lowered_type:
        return "text/css"
    if (normalized_path.endswith(".htm") or normalized_path.endswith(".html")) and "text/html" not in lowered_type:
        return "text/html"
    if (normalized_path.endswith(".xml") or normalized_path.endswith("/web/login") or normalized_path.endswith("web/login")) and "xml" not in lowered_type:
        return "text/xml"
    return current


def _rewrite_switch_proxy_location(
    *,
    location: str,
    base: urllib.parse.SplitResult,
    proxy_prefix: str,
) -> str:
    raw = str(location or "").strip()
    if not raw:
        return raw
    parsed = urllib.parse.urlsplit(raw)
    if not parsed.scheme and not parsed.netloc:
        normalized = parsed.path.lstrip("/")
        prefixed = f"{proxy_prefix}/{normalized}" if normalized else proxy_prefix
        return urllib.parse.urlunsplit(("", "", prefixed, parsed.query, parsed.fragment))
    if str(parsed.scheme or "").strip().lower() not in {"http", "https"}:
        return raw
    parsed_host = str(parsed.hostname or "").strip().lower()
    base_host = str(base.hostname or "").strip().lower()
    if parsed_host != base_host:
        return raw
    normalized = str(parsed.path or "/").lstrip("/")
    prefixed = f"{proxy_prefix}/{normalized}" if normalized else proxy_prefix
    return urllib.parse.urlunsplit(("", "", prefixed, parsed.query, parsed.fragment))


_SWITCH_PROXY_REFRESH_URL_RE = re.compile(
    r"^(?P<delay>\s*\d+(?:\.\d+)?\s*(?:[;,]\s*)?)(?:(?P<prefix>url\s*=\s*)?(?P<url>.+))?$",
    re.IGNORECASE,
)


def _rewrite_switch_proxy_refresh(
    *,
    value: str,
    base: urllib.parse.SplitResult,
    proxy_prefix: str,
) -> str:
    raw = str(value or "").strip()
    if not raw:
        return raw
    match = _SWITCH_PROXY_REFRESH_URL_RE.match(raw)
    if not match:
        return raw
    delay = str(match.group("delay") or "").strip()
    delay = re.sub(r"[;,]\s*$", "", delay).strip()
    url_part = match.group("url")
    if not url_part:
        return delay or raw
    unwrapped = str(url_part).strip()
    quote = ""
    if len(unwrapped) >= 2 and unwrapped[0] == unwrapped[-1] and unwrapped[0] in {"'", '"'}:
        quote = unwrapped[0]
        unwrapped = unwrapped[1:-1]
    rewritten = _rewrite_switch_proxy_location(location=unwrapped, base=base, proxy_prefix=proxy_prefix)
    if quote:
        rewritten = f"{quote}{rewritten}{quote}"
    return f"{delay}; url={rewritten}"


def _rewrite_switch_proxy_set_cookie(*, value: str, proxy_prefix: str) -> str:
    parts = [item.strip() for item in str(value or "").split(";") if str(item or "").strip()]
    if not parts:
        return str(value or "")
    cookie_name = parts[0].split("=", 1)[0].strip().lower()
    if cookie_name == "token":
        return f"token=; Max-Age=0; Path={proxy_prefix}/"
    rewritten: list[str] = []
    has_path = False
    for idx, item in enumerate(parts):
        lowered = item.lower()
        if idx > 0 and lowered.startswith("domain="):
            continue
        if idx > 0 and lowered.startswith("path="):
            has_path = True
            rewritten.append(f"Path={proxy_prefix}/")
            continue
        rewritten.append(item)
    if not has_path:
        rewritten.append(f"Path={proxy_prefix}/")
    return "; ".join(rewritten)


_SWITCH_PROXY_ABSOLUTE_ATTR_RE = re.compile(r'(?P<attr>\b(?:href|src|action)\s*=\s*[\'"])\s*/', re.IGNORECASE)
_SWITCH_PROXY_CSS_URL_RE = re.compile(r"url\(\s*/", re.IGNORECASE)
_SWITCH_PROXY_ABSOLUTE_URL_ATTR_RE = re.compile(
    r'(?P<attr>\b(?:href|src|action)\s*=\s*[\'"])(?P<url>https?://[^\'"]+)(?P<end>[\'"])',
    re.IGNORECASE,
)
_SWITCH_PROXY_ABSOLUTE_TEXT_URL_RE = re.compile(r"https?://[^\s\"'<>\\)]+", re.IGNORECASE)
_SWITCH_PROXY_HTML_MARKUP_HINT_RE = re.compile(
    r"<\s*(?:!doctype|html|head|body|title|meta|link|script|form|iframe|div|span|table|input|button)\b",
    re.IGNORECASE,
)


def _looks_like_switch_proxy_html_markup(text: str) -> bool:
    raw = str(text or "")
    # Some firmwares emit UTF-8 BOM while responses are decoded as latin-1 in
    # the proxy pipeline; tolerate both canonical and mojibake BOM forms.
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    elif raw.startswith("ï»¿"):
        raw = raw[3:]
    stripped = raw.lstrip()
    if not stripped or not stripped.startswith("<"):
        return False
    if stripped.lower().startswith("<?xml"):
        return False
    sample = stripped[:2048]
    return bool(_SWITCH_PROXY_HTML_MARKUP_HINT_RE.search(sample))


def _inject_switch_proxy_runtime_js(
    *,
    html_text: str,
    proxy_prefix: str,
    base: urllib.parse.SplitResult,
) -> str:
    marker = "data-itops-switch-proxy-runtime"
    if marker in html_text:
        return html_text
    base_host = str(base.hostname or "").strip().lower()
    base_port = base.port or (443 if str(base.scheme).lower() == "https" else 80)
    script = f"""
<script {marker}="1">
(function() {{
  var PROXY_PREFIX = {json.dumps(proxy_prefix)};
  var BASE_HOST = {json.dumps(base_host)};
  var BASE_PORT = {int(base_port)};
  function withPrefix(pathname, search, hash) {{
    var p = String(pathname || "");
    if (!p.startsWith("/")) p = "/" + p;
    if (p === PROXY_PREFIX || p.startsWith(PROXY_PREFIX + "/")) return p + String(search || "") + String(hash || "");
    return PROXY_PREFIX + p + String(search || "") + String(hash || "");
  }}
  function rewriteUrl(raw) {{
    if (raw == null) return raw;
    var value = String(raw);
    if (!value) return value;
    if (value.startsWith("#") || value.startsWith("javascript:") || value.startsWith("data:") || value.startsWith("mailto:")) return value;
    try {{
      var currentHref = window.location.href;
      var currentOrigin = window.location.origin;
      var parsed = new URL(value, currentHref);
      var proto = String(parsed.protocol || "").toLowerCase();
      var isHttp = proto === "http:" || proto === "https:";
      if (isHttp && String(parsed.hostname || "").toLowerCase() === BASE_HOST) {{
        return withPrefix(parsed.pathname, parsed.search, parsed.hash);
      }}
      if (parsed.origin === currentOrigin) {{
        var parsedPath = String(parsed.pathname || "");
        if (parsedPath === PROXY_PREFIX || parsedPath.startsWith(PROXY_PREFIX + "/")) {{
          return parsedPath + String(parsed.search || "") + String(parsed.hash || "");
        }}
        if (parsedPath.startsWith("/")) {{
          return withPrefix(parsedPath, parsed.search, parsed.hash);
        }}
      }}
      return value;
    }} catch (_err) {{
      if (value.startsWith("/")) return withPrefix(value, "", "");
      return value;
    }}
  }}
  function rewriteElementUrlAttribute(el, name) {{
    try {{
      if (!el || !name || typeof el.getAttribute !== "function" || typeof el.setAttribute !== "function") return;
      var raw = el.getAttribute(name);
      if (!raw) return;
      var rewritten = rewriteUrl(raw);
      if (rewritten && rewritten !== raw) {{
        el.setAttribute(name, rewritten);
      }}
    }} catch (_err) {{}}
  }}
  function rewriteElementUrlAttributes(el) {{
    rewriteElementUrlAttribute(el, "src");
    rewriteElementUrlAttribute(el, "href");
    rewriteElementUrlAttribute(el, "action");
  }}
  function patchUrlProperty(proto, prop) {{
    try {{
      var owner = proto;
      var descriptor = null;
      while (owner && !descriptor) {{
        descriptor = Object.getOwnPropertyDescriptor(owner, prop);
        owner = Object.getPrototypeOf(owner);
      }}
      if (!descriptor || typeof descriptor.set !== "function" || typeof descriptor.get !== "function") return;
      Object.defineProperty(proto, prop, {{
        configurable: true,
        enumerable: descriptor.enumerable,
        get: function() {{
          return descriptor.get.call(this);
        }},
        set: function(value) {{
          return descriptor.set.call(this, rewriteUrl(value));
        }}
      }});
    }} catch (_err) {{}}
  }}
  var nativeSetAttribute = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function(name, value) {{
    try {{
      var n = String(name || "").toLowerCase();
      if (n === "src" || n === "href" || n === "action") {{
        value = rewriteUrl(value);
      }}
    }} catch (_err) {{}}
    return nativeSetAttribute.call(this, name, value);
  }};
  if (window.HTMLImageElement) patchUrlProperty(window.HTMLImageElement.prototype, "src");
  if (window.HTMLScriptElement) patchUrlProperty(window.HTMLScriptElement.prototype, "src");
  if (window.HTMLIFrameElement) patchUrlProperty(window.HTMLIFrameElement.prototype, "src");
  if (window.HTMLLinkElement) patchUrlProperty(window.HTMLLinkElement.prototype, "href");
  if (window.HTMLAnchorElement) patchUrlProperty(window.HTMLAnchorElement.prototype, "href");
  if (window.HTMLFormElement) patchUrlProperty(window.HTMLFormElement.prototype, "action");
  try {{
    var scanUrlElements = function(root) {{
      try {{
        if (root && root.nodeType === 1) rewriteElementUrlAttributes(root);
        var nodes = root && typeof root.querySelectorAll === "function"
          ? root.querySelectorAll("[src], [href], [action]")
          : [];
        for (var i = 0; i < nodes.length; i++) rewriteElementUrlAttributes(nodes[i]);
      }} catch (_err) {{}}
    }};
    if (document.readyState === "loading") {{
      document.addEventListener("DOMContentLoaded", function() {{ scanUrlElements(document); }}, {{ once: true }});
    }} else {{
      scanUrlElements(document);
    }}
    if (window.MutationObserver) {{
      new MutationObserver(function(mutations) {{
        for (var i = 0; i < mutations.length; i++) {{
          var mutation = mutations[i];
          if (mutation.type === "attributes") {{
            rewriteElementUrlAttributes(mutation.target);
          }}
          for (var j = 0; j < mutation.addedNodes.length; j++) {{
            scanUrlElements(mutation.addedNodes[j]);
          }}
        }}
      }}).observe(document.documentElement || document, {{
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["src", "href", "action"]
      }});
    }}
  }} catch (_err) {{}}
  document.addEventListener("submit", function(event) {{
    try {{
      var form = event && event.target;
      if (form && typeof form.action === "string" && form.action) {{
        form.action = rewriteUrl(form.action);
      }}
    }} catch (_err) {{}}
  }}, true);
  if (window.HTMLFormElement && window.HTMLFormElement.prototype && typeof window.HTMLFormElement.prototype.submit === "function") {{
    var _nativeFormSubmit = window.HTMLFormElement.prototype.submit;
    window.HTMLFormElement.prototype.submit = function() {{
      try {{
        if (this && typeof this.action === "string" && this.action) {{
          this.action = rewriteUrl(this.action);
        }}
      }} catch (_err) {{}}
      return _nativeFormSubmit.apply(this, arguments);
    }};
  }}
  var open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url) {{
    try {{
      arguments[1] = rewriteUrl(url);
    }} catch (_err) {{}}
    return open.apply(this, arguments);
  }};
  if (window.fetch) {{
    var originalFetch = window.fetch.bind(window);
    window.fetch = function(input, init) {{
      try {{
        if (typeof input === "string") {{
          input = rewriteUrl(input);
        }} else if (input && typeof input.url === "string") {{
          // Keep Request instances untouched to avoid body/stream side effects on
          // legacy switch firmware POST flows (password validation).
          if (!(window.Request && input instanceof Request)) {{
            input = rewriteUrl(input.url);
          }}
        }}
      }} catch (_err) {{}}
      return originalFetch(input, init);
    }};
  }}
  var originalOpenWindow = window.open;
  window.open = function(url) {{
    try {{
      arguments[0] = rewriteUrl(url);
    }} catch (_err) {{}}
    return originalOpenWindow.apply(window, arguments);
  }};
}})();
</script>
"""
    lowered = html_text.lower()
    head_idx = lowered.find("</head>")
    if head_idx >= 0:
        return html_text[:head_idx] + script + html_text[head_idx:]
    body_idx = lowered.find("</body>")
    if body_idx >= 0:
        return html_text[:body_idx] + script + html_text[body_idx:]
    return html_text + script


def _rewrite_switch_proxy_absolute_text_urls(
    *,
    text: str,
    base: urllib.parse.SplitResult,
    proxy_prefix: str,
) -> str:
    base_host = str(base.hostname or "").strip().lower()
    if not base_host:
        return str(text or "")

    def _replace(match: re.Match) -> str:
        raw_url = str(match.group(0) or "")
        try:
            parsed = urllib.parse.urlsplit(raw_url)
        except Exception:
            return raw_url
        scheme = str(parsed.scheme or "").strip().lower()
        host = str(parsed.hostname or "").strip().lower()
        if scheme not in {"http", "https"} or host != base_host:
            return raw_url
        normalized = str(parsed.path or "/").lstrip("/")
        proxied_path = f"{proxy_prefix}/{normalized}" if normalized else proxy_prefix
        return urllib.parse.urlunsplit(("", "", proxied_path, parsed.query, parsed.fragment))

    return _SWITCH_PROXY_ABSOLUTE_TEXT_URL_RE.sub(_replace, str(text or ""))


def _rewrite_switch_proxy_html(
    *,
    body: bytes,
    proxy_prefix: str,
    base: urllib.parse.SplitResult,
    proxy_path: str = "",
) -> bytes:
    if not body:
        return body
    text = body.decode("latin-1", errors="ignore")
    looks_like_markup = _looks_like_switch_proxy_html_markup(text=text)
    if looks_like_markup:
        text = _SWITCH_PROXY_ABSOLUTE_ATTR_RE.sub(lambda m: f"{m.group('attr')}{html_lib.escape(proxy_prefix, quote=True)}/", text)
        text = _SWITCH_PROXY_CSS_URL_RE.sub(f"url({proxy_prefix}/", text)

    base_host = str(base.hostname or "").strip().lower()

    def _replace_absolute_url(match: re.Match) -> str:
        raw_url = str(match.group("url") or "")
        parsed = urllib.parse.urlsplit(raw_url)
        scheme = str(parsed.scheme or "").strip().lower()
        host = str(parsed.hostname or "").strip().lower()
        if scheme not in {"http", "https"} or host != base_host:
            return match.group(0)
        normalized = str(parsed.path or "/").lstrip("/")
        proxied_path = f"{proxy_prefix}/{normalized}" if normalized else proxy_prefix
        rewritten = urllib.parse.urlunsplit(("", "", proxied_path, parsed.query, parsed.fragment))
        return f"{match.group('attr')}{html_lib.escape(rewritten, quote=True)}{match.group('end')}"

    if looks_like_markup:
        text = _SWITCH_PROXY_ABSOLUTE_URL_ATTR_RE.sub(_replace_absolute_url, text)
    text = _rewrite_switch_proxy_absolute_text_urls(text=text, base=base, proxy_prefix=proxy_prefix)
    text = _prefix_switch_root_paths(text=text, proxy_prefix=proxy_prefix)

    normalized_proxy_path = str(proxy_path or "").strip().lower().lstrip("/")
    lowered_text = text.lower()
    has_unclosed_textarea = "<textarea" in lowered_text and "</textarea>" not in lowered_text
    should_inject_runtime = looks_like_markup and not normalized_proxy_path.startswith("wcn/") and not has_unclosed_textarea
    if should_inject_runtime:
        text = _inject_switch_proxy_runtime_js(html_text=text, proxy_prefix=proxy_prefix, base=base)
    return text.encode("latin-1", errors="ignore")


def _rewrite_switch_proxy_javascript(*, body: bytes, proxy_prefix: str, base: urllib.parse.SplitResult) -> bytes:
    if not body:
        return body
    text = body.decode("latin-1", errors="ignore")
    base_host = str(base.hostname or "").strip().lower()
    host_pattern = re.escape(base_host)
    abs_re = re.compile(
        rf"""(?P<q>["'`])https?://{host_pattern}(?::\d+)?(?P<path>/[^"'`]*)?(?P=q)""",
        re.IGNORECASE,
    )

    def _replace_abs(match: re.Match) -> str:
        quote = str(match.group("q") or '"')
        path = str(match.group("path") or "/")
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{quote}{proxy_prefix}{normalized}{quote}"

    text = abs_re.sub(_replace_abs, text)

    # Legacy HPE WCN scripts detect dynamic URLs with a hardcoded "/wcn/" check.
    # After proxy prefixing, preserve compatibility by accepting both raw and proxied forms.
    legacy_dyn_url_check = re.compile(
        rf'(?P<lhs>[A-Za-z_$][\w$.]*)\.indexOf\(\s*(?P<q>["\']){re.escape(proxy_prefix)}/wcn/(?P=q)\s*\)\s*!=\s*-?1'
    )

    def _restore_legacy_dyn_url_check(match: re.Match) -> str:
        lhs = str(match.group("lhs") or "sActionValue")
        quote = str(match.group("q") or '"')
        return (
            f"({lhs}.indexOf({quote}/wcn/{quote})!=-1 || "
            f"{lhs}.indexOf({quote}{proxy_prefix}/wcn/{quote})!=-1)"
        )

    text = legacy_dyn_url_check.sub(_restore_legacy_dyn_url_check, text)
    return text.encode("latin-1", errors="ignore")


_SWITCH_PROXY_XML_STYLESHEET_HREF_RE = re.compile(r'(<\?xml-stylesheet[^>]*\bhref\s*=\s*["\'])/', re.IGNORECASE)
_SWITCH_PROXY_CONNECTED_USER_LIST_RE = re.compile(r"<ConnectedUserList\b[\s\S]*?</ConnectedUserList>", re.IGNORECASE)
_SWITCH_PROXY_SESSION_TYPE_RE = re.compile(r"<sessionType>\s*\d+\s*</sessionType>", re.IGNORECASE)


def _rewrite_switch_proxy_connected_user_session_type(*, xml_text: str, client_scheme: str) -> str:
    normalized_scheme = str(client_scheme or "").strip().lower()
    expected = "4" if normalized_scheme == "https" else "2"

    def _rewrite_block(match: re.Match) -> str:
        block = str(match.group(0) or "")
        return _SWITCH_PROXY_SESSION_TYPE_RE.sub(f"<sessionType>{expected}</sessionType>", block)

    return _SWITCH_PROXY_CONNECTED_USER_LIST_RE.sub(_rewrite_block, str(xml_text or ""))


def _rewrite_switch_proxy_xml(*, body: bytes, proxy_prefix: str, client_scheme: str = "") -> bytes:
    if not body:
        return body
    text = body.decode("latin-1", errors="ignore")
    text = _SWITCH_PROXY_XML_STYLESHEET_HREF_RE.sub(rf"\1{proxy_prefix}/", text)
    text = _prefix_switch_root_paths(text=text, proxy_prefix=proxy_prefix)
    text = _rewrite_switch_proxy_connected_user_session_type(xml_text=text, client_scheme=client_scheme)
    return text.encode("latin-1", errors="ignore")


_SWITCH_PROXY_ABORTED_LOAD_STATUS_RE = re.compile(
    r"<LoadStatus\b[^>]*>[\s\S]*?<copyStatusType>\s*3\s*</copyStatusType>[\s\S]*?"
    r"<errorMessage>\s*Copy:\s*Copy process aborted by application\s*</errorMessage>[\s\S]*?</LoadStatus>",
    re.IGNORECASE,
)
_SWITCH_PROXY_IMAGE_ABORTED_LOAD_STATUS_RE = re.compile(
    r"<LoadStatus\b[^>]*>[\s\S]*?"
    r"(?:(?:<sourceFileType>\s*8\s*</sourceFileType>)|(?:system/images/[^<\s]+))[\s\S]*?"
    r"<copyStatusType>\s*3\s*</copyStatusType>[\s\S]*?"
    r"<errorMessage>\s*Copy:\s*Copy process aborted by application\s*</errorMessage>[\s\S]*?</LoadStatus>",
    re.IGNORECASE,
)
_SWITCH_PROXY_ACTIVE_LOAD_STATUS_RE = re.compile(
    r"<LoadStatus\b[^>]*>[\s\S]*?<copyStatusType>\s*1\s*</copyStatusType>[\s\S]*?</LoadStatus>",
    re.IGNORECASE,
)
def _extract_switch_proxy_tag_value(*, xml_text: str, tag: str, default: str = "") -> str:
    pattern = re.compile(rf"<{re.escape(str(tag))}>\s*([\s\S]*?)\s*</{re.escape(str(tag))}>", re.IGNORECASE)
    match = pattern.search(str(xml_text or ""))
    return str(match.group(1) if match else default).strip()


def _switch_proxy_xml_tag(tag: str, value: str) -> str:
    return f"<{tag}>{html_lib.escape(str(value or ''), quote=False)}</{tag}>"


def _build_switch_proxy_image_load_status_block(load_status_block: str, *, completed: bool) -> str:
    block = str(load_status_block or "")
    source_name = _extract_switch_proxy_tag_value(xml_text=block, tag="sourceFileName", default="system/images/image1.bin")
    source_type = _extract_switch_proxy_tag_value(xml_text=block, tag="sourceFileType", default="8") or "8"
    destination_name = _extract_switch_proxy_tag_value(xml_text=block, tag="destinationFileName", default=source_name)
    destination_type = _extract_switch_proxy_tag_value(xml_text=block, tag="destinationFileType", default="1") or "1"
    uptime = _extract_switch_proxy_tag_value(xml_text=block, tag="upTime", default="0") or "0"
    transferred = _extract_switch_proxy_tag_value(xml_text=block, tag="bytesTransfered", default="0") or "0"
    total = _extract_switch_proxy_tag_value(xml_text=block, tag="totalSize", default="0") or "0"
    try:
        transferred_value = int(str(transferred).strip() or "0")
    except ValueError:
        transferred_value = 0
    try:
        total_value = int(str(total).strip() or "0")
    except ValueError:
        total_value = 0
    completed_bytes = str(max(transferred_value, total_value))
    active_total = str(total_value if total_value > 0 else 0)
    lines = [
        '<LoadStatus type="section">',
        _switch_proxy_xml_tag("sourceFileName", source_name),
        _switch_proxy_xml_tag("sourceFileType", source_type),
        _switch_proxy_xml_tag("destinationFileName", destination_name or source_name),
        _switch_proxy_xml_tag("destinationFileType", destination_type),
        _switch_proxy_xml_tag("upTime", uptime),
        "<copyStatusType>5</copyStatusType>" if completed else "<copyStatusType>1</copyStatusType>",
        _switch_proxy_xml_tag("bytesTransfered", completed_bytes if completed else str(transferred_value)),
        "<errorMessage></errorMessage>",
        "<totalSize>0</totalSize>" if completed else _switch_proxy_xml_tag("totalSize", active_total),
        "</LoadStatus>",
    ]
    return "\n".join(lines)


def _rewrite_switch_proxy_image_download_load_status(xml_text: str, *, completed: bool) -> str:
    return _SWITCH_PROXY_IMAGE_ABORTED_LOAD_STATUS_RE.sub(
        lambda match: _build_switch_proxy_image_load_status_block(str(match.group(0) or ""), completed=completed),
        str(xml_text or ""),
    )


def _rewrite_switch_proxy_recent_download_load_status(body: bytes, *, completed: bool = True) -> bytes:
    if not body:
        return body
    text = body.decode("latin-1", errors="ignore")
    has_false_abort = "Copy process aborted by application" in text
    has_active_status = bool(_SWITCH_PROXY_ACTIVE_LOAD_STATUS_RE.search(text))
    if not has_false_abort and not has_active_status:
        return body

    rewritten = text
    if _is_switch_proxy_image_download_false_abort(body):
        rewritten = _rewrite_switch_proxy_image_download_load_status(rewritten, completed=completed)
    elif has_false_abort:
        rewritten = _SWITCH_PROXY_ABORTED_LOAD_STATUS_RE.sub('<LoadStatus type="section">\n</LoadStatus>', rewritten)
    if has_active_status:
        rewritten = _SWITCH_PROXY_ACTIVE_LOAD_STATUS_RE.sub('<LoadStatus type="section">\n</LoadStatus>', rewritten)
    rewritten = re.sub(r"<statusCode>\s*</statusCode>", "<statusCode>0</statusCode>", rewritten, flags=re.IGNORECASE)
    if "<deviceStatusCode>" not in rewritten:
        rewritten = re.sub(
            r"(</ActionStatus>)",
            "<deviceStatusCode>0</deviceStatusCode>\n<statusString>OK</statusString>\n\\1",
            rewritten,
            count=1,
            flags=re.IGNORECASE,
        )
    return rewritten.encode("latin-1", errors="ignore") if rewritten != text else body


def _build_switch_proxy_successful_load_status_body(*, completed: bool = True) -> bytes:
    copy_status = b"5" if completed else b"1"
    return (
        b'<?xml version="1.0" encoding="UTF-8" ?>\n'
        b"<ResponseData>\n"
        b"<DeviceConfiguration>\n"
        b"<version>1.0</version>\n"
        b'<LoadStatus type="section">\n'
        b"<sourceFileName>system/images/image1.bin</sourceFileName>\n"
        b"<sourceFileType>8</sourceFileType>\n"
        b"<destinationFileName>system/images/image1.bin</destinationFileName>\n"
        b"<destinationFileType>1</destinationFileType>\n"
        b"<upTime>0</upTime>\n"
        b"<copyStatusType>" + copy_status + b"</copyStatusType>\n"
        b"<bytesTransfered>0</bytesTransfered>\n"
        b"<errorMessage></errorMessage>\n"
        b"<totalSize>0</totalSize>\n"
        b"</LoadStatus>\n"
        b"</DeviceConfiguration>\n"
        b"<ActionStatus>\n"
        b"<requestURL>LoadStatus</requestURL>\n"
        b"<statusCode></statusCode>\n"
        b"</ActionStatus>\n"
        b"</ResponseData>\n"
    )


def _is_switch_proxy_image_download_false_abort(body: bytes) -> bool:
    if not body:
        return False
    text = body.decode("latin-1", errors="ignore")
    return bool(_SWITCH_PROXY_IMAGE_ABORTED_LOAD_STATUS_RE.search(text))


def _resolve_switch_proxy_image_download_started_at(request: Request) -> float:
    raw = str(request.cookies.get(_SWITCH_PROXY_IMAGE_DOWNLOAD_STARTED_COOKIE) or "").strip()
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 0.0
    return value if value > 0 else time.time()


def _is_switch_proxy_image_download_completion_due(started_at: float) -> bool:
    try:
        elapsed = time.time() - float(started_at or 0.0)
    except (TypeError, ValueError):
        elapsed = 0.0
    return elapsed >= _SWITCH_PROXY_IMAGE_COMPLETE_DELAY_SECONDS


def _set_switch_proxy_session_cookies(
    response: Response,
    *,
    proxy_prefix: str,
    session_token_cookie_value: str,
    secure: bool,
) -> None:
    if session_token_cookie_value:
        response.set_cookie(
            key=_SWITCH_PROXY_TOKEN_COOKIE,
            value=session_token_cookie_value,
            path=f"{proxy_prefix}/",
            httponly=True,
            secure=secure,
            samesite="lax",
            max_age=3600,
        )
    response.set_cookie(
        key=_SWITCH_PROXY_PREFIX_COOKIE,
        value=proxy_prefix,
        path="/",
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=3600,
    )


def _set_switch_proxy_image_download_started_cookie(
    response: Response,
    *,
    proxy_prefix: str,
    secure: bool,
    started_at: float,
) -> None:
    response.set_cookie(
        key=_SWITCH_PROXY_IMAGE_DOWNLOAD_STARTED_COOKIE,
        value=str(float(started_at)),
        path=f"{proxy_prefix}/",
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=int(_SWITCH_PROXY_IMAGE_COMPLETE_DELAY_SECONDS * 2),
    )


def _sync_switch_proxy_image_download_started_cookie(
    response: Response,
    *,
    proxy_prefix: str,
    secure: bool,
    started_at: float,
    completed: bool,
) -> None:
    if completed:
        response.delete_cookie(
            key=_SWITCH_PROXY_IMAGE_DOWNLOAD_STARTED_COOKIE,
            path=f"{proxy_prefix}/",
        )
        return
    _set_switch_proxy_image_download_started_cookie(
        response,
        proxy_prefix=proxy_prefix,
        secure=secure,
        started_at=started_at,
    )


def _set_switch_proxy_load_status_headers(
    response: Response,
    *,
    upstream_state: str,
    rewritten: bool,
    recent_download: bool,
    started_at: float | None = None,
    completion_due: bool = False,
) -> None:
    response.headers["X-ITops-LoadStatus-Upstream"] = str(upstream_state or "")
    response.headers["X-ITops-LoadStatus-Rewritten"] = "1" if rewritten else "0"
    response.headers["X-ITops-Recent-Download"] = "1" if recent_download else "0"
    if started_at is not None:
        response.headers["X-ITops-Image-Download-Elapsed"] = str(max(0, int(time.time() - float(started_at))))
        response.headers["X-ITops-Image-Download-Completion-Due"] = "1" if completion_due else "0"


def _is_switch_proxy_load_status_query(query: str) -> bool:
    return "loadstatus" in str(query or "").strip().lower()


def _is_switch_proxy_load_status_delete_request(*, method: str, query: str, body: bytes) -> bool:
    if str(method or "").upper() != "POST" or not _is_switch_proxy_load_status_query(query):
        return False
    text = bytes(body or b"").decode("latin-1", errors="ignore").lower()
    return "<loadstatus" in text and "delete" in text


def _build_switch_proxy_successful_load_status_delete_body() -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8" ?>\n'
        b"<ResponseData>\n"
        b"<ActionStatus>\n"
        b"<version>1.0</version>\n"
        b"<requestURL>LoadStatus</requestURL>\n"
        b"<requestAction>delete</requestAction>\n"
        b"<statusCode>0</statusCode>\n"
        b"<deviceStatusCode>0</deviceStatusCode>\n"
        b"<statusString>OK</statusString>\n"
        b"</ActionStatus>\n"
        b"</ResponseData>\n"
    )


def _classify_switch_proxy_load_status(body: bytes) -> str:
    text = bytes(body or b"").decode("latin-1", errors="ignore")
    load_status_match = re.search(r"<LoadStatus\b[^>]*>([\s\S]*?)</LoadStatus>", text, re.IGNORECASE)
    if not load_status_match:
        return "missing"
    load_status = str(load_status_match.group(1) or "").strip()
    if not load_status:
        return "empty"
    copy_status_match = re.search(r"<copyStatusType>\s*([^<]+?)\s*</copyStatusType>", load_status, re.IGNORECASE)
    if copy_status_match:
        return f"copyStatusType-{copy_status_match.group(1).strip()}"
    return "present"


def _switch_proxy_response_has_download_body(*, response_body: bytes, headers) -> bool:
    if len(response_body or b"") > 0:
        return True
    try:
        content_length = int(str(headers.get("content-length") or "0").strip() or "0")
    except (TypeError, ValueError):
        content_length = 0
    return content_length > 0


def _strip_switch_proxy_internal_cookies(cookie_header: str) -> str:
    raw = str(cookie_header or "").strip()
    if not raw:
        return raw
    blocked_names = {
        str(_SWITCH_PROXY_TOKEN_COOKIE).strip().lower(),
        str(_SWITCH_PROXY_PREFIX_COOKIE).strip().lower(),
        "token",
    }
    kept: list[tuple[str, str]] = []
    positions_by_name: dict[str, int] = {}
    for chunk in raw.split(";"):
        part = str(chunk or "").strip()
        if not part:
            continue
        raw_name, raw_value = part.split("=", 1) if "=" in part else (part, "")
        name = raw_name.strip()
        normalized_name = name.lower()
        value = raw_value.strip()
        if normalized_name in blocked_names:
            continue
        existing_position = positions_by_name.get(normalized_name)
        if existing_position is None:
            if value:
                positions_by_name[normalized_name] = len(kept)
                kept.append((name, value))
            continue
        existing_name, existing_value = kept[existing_position]
        if value:
            kept[existing_position] = (existing_name or name, value)
        elif not existing_value:
            kept[existing_position] = (existing_name or name, value)
    return "; ".join(f"{name}={value}" if value else str(name) for name, value in kept)


def _build_switch_proxy_request_headers(
    request: Request,
    base: urllib.parse.SplitResult,
    target_url: str,
    proxy_prefix: str = "",
) -> dict[str, str]:
    forwarded: dict[str, str] = {}
    upstream_origin = f"{base.scheme}://{base.netloc}"

    def _rewrite_referer(raw_value: str) -> str:
        raw = str(raw_value or "").strip()
        if not raw:
            return ""
        try:
            parsed = urllib.parse.urlsplit(raw)
        except Exception:
            return ""
        path = str(parsed.path or "/")
        normalized_prefix = str(proxy_prefix or "").rstrip("/")
        upstream_path = path
        matched_proxy_prefix = False
        if normalized_prefix:
            if path == normalized_prefix or path == f"{normalized_prefix}/":
                upstream_path = "/"
                matched_proxy_prefix = True
            elif path.startswith(f"{normalized_prefix}/"):
                upstream_path = f"/{path[len(normalized_prefix) + 1:]}"
                matched_proxy_prefix = True
        upstream_path = re.sub(r"/{2,}", "/", str(upstream_path or "/"))
        scheme = str(parsed.scheme or "").strip().lower()
        parsed_host = str(parsed.hostname or "").strip().lower()
        base_host = str(base.hostname or "").strip().lower()
        if (
            scheme in {"http", "https"}
            and parsed_host
            and parsed_host != base_host
            and not matched_proxy_prefix
        ):
            # Ignore cross-origin referers for upstream devices.
            return ""
        return urllib.parse.urlunsplit(
            (
                str(base.scheme or "http"),
                str(base.netloc or ""),
                upstream_path or "/",
                str(parsed.query or ""),
                "",
            )
        )

    for key, value in request.headers.items():
        lowered = str(key or "").strip().lower()
        if lowered in _SWITCH_PROXY_HOP_BY_HOP_HEADERS or lowered in {"host", "content-length", "origin", "referer"}:
            continue
        if lowered == "cookie":
            sanitized_cookie = _strip_switch_proxy_internal_cookies(str(value))
            if sanitized_cookie:
                forwarded[str(key)] = sanitized_cookie
            continue
        forwarded[str(key)] = str(value)
    forwarded["Host"] = str(base.netloc)
    if request.headers.get("origin"):
        forwarded["Origin"] = upstream_origin
    if request.headers.get("referer"):
        rewritten_referer = _rewrite_referer(str(request.headers.get("referer") or ""))
        if rewritten_referer:
            forwarded["Referer"] = rewritten_referer
    return forwarded


def _format_switch_proxy_request_error(exc: httpx.RequestError) -> str:
    message = str(exc or "").strip()
    if message:
        return message
    request = getattr(exc, "request", None)
    url = str(getattr(request, "url", "") or "").strip()
    kind = exc.__class__.__name__
    return f"{kind} ({url})" if url else kind


def _is_switch_proxy_multiple_transfer_encoding_error(exc: BaseException | None) -> bool:
    message = str(exc or "").strip().lower()
    return "multiple transfer-encoding headers" in message or "incomplete chunked read" in message


def _decode_switch_proxy_chunked_body(raw_body: bytes) -> bytes:
    body = bytes(raw_body or b"")
    decoded = bytearray()
    position = 0
    while position < len(body):
        line_end = body.find(b"\r\n", position)
        if line_end < 0:
            break
        size_line = body[position:line_end].split(b";", 1)[0].strip()
        try:
            chunk_size = int(size_line, 16)
        except ValueError:
            return body
        position = line_end + 2
        if chunk_size == 0:
            return bytes(decoded)
        chunk_end = position + chunk_size
        if chunk_end > len(body):
            return body
        decoded.extend(body[position:chunk_end])
        position = chunk_end + 2 if body[chunk_end:chunk_end + 2] == b"\r\n" else chunk_end
    return body


@dataclass
class _SwitchProxyLenientRawResponse:
    status_code: int
    headers: list[tuple[str, str]]
    transfer_encodings: list[str]
    initial_body: bytes
    raw_socket: socket.socket | ssl.SSLSocket | None

    def close(self) -> None:
        if self.raw_socket is None:
            return
        try:
            self.raw_socket.close()
        except Exception:
            pass
        self.raw_socket = None

    def iter_body(self):
        try:
            if any("chunked" in value for value in self.transfer_encodings):
                yield from _iter_switch_proxy_lenient_chunked_body(
                    raw_socket=self.raw_socket,
                    initial_body=self.initial_body,
                )
            else:
                if self.initial_body:
                    yield self.initial_body
                while self.raw_socket is not None:
                    try:
                        chunk = self.raw_socket.recv(65536)
                    except socket.timeout:
                        break
                    if not chunk:
                        break
                    yield chunk
        finally:
            self.close()

    def read_body(self) -> bytes:
        return b"".join(self.iter_body())


def _iter_switch_proxy_lenient_chunked_body(
    *,
    raw_socket: socket.socket | ssl.SSLSocket | None,
    initial_body: bytes,
):
    buffer = bytearray(initial_body or b"")
    while True:
        while b"\r\n" not in buffer:
            if raw_socket is None:
                break
            try:
                chunk = raw_socket.recv(65536)
            except socket.timeout:
                chunk = b""
            if not chunk:
                break
            buffer.extend(chunk)
        line_end = buffer.find(b"\r\n")
        if line_end < 0:
            if buffer:
                yield bytes(buffer)
            break
        size_line = bytes(buffer[:line_end]).split(b";", 1)[0].strip()
        del buffer[:line_end + 2]
        try:
            chunk_size = int(size_line, 16)
        except ValueError:
            yield size_line + b"\r\n" + bytes(buffer)
            break
        if chunk_size == 0:
            break
        while len(buffer) < chunk_size + 2:
            if raw_socket is None:
                break
            try:
                chunk = raw_socket.recv(65536)
            except socket.timeout:
                chunk = b""
            if not chunk:
                break
            buffer.extend(chunk)
        available = min(chunk_size, len(buffer))
        if available:
            yield bytes(buffer[:available])
        del buffer[:min(len(buffer), chunk_size + 2)]
        if available < chunk_size:
            break


def _open_switch_proxy_lenient_raw_response(
    *,
    method: str,
    target_url: str,
    headers: dict[str, str],
    content: bytes | None = None,
) -> _SwitchProxyLenientRawResponse:
    parsed = urllib.parse.urlsplit(str(target_url or ""))
    scheme = str(parsed.scheme or "").strip().lower()
    if scheme not in {"http", "https"}:
        raise httpx.RequestError(f"Unsupported upstream scheme: {scheme}")
    host = str(parsed.hostname or "").strip()
    if not host:
        raise httpx.RequestError("Missing upstream host")
    port = parsed.port or (443 if scheme == "https" else 80)
    path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query or "", ""))
    forwarded_headers = {
        str(key): str(value)
        for key, value in dict(headers or {}).items()
        if str(key or "").strip().lower() not in {"connection", "content-length", "accept-encoding"}
    }
    forwarded_headers["Accept-Encoding"] = "gzip, deflate"
    forwarded_headers["Connection"] = "keep-alive"
    body = bytes(content or b"")
    if body:
        forwarded_headers["Content-Length"] = str(len(body))
    request_lines = [f"{str(method or 'GET').upper()} {path} HTTP/1.1", f"Host: {parsed.netloc}"]
    request_lines.extend(f"{key}: {value}" for key, value in forwarded_headers.items() if str(key).lower() != "host")
    request_bytes = ("\r\n".join(request_lines) + "\r\n\r\n").encode("latin-1", errors="ignore") + body
    raw_socket: socket.socket | ssl.SSLSocket | None = None
    try:
        raw_socket = socket.create_connection((host, int(port)), timeout=45)
        if scheme == "https":
            raw_socket = ssl._create_unverified_context().wrap_socket(raw_socket, server_hostname=host)
        raw_socket.settimeout(300)
        raw_socket.sendall(request_bytes)
        raw_response = bytearray()
        while b"\r\n\r\n" not in raw_response and b"\n\n" not in raw_response:
            try:
                chunk = raw_socket.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            raw_response.extend(chunk)
        header_end = raw_response.find(b"\r\n\r\n")
        separator_size = 4
        if header_end < 0:
            header_end = raw_response.find(b"\n\n")
            separator_size = 2
        if header_end < 0:
            raise httpx.RequestError("Invalid upstream response")
        raw_headers = raw_response[:header_end].decode("iso-8859-1", errors="replace").splitlines()
        status_line = raw_headers[0] if raw_headers else ""
        status_match = re.match(r"^HTTP/\d(?:\.\d)?\s+(\d{3})", status_line)
        if not status_match:
            raise httpx.RequestError(f"Invalid upstream status line: {status_line}")
        response_headers: list[tuple[str, str]] = []
        transfer_encodings: list[str] = []
        for line in raw_headers[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            header_name = name.strip()
            header_value = value.strip()
            if header_name.lower() == "transfer-encoding":
                transfer_encodings.append(header_value.lower())
            response_headers.append((header_name, header_value))
        response_body = bytes(raw_response[header_end + separator_size:])
        opened_socket = raw_socket
        raw_socket = None
        return _SwitchProxyLenientRawResponse(
            status_code=int(status_match.group(1)),
            headers=response_headers,
            transfer_encodings=transfer_encodings,
            initial_body=response_body,
            raw_socket=opened_socket,
        )
    except httpx.RequestError:
        raise
    except Exception as exc:
        raise httpx.RequestError(str(exc) or exc.__class__.__name__) from exc
    finally:
        if raw_socket is not None:
            try:
                raw_socket.close()
            except Exception:
                pass


def _request_switch_proxy_lenient_sync(*, method: str, target_url: str, headers: dict[str, str], content: bytes | None = None) -> httpx.Response:
    raw_response = _open_switch_proxy_lenient_raw_response(
        method=method,
        target_url=target_url,
        headers=headers,
        content=content,
    )
    response_body = raw_response.read_body()
    return httpx.Response(
        status_code=int(raw_response.status_code),
        headers=raw_response.headers,
        content=response_body,
        request=httpx.Request(str(method or "GET").upper(), target_url),
    )


async def _request_switch_proxy_lenient(*, method: str, target_url: str, headers: dict[str, str], content: bytes | None = None) -> httpx.Response:
    return await asyncio.to_thread(
        _request_switch_proxy_lenient_sync,
        method=method,
        target_url=target_url,
        headers=headers,
        content=content,
    )


async def _open_switch_proxy_lenient_raw_response_async(
    *,
    method: str,
    target_url: str,
    headers: dict[str, str],
    content: bytes | None = None,
) -> _SwitchProxyLenientRawResponse:
    return await asyncio.to_thread(
        _open_switch_proxy_lenient_raw_response,
        method=method,
        target_url=target_url,
        headers=headers,
        content=content,
    )


async def _send_switch_proxy_request(
    *,
    client: httpx.AsyncClient | None,
    method: str,
    target_url: str,
    headers: dict[str, str],
    content: bytes | None = None,
) -> httpx.Response:
    request_kwargs: dict[str, object] = {
        "method": str(method or "GET").upper(),
        "url": target_url,
        "headers": dict(headers or {}),
    }
    if content is not None:
        request_kwargs["content"] = content
    request = httpx.Request(**request_kwargs)
    if client is not None:
        return await client.send(request)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(45.0, connect=10.0),
        verify=False,
        follow_redirects=False,
        limits=_SWITCH_PROXY_CLIENT_LIMITS,
    ) as transient_client:
        return await transient_client.send(request)


def _build_switch_proxy_legacy_redirect_url(*, request: Request, root: str, proxy_path: str) -> str | None:
    prefix = str(request.cookies.get(_SWITCH_PROXY_PREFIX_COOKIE) or "").strip()
    if not prefix.startswith("/devices/") or "/web-ui" not in prefix:
        return None
    normalized_root = str(root or "").strip("/")
    normalized_path = str(proxy_path or "").lstrip("/")
    target = f"{prefix}/{normalized_root}"
    if normalized_path:
        target = f"{target}/{normalized_path}"
    query = str(request.url.query or "")
    return f"{target}?{query}" if query else target


def _resolve_switch_proxy_prefix_from_request(request: Request) -> str:
    prefix = str(request.cookies.get(_SWITCH_PROXY_PREFIX_COOKIE) or "").strip()
    if not prefix.startswith("/devices/") or "/web-ui" not in prefix:
        return ""
    return prefix.rstrip("/")


def _resolve_switch_proxy_root_redirect_url(*, request: Request, proxy_prefix: str) -> str:
    normalized_prefix = str(proxy_prefix or "").rstrip("/")
    default_login_url = f"{normalized_prefix}/web/device/login?lang=0"
    referer = str(request.headers.get("referer") or "").strip()
    if not referer:
        return ""
    try:
        parsed = urllib.parse.urlsplit(referer)
    except Exception:
        return ""
    referer_path = str(parsed.path or "").strip()
    referer_query = _strip_proxy_token_from_query(str(parsed.query or ""))
    if not (referer_path == normalized_prefix or referer_path.startswith(f"{normalized_prefix}/")):
        return ""
    if referer_path.startswith(f"{normalized_prefix}/"):
        referer_relative_path = referer_path[len(normalized_prefix) :]
        if not referer_relative_path.startswith("/"):
            referer_relative_path = f"/{referer_relative_path}"
        lowered_relative_path = referer_relative_path.lower()
        if lowered_relative_path == "/web/login":
            # /Web/login is a login submit endpoint on Aruba/HPE firmware.
            # After an error, browser scripts may force top.location="/".
            # Redirecting back to /Web/login loops on "Input parameter error",
            # so always bounce to the canonical login form page instead.
            return default_login_url
        if (
            lowered_relative_path in {"/web/device/login", "/html/logincheck"}
            or lowered_relative_path.startswith("/htdocs/login/")
        ):
            if referer_query:
                return f"{normalized_prefix}{referer_relative_path}?{referer_query}"
            return f"{normalized_prefix}{referer_relative_path}"
    if referer_path.startswith(f"{normalized_prefix}/wcn/logout"):
        return default_login_url
    if referer_path == f"{normalized_prefix}/wcn/frame/tree":
        uid_values = urllib.parse.parse_qs(referer_query, keep_blank_values=True).get("uid", [])
        resolved_uid = next((str(item or "").strip() for item in uid_values if str(item or "").strip()), "")
        if not resolved_uid:
            return default_login_url
        encoded_uid = urllib.parse.quote(resolved_uid, safe="")
        return f"{normalized_prefix}/wcn/frame/.x?uid={encoded_uid}"
    if referer_path.startswith(f"{normalized_prefix}/wcn/frame/"):
        if referer_query:
            return f"{normalized_prefix}/wcn/frame/.x?{referer_query}"
        return f"{normalized_prefix}/wcn/frame/.x"
    return default_login_url


def _register_devices_routes(app: FastAPI, get_services, require_session, require_websocket_session, require_monitoring_module) -> None:
    def _device_with_saved_config(api: ApiServices, row: dict) -> dict:
        payload = dict(row or {})
        dtype = str(payload.get("device_type") or payload.get("type") or "").strip().lower()
        if not dtype:
            payload["has_saved_config"] = False
            return payload
        if not api.model.is_config_download_type(dtype):
            payload["has_saved_config"] = False
            return payload
        device_name = str(payload.get("name", "")).strip()
        device_id = str(payload.get("id", "")).strip()
        try:
            payload["has_saved_config"] = api.device_config_files.has_config_files(
                device_type=dtype,
                device_id=device_id,
                device_name=device_name,
            )
        except Exception:
            payload["has_saved_config"] = False
        return payload

    def _require_monitoring_query_session(*, token: str, api: ApiServices):
        session = require_websocket_session(str(token or "").strip(), api)
        if session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expiree.")
        checker = getattr(api.logs, "subject_has_module", None)
        if callable(checker):
            allowed = bool(checker(subject=str(session.subject), module_code="monitoring"))
        else:
            allowed = str(session.subject).strip().lower() in {"sa", "admin"}
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse pour le module 'monitoring'.")
        return session

    @app.get("/devices", response_model=list[DeviceResponse])
    def list_devices(
        device_type: Optional[str] = None,
        q: Optional[str] = None,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[DeviceResponse]:
        rows = api.model.search_devices(q, device_type=device_type) if q else api.model.list_devices(device_type=device_type)
        return [DeviceResponse(**_with_device_version_token(_device_with_saved_config(api, row))) for row in rows]

    @app.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
    def create_device(
        payload: DeviceCreateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceResponse:
        try:
            device_id = api.model.add_device(
                payload.device_type,
                payload.name,
                payload.ip,
                payload.description,
                id_Teamviewer=payload.id_Teamviewer,
                device_subtype=payload.device_subtype,
                action_double_click=payload.action_double_click,
                web_url=payload.web_url,
                ssh_user=payload.ssh_user,
                device_login=payload.device_login,
                device_password=payload.device_password,
                custom_data=payload.custom_data,
                notify=payload.notify,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        if device_id is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Adresse IP deja utilisee pour ce type.")
        row = api.model.get_device_row(payload.device_type, device_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable apres creation.")
        return DeviceResponse(**_with_device_version_token(_device_with_saved_config(api, row)))

    @app.put("/devices/{device_type}/{device_id}", response_model=DeviceResponse)
    def update_device(
        device_type: str,
        device_id: str,
        payload: DeviceUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceResponse:
        existing_row = api.model.get_device_row(device_type, device_id)
        if existing_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable.")
        _assert_version_token(
            expected=_device_version_token(existing_row),
            received=str(payload.version_token or ""),
            resource_label=f"Equipement {device_id}",
        )
        try:
            ok = api.model.update_device(
                device_type,
                device_id,
                new_name=payload.name,
                new_ip=payload.ip,
                new_description=payload.description,
                id_Teamviewer=payload.id_Teamviewer,
                device_subtype=payload.device_subtype,
                action_double_click=payload.action_double_click,
                web_url=payload.web_url,
                ssh_user=payload.ssh_user,
                device_login=payload.device_login,
                device_password=payload.device_password,
                custom_data=payload.custom_data,
                notify=payload.notify,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable.")
        row = api.model.get_device_row(device_type, device_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable apres mise a jour.")
        return DeviceResponse(**_with_device_version_token(_device_with_saved_config(api, row)))

    @app.delete("/devices/{device_type}/{device_id}", response_model=MessageResponse)
    def delete_device(
        device_type: str,
        device_id: str,
        version_token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        existing_row = api.model.get_device_row(device_type, device_id)
        if existing_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable.")
        _assert_version_token(
            expected=_device_version_token(existing_row),
            received=version_token,
            resource_label=f"Equipement {device_id}",
        )
        if not api.model.delete_device(device_type, device_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable.")
        return MessageResponse(message="Equipement supprime.")

    @app.post("/devices/{device_type}/{device_id}/credentials/reveal", response_model=DeviceCredentialRevealResponse)
    def reveal_device_credentials(
        device_type: str,
        device_id: str,
        payload: DeviceCredentialRevealRequest,
        api: ApiServices = Depends(get_services),
        session=Depends(require_monitoring_module),
    ) -> DeviceCredentialRevealResponse:
        normalized_type = str(device_type or "").strip().lower()
        target_id = str(device_id or "").strip()
        row = api.model.get_device_row(normalized_type, target_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable.")

        subject = str(getattr(session, "subject", "") or "").strip()
        if not api.auth.verify_user_password(subject, str(payload.session_password or "")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mot de passe de session invalide.")

        device_password = str(row.get("device_password") or "")
        if not device_password:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun mot de passe stocke pour cet equipement.")

        return DeviceCredentialRevealResponse(
            device_login=str(row.get("device_login") or ""),
            device_password=device_password,
        )

    @app.get("/devices/{device_type}/{device_id}/remote-desktop/shortcut", include_in_schema=False)
    def download_remote_desktop_shortcut(
        device_type: str,
        device_id: str,
        token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
    ) -> Response:
        _require_monitoring_query_session(token=token, api=api)
        normalized_type = str(device_type or "").strip().lower()
        target_id = str(device_id or "").strip()
        device_row = api.model.get_device_row(normalized_type, target_id)
        if device_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable.")
        ip = str(device_row.get("ip") or "").strip()
        if not ip:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="IP manquante pour la connexion Remote Desktop.")
        name = str(device_row.get("name") or "").strip()
        payload = _build_rdp_shortcut_content(device_name=name, device_ip=ip)
        filename = _build_rdp_shortcut_filename(device_name=name, device_ip=ip)
        return Response(
            content=payload,
            media_type="application/x-rdp",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.post("/devices/import/preview", response_model=DeviceImportPreviewResponse)
    def preview_devices_import(
        payload: DeviceImportRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceImportPreviewResponse:
        raw_bytes = _decode_base64_payload(content_base64=payload.content_base64)
        allowed_types = {str(code or "").strip().lower() for code in dict(api.model.type_definitions or {}).keys()}
        selected_sheet_name = ""
        available_sheets: list[str] = []
        try:
            selected_sheet_name, available_sheets = resolve_tabular_sheet_selection(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=str(payload.sheet_name or ""),
            )
            parsed = parse_tabular_file_with_metadata(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=selected_sheet_name,
                header_mode=str(payload.header_mode or ""),
                header_row_number=int(payload.header_row_number or 1),
            )
            source_headers = parsed.headers
            source_rows = parsed.rows
            rows, detected_rows, detected_columns, issues = infer_devices_from_rows(
                headers=source_headers,
                raw_rows=source_rows,
                default_device_type=str(payload.default_device_type or ""),
                allowed_device_types=allowed_types,
                column_mappings=list(payload.column_mappings or []),
                fail_on_empty=False,
            )
            effective_mapping = resolve_effective_column_mapping(
                headers=source_headers,
                column_mappings=list(payload.column_mappings or []),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analyse du fichier impossible: {exc}") from exc
        return DeviceImportPreviewResponse(
            rows=_sanitize_device_import_preview_rows(rows),
            detected_rows=int(detected_rows),
            detected_columns=int(detected_columns),
            issues=[str(item or "") for item in list(issues or []) if str(item or "").strip()],
            source_headers=[str(item or "") for item in list(source_headers or [])],
            source_rows_preview=[
                [str(value or "") for value in list(row or [])]
                for row in list(parsed.source_rows or [])[:12]
            ],
            available_sheets=[str(item or "") for item in list(available_sheets or []) if str(item or "").strip()],
            selected_sheet_name=str(selected_sheet_name or ""),
            detected_header_row_number=int(parsed.detected_header_row_number or 1),
            effective_header_mode=str(parsed.effective_header_mode or "auto"),
            effective_mapping=effective_mapping,
        )

    @app.post("/devices/import/apply", response_model=DeviceImportApplyResponse)
    def apply_devices_import(
        payload: DeviceImportRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceImportApplyResponse:
        raw_bytes = _decode_base64_payload(content_base64=payload.content_base64)
        allowed_types = {str(code or "").strip().lower() for code in dict(api.model.type_definitions or {}).keys()}
        selected_sheet_name = ""
        try:
            selected_sheet_name, _available_sheets = resolve_tabular_sheet_selection(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=str(payload.sheet_name or ""),
            )
            parsed = parse_tabular_file_with_metadata(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=selected_sheet_name,
                header_mode=str(payload.header_mode or ""),
                header_row_number=int(payload.header_row_number or 1),
            )
            rows, detected_rows, _detected_columns, parser_issues = infer_devices_from_rows(
                headers=parsed.headers,
                raw_rows=parsed.rows,
                default_device_type=str(payload.default_device_type or ""),
                allowed_device_types=allowed_types,
                column_mappings=list(payload.column_mappings or []),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analyse du fichier impossible: {exc}") from exc

        upsert_existing = bool(payload.upsert_existing)
        credential_mode = normalize_credential_import_mode(payload.credential_mode)
        created = 0
        updated = 0
        skipped = len(list(parser_issues or []))
        issues = [str(item or "") for item in list(parser_issues or []) if str(item or "").strip()]

        existing_by_type_ip: dict[tuple[str, str], dict] = {}
        for row in list(api.model.list_devices() or []):
            type_code = str(row.get("device_type") or row.get("type") or "").strip().lower()
            ip = str(row.get("ip") or "").strip()
            if type_code and ip:
                existing_by_type_ip[(type_code, ip)] = dict(row)

        schema_cache: dict[str, tuple[list[dict], list[dict]]] = {}
        for row in rows:
            device_type = str(row.get("device_type") or "").strip().lower()
            name = str(row.get("name") or "").strip()
            ip = str(row.get("ip") or "").strip()
            if not device_type or not ip:
                skipped += 1
                issues.append("Ligne ignoree: type ou IP manquant.")
                continue
            if device_type not in allowed_types:
                skipped += 1
                issues.append(f"Type inconnu ignore: {device_type}.")
                continue

            if device_type not in schema_cache:
                schema_cache[device_type] = api.device_types.load_schema(device_type)
            fields, actions = schema_cache[device_type]
            custom_data = dict(row.get("custom_data") or {})
            if custom_data:
                standard_keys = {
                    "name",
                    "ip",
                    "description",
                    "id_Teamviewer",
                    "type",
                    "device_subtype",
                    "action_double_click",
                    "web_url",
                    "ssh_user",
                    "device_login",
                    "device_password",
                    "config_saved",
                    "notify",
                }
                allowed_custom_keys = {
                    str(field.get("field_key") or "").strip().lower()
                    for field in list(fields or [])
                    if isinstance(field, dict)
                    and str(field.get("field_key") or "").strip()
                    and str(field.get("field_key") or "").strip().lower() not in standard_keys
                }
                filtered_custom_data = {
                    key: value
                    for key, value in custom_data.items()
                    if str(key or "").strip().lower() in allowed_custom_keys
                }
                ignored_custom_keys = sorted(
                    str(key or "").strip()
                    for key in custom_data.keys()
                    if str(key or "").strip().lower() not in allowed_custom_keys
                )
                if ignored_custom_keys:
                    issues.append(
                        f"{name or ip}: champ(s) ignore(s) car absents du type {device_type}: {', '.join(ignored_custom_keys)}."
                    )
                row["custom_data"] = filtered_custom_data
                custom_data = filtered_custom_data
            credentials_enabled = _device_schema_supports_credentials(fields)
            try:
                validate_action_double_click(
                    fields=fields,
                    actions=actions,
                    device_subtype=str(row.get("device_subtype") or ""),
                    action_double_click=str(row.get("action_double_click") or ""),
                )
            except ValueError as exc:
                skipped += 1
                issues.append(f"{name} ({ip}): {exc}")
                continue

            imported_login_present = "device_login" in row
            imported_password_present = "device_password" in row
            imported_login_value = str(row.get("device_login") or "") if imported_login_present else ""
            imported_password_value = str(row.get("device_password") or "") if imported_password_present else ""
            if not credentials_enabled and (imported_login_value.strip() or imported_password_value.strip()):
                issues.append(
                    f"{name} ({ip}): identifiants importes ignores (gestion des identifiants desactivee pour ce type)."
                )

            existing = existing_by_type_ip.get((device_type, ip))
            if existing is not None:
                if not name:
                    name = str(existing.get("name") or "").strip()
                if not upsert_existing:
                    skipped += 1
                    issues.append(f"{name} ({ip}): equipement deja present, ignore.")
                    continue
                resolved_credentials = resolve_credential_import_values(
                    mode=credential_mode,
                    operation="update",
                    login_present=imported_login_present and credentials_enabled,
                    login_value=imported_login_value,
                    password_present=imported_password_present and credentials_enabled,
                    password_value=imported_password_value,
                )
                try:
                    ok = api.model.update_device(
                        device_type=device_type,
                        device_id=str(existing.get("id") or ""),
                        new_name=name,
                        new_ip=ip,
                        new_description=str(row.get("description") or ""),
                        id_Teamviewer=str(row.get("id_Teamviewer") or ""),
                        device_subtype=str(row.get("device_subtype") or ""),
                        action_double_click=str(row.get("action_double_click") or ""),
                        web_url=str(row.get("web_url") or ""),
                        ssh_user=str(row.get("ssh_user") or ""),
                        device_login=resolved_credentials.login,
                        device_password=resolved_credentials.password,
                        custom_data=custom_data,
                        notify=bool(row.get("notify", True)),
                    )
                except Exception as exc:
                    log_with_timestamp(f"Import equipement: mise a jour impossible pour {device_type}/{ip}: {exc}", level="WARNING")
                    skipped += 1
                    issues.append(_format_device_import_row_error(name=name, ip=ip, exc=exc))
                    continue
                if ok:
                    updated += 1
                else:
                    skipped += 1
                    issues.append(f"{name or ip} ({ip}): mise a jour impossible.")
                continue

            if not name:
                skipped += 1
                issues.append(f"{ip}: creation impossible, nom manquant.")
                continue

            resolved_credentials = resolve_credential_import_values(
                mode=credential_mode,
                operation="create",
                login_present=imported_login_present and credentials_enabled,
                login_value=imported_login_value,
                password_present=imported_password_present and credentials_enabled,
                password_value=imported_password_value,
            )
            try:
                created_id = api.model.add_device(
                    device_type=device_type,
                    name=name,
                    ip=ip,
                    description=str(row.get("description") or ""),
                    id_Teamviewer=str(row.get("id_Teamviewer") or ""),
                    device_subtype=str(row.get("device_subtype") or ""),
                    action_double_click=str(row.get("action_double_click") or ""),
                    web_url=str(row.get("web_url") or ""),
                    ssh_user=str(row.get("ssh_user") or ""),
                    device_login=resolved_credentials.login,
                    device_password=resolved_credentials.password,
                    custom_data=custom_data,
                    notify=bool(row.get("notify", True)),
                )
            except Exception as exc:
                log_with_timestamp(f"Import equipement: creation impossible pour {device_type}/{ip}: {exc}", level="WARNING")
                skipped += 1
                issues.append(_format_device_import_row_error(name=name, ip=ip, exc=exc))
                continue
            if created_id is None:
                skipped += 1
                issues.append(f"{name} ({ip}): creation ignoree (IP deja utilisee).")
                continue
            created += 1
            existing_by_type_ip[(device_type, ip)] = {
                "id": str(created_id),
                "device_type": device_type,
                "ip": ip,
            }

        return DeviceImportApplyResponse(
            processed=int(detected_rows),
            created=int(created),
            updated=int(updated),
            skipped=int(skipped),
            issues=issues,
        )

    @app.api_route(
        "/devices/{device_type}/{device_id}/web-ui",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        include_in_schema=False,
    )
    @app.api_route(
        "/devices/{device_type}/{device_id}/web-ui/{proxy_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        include_in_schema=False,
    )
    async def proxy_device_web_ui(
        request: Request,
        device_type: str,
        device_id: str,
        proxy_path: str = "",
        token: Optional[str] = Query(default=None),
        authorization: Optional[str] = Header(default=None),
        api: ApiServices = Depends(get_services),
    ) -> Response:
        cookie_token = request.cookies.get(_SWITCH_PROXY_TOKEN_COOKIE)
        session = _resolve_switch_proxy_session(
            api=api,
            authorization=authorization,
            token=token,
            cookie_token=cookie_token,
        )
        session_token_cookie_value = _switch_proxy_session_cookie_value(session)
        requested_device_locator = str(device_id or "").strip()
        known_devices = list(api.model.list_devices(device_type=device_type) or [])
        device = _resolve_switch_proxy_device_row(devices=known_devices, device_locator=requested_device_locator)
        if device is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable.")

        if not requested_device_locator:
            requested_device_locator = str(device.get("id") or "").strip()
        base = _resolve_switch_base_url(device)
        base_candidates = _build_switch_base_fallback_chain(base)
        active_base = base_candidates[0]
        proxy_prefix = (
            f"/devices/{urllib.parse.quote(str(device_type), safe='')}/"
            f"{urllib.parse.quote(str(requested_device_locator), safe='')}/web-ui"
        )
        raw_query = bytes(request.scope.get("query_string") or b"").decode("latin-1", errors="ignore")
        upstream_query = _strip_proxy_token_from_query(
            raw_query,
            auth_token=str(getattr(session, "token", "") or ""),
        )
        target_url = _build_switch_target_url(
            base=active_base,
            proxy_path=proxy_path,
            query_string=upstream_query,
        )
        resolved_device_id = str(device.get("id") or "").strip()
        device_gate_key = (
            f"{str(device_type or '').strip().lower()}:"
            f"{resolved_device_id.lower()}:"
            f"{str(active_base.netloc or '').strip().lower()}"
        )
        device_semaphore = _get_switch_proxy_device_semaphore(device_gate_key)

        method = str(request.method or "GET").upper()
        body = await request.body()
        forward_body = body if method not in {"GET", "HEAD"} else None
        proxy_cookie_secure = str(request.url.scheme or "").lower() == "https"

        upstream: httpx.Response | None = None
        last_request_error: httpx.RequestError | None = None
        resolved_proxy_path = str(proxy_path or "").strip().lstrip("/")
        shared_proxy_client = _get_switch_proxy_http_client()
        download_retry_diagnostics: list[str] = []
        async with device_semaphore:
            for candidate_index, candidate_base in enumerate(base_candidates):
                active_base = candidate_base
                target_url = _build_switch_target_url(
                    base=active_base,
                    proxy_path=proxy_path,
                    query_string=upstream_query,
                )
                request_headers = _build_switch_proxy_request_headers(
                    request=request,
                    base=active_base,
                    target_url=target_url,
                    proxy_prefix=proxy_prefix,
                )
                is_last_candidate = candidate_index + 1 >= len(base_candidates)
                max_attempts = 3 if method in {"GET", "HEAD", "OPTIONS"} else 1
                if not is_last_candidate:
                    max_attempts = 1
                for attempt in range(max_attempts):
                    try:
                        upstream = await _send_switch_proxy_request(
                            client=shared_proxy_client,
                            method=method,
                            target_url=target_url,
                            headers=request_headers,
                            content=forward_body,
                        )
                        break
                    except httpx.RequestError as exc:
                        last_request_error = exc
                        if (
                            method == "GET"
                            and "http_download" in str(resolved_proxy_path or "").strip().lower()
                            and _is_switch_proxy_multiple_transfer_encoding_error(exc)
                        ):
                            raw_upstream = await _open_switch_proxy_lenient_raw_response_async(
                                method=method,
                                target_url=target_url,
                                headers=request_headers,
                                content=forward_body,
                            )
                            if (
                                int(raw_upstream.status_code) == status.HTTP_200_OK
                                and _is_switch_proxy_attachment_response(httpx.Headers(raw_upstream.headers))
                            ):
                                image_download_started_at = time.time()

                                def _iter_switch_proxy_download_body():
                                    completed = False
                                    try:
                                        for chunk in raw_upstream.iter_body():
                                            yield chunk
                                        completed = True
                                    finally:
                                        if completed:
                                            _mark_switch_proxy_download_completed(device_gate_key)

                                streaming_response = StreamingResponse(
                                    _iter_switch_proxy_download_body(),
                                    status_code=int(raw_upstream.status_code),
                                )
                                for header_name, header_value in raw_upstream.headers:
                                    lowered = str(header_name or "").strip().lower()
                                    if lowered in _SWITCH_PROXY_HOP_BY_HOP_HEADERS or lowered in {"content-length", "content-encoding"}:
                                        continue
                                    streaming_response.headers.append(str(header_name), str(header_value or ""))
                                normalized_content_type = _normalize_switch_proxy_response_content_type(
                                    content_type=str(streaming_response.headers.get("content-type") or ""),
                                    proxy_path=str(resolved_proxy_path or "").strip().lower(),
                                )
                                if normalized_content_type:
                                    streaming_response.headers["content-type"] = normalized_content_type
                                _set_switch_proxy_session_cookies(
                                    streaming_response,
                                    proxy_prefix=proxy_prefix,
                                    session_token_cookie_value=session_token_cookie_value,
                                    secure=proxy_cookie_secure,
                                )
                                _set_switch_proxy_image_download_started_cookie(
                                    streaming_response,
                                    proxy_prefix=proxy_prefix,
                                    secure=proxy_cookie_secure,
                                    started_at=image_download_started_at,
                                )
                                return streaming_response
                            upstream = httpx.Response(
                                status_code=int(raw_upstream.status_code),
                                headers=raw_upstream.headers,
                                content=raw_upstream.read_body(),
                                request=httpx.Request(method, target_url),
                            )
                            break
                        if attempt + 1 >= max_attempts:
                            break
                        await asyncio.sleep(0.2 * float(attempt + 1))
                if upstream is not None:
                    break
            if upstream is None:
                is_failed_load_status_request = method == "GET" and _is_switch_proxy_load_status_query(upstream_query)
                is_failed_load_status_delete_request = _is_switch_proxy_load_status_delete_request(
                    method=method,
                    query=upstream_query,
                    body=body,
                )
                has_image_started_cookie = bool(str(request.cookies.get(_SWITCH_PROXY_IMAGE_DOWNLOAD_STARTED_COOKIE) or "").strip())
                has_recent_download_or_marker = _has_recent_switch_proxy_download(device_gate_key) or has_image_started_cookie
                if (is_failed_load_status_request or is_failed_load_status_delete_request) and has_recent_download_or_marker:
                    image_download_started_at = _resolve_switch_proxy_image_download_started_at(request)
                    image_download_completion_due = (
                        _has_recent_switch_proxy_download(device_gate_key)
                        or _is_switch_proxy_image_download_completion_due(image_download_started_at)
                    )
                    response_body = (
                        _build_switch_proxy_successful_load_status_delete_body()
                        if is_failed_load_status_delete_request
                        else _build_switch_proxy_successful_load_status_body(completed=image_download_completion_due)
                    )
                    response = Response(content=response_body, status_code=status.HTTP_200_OK, media_type="text/xml")
                    _set_switch_proxy_load_status_headers(
                        response,
                        upstream_state="request-error-delete" if is_failed_load_status_delete_request else "request-error",
                        rewritten=True,
                        recent_download=True,
                        started_at=image_download_started_at,
                        completion_due=image_download_completion_due,
                    )
                    _set_switch_proxy_session_cookies(
                        response,
                        proxy_prefix=proxy_prefix,
                        session_token_cookie_value=session_token_cookie_value,
                        secure=proxy_cookie_secure,
                    )
                    _sync_switch_proxy_image_download_started_cookie(
                        response,
                        proxy_prefix=proxy_prefix,
                        secure=proxy_cookie_secure,
                        started_at=image_download_started_at,
                        completed=image_download_completion_due or is_failed_load_status_delete_request,
                    )
                    return response
                detail = _format_switch_proxy_request_error(last_request_error or httpx.RequestError("unknown error"))
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Switch inacessible via proxy: {detail}",
                ) from last_request_error

            if (
                method == "GET"
                and "http_download" in str(resolved_proxy_path or "").strip().lower()
                and _is_switch_proxy_login_redirect(upstream)
            ):
                retry_bases = [active_base] + [
                    candidate
                    for candidate in base_candidates
                    if urllib.parse.urlunsplit(candidate) != urllib.parse.urlunsplit(active_base)
                ]
                retry_queries = [upstream_query] + _build_switch_proxy_download_retry_queries(upstream_query)
                retry_done = False
                for retry_base in retry_bases:
                    for retry_query in retry_queries:
                        retry_diagnostic = f"base={retry_base.scheme}://{retry_base.netloc};query={retry_query}"
                        retry_target_url = _build_switch_target_url(
                            base=retry_base,
                            proxy_path=resolved_proxy_path,
                            query_string=retry_query,
                        )
                        retry_headers = _build_switch_proxy_request_headers(
                            request=request,
                            base=retry_base,
                            target_url=retry_target_url,
                            proxy_prefix=proxy_prefix,
                        )
                        try:
                            retry_upstream = await _send_switch_proxy_request(
                                client=shared_proxy_client,
                                method=method,
                                target_url=retry_target_url,
                                headers=retry_headers,
                            )
                            retry_diagnostic = (
                                f"{retry_diagnostic};status={int(retry_upstream.status_code)};"
                                f"location={str(retry_upstream.headers.get('location') or '').strip()}"
                            )
                            download_retry_diagnostics.append(retry_diagnostic)
                            if not _is_switch_proxy_login_redirect(retry_upstream):
                                upstream = retry_upstream
                                target_url = retry_target_url
                                upstream_query = retry_query
                                active_base = retry_base
                                retry_done = True
                                break
                        except httpx.RequestError as exc:
                            retry_diagnostic = f"{retry_diagnostic};error={exc.__class__.__name__}:{str(exc)}"
                            if _is_switch_proxy_multiple_transfer_encoding_error(exc):
                                try:
                                    retry_upstream = await _request_switch_proxy_lenient(
                                        method=method,
                                        target_url=retry_target_url,
                                        headers=retry_headers,
                                    )
                                    retry_diagnostic = (
                                        f"{retry_diagnostic};lenient_status={int(retry_upstream.status_code)};"
                                        f"lenient_location={str(retry_upstream.headers.get('location') or '').strip()}"
                                    )
                                    download_retry_diagnostics.append(retry_diagnostic)
                                    if not _is_switch_proxy_login_redirect(retry_upstream):
                                        upstream = retry_upstream
                                        target_url = retry_target_url
                                        upstream_query = retry_query
                                        active_base = retry_base
                                        retry_done = True
                                        break
                                except httpx.RequestError:
                                    download_retry_diagnostics.append(retry_diagnostic)
                                    pass
                            else:
                                download_retry_diagnostics.append(retry_diagnostic)
                            continue
                    if retry_done:
                        break

            if method == "GET" and int(upstream.status_code) == 404:
                for fallback_proxy_path in _build_switch_proxy_fallback_paths(resolved_proxy_path):
                    fallback_target_url = _build_switch_target_url(
                        base=active_base,
                        proxy_path=fallback_proxy_path,
                        query_string=upstream_query,
                    )
                    fallback_headers = _build_switch_proxy_request_headers(
                        request=request,
                        base=active_base,
                        target_url=fallback_target_url,
                        proxy_prefix=proxy_prefix,
                    )
                    try:
                        fallback_upstream = await _send_switch_proxy_request(
                            client=shared_proxy_client,
                            method=method,
                            target_url=fallback_target_url,
                            headers=fallback_headers,
                        )
                        if int(fallback_upstream.status_code) != 404:
                            upstream = fallback_upstream
                            target_url = fallback_target_url
                            resolved_proxy_path = fallback_proxy_path
                            break
                    except httpx.RequestError:
                        continue

        proxy_path_lower = str(resolved_proxy_path or "").strip().lower()
        if method == "GET" and (proxy_path_lower == "wcn/logout" or proxy_path_lower.endswith("/wcn/logout")):
            response = RedirectResponse(
                url=f"{proxy_prefix}/web/device/login?lang=0",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            )
            response.headers.setdefault("Cache-Control", "no-store")
            _set_switch_proxy_session_cookies(
                response,
                proxy_prefix=proxy_prefix,
                session_token_cookie_value=session_token_cookie_value,
                secure=proxy_cookie_secure,
            )
            return response

        response_body = b"" if method == "HEAD" else bytes(upstream.content or b"")
        content_type = str(upstream.headers.get("content-type") or "").strip().lower()
        is_attachment = _is_switch_proxy_attachment_response(upstream.headers)
        is_load_status_request = method == "GET" and _is_switch_proxy_load_status_query(upstream_query)
        load_status_upstream_state = ""
        load_status_rewritten = False
        image_download_started_at: float | None = None
        image_download_completion_due = False
        image_download_cookie_needed = False
        if method != "HEAD" and not is_attachment and _is_switch_proxy_html_response(content_type=content_type, proxy_path=proxy_path_lower):
            response_body = _rewrite_switch_proxy_html(
                body=response_body,
                proxy_prefix=proxy_prefix,
                base=active_base,
                proxy_path=resolved_proxy_path,
            )
        elif method != "HEAD" and not is_attachment and ("javascript" in content_type or proxy_path_lower.endswith(".js")):
            response_body = _rewrite_switch_proxy_javascript(body=response_body, proxy_prefix=proxy_prefix, base=active_base)
        elif method != "HEAD" and not is_attachment and ("xml" in content_type or proxy_path_lower.endswith(".xml") or proxy_path_lower.endswith("/web/login")):
            response_body = _rewrite_switch_proxy_xml(
                body=response_body,
                proxy_prefix=proxy_prefix,
                client_scheme=str(request.url.scheme or ""),
            )
            if is_load_status_request:
                load_status_upstream_state = _classify_switch_proxy_load_status(response_body)
            if (
                is_load_status_request
                and (
                    _has_recent_switch_proxy_download(device_gate_key)
                    or _is_switch_proxy_image_download_false_abort(response_body)
                )
            ):
                image_false_abort = _is_switch_proxy_image_download_false_abort(response_body)
                if image_false_abort:
                    image_download_started_at = _resolve_switch_proxy_image_download_started_at(request)
                    image_download_completion_due = (
                        _has_recent_switch_proxy_download(device_gate_key)
                        or _is_switch_proxy_image_download_completion_due(image_download_started_at)
                    )
                    image_download_cookie_needed = True
                rewritten_body = _rewrite_switch_proxy_recent_download_load_status(
                    response_body,
                    completed=(not image_false_abort or image_download_completion_due),
                )
                load_status_rewritten = rewritten_body != response_body
                response_body = rewritten_body
        upstream_status = int(upstream.status_code)
        response_status = upstream_status
        upstream_location = str(upstream.headers.get("location") or "").strip()
        if upstream_location and upstream_status in {301, 308}:
            response_status = status.HTTP_307_TEMPORARY_REDIRECT
        response = Response(content=response_body, status_code=response_status)

        for header_name, header_value in upstream.headers.multi_items():
            lowered = str(header_name or "").strip().lower()
            if lowered in _SWITCH_PROXY_HOP_BY_HOP_HEADERS or lowered in {"content-length", "content-encoding"}:
                continue
            value = str(header_value or "")
            if lowered == "location":
                value = _rewrite_switch_proxy_location(location=value, base=active_base, proxy_prefix=proxy_prefix)
            elif lowered == "refresh":
                value = _rewrite_switch_proxy_refresh(value=value, base=active_base, proxy_prefix=proxy_prefix)
            elif lowered == "set-cookie":
                value = _rewrite_switch_proxy_set_cookie(value=value, proxy_prefix=proxy_prefix)
            response.headers.append(str(header_name), value)
        if response.status_code in {status.HTTP_301_MOVED_PERMANENTLY, status.HTTP_302_FOUND, status.HTTP_303_SEE_OTHER, status.HTTP_307_TEMPORARY_REDIRECT, status.HTTP_308_PERMANENT_REDIRECT}:
            response.headers.setdefault("Cache-Control", "no-store")
        if download_retry_diagnostics:
            response.headers["X-ITops-Switch-Download-Retry-Diagnostics"] = " | ".join(download_retry_diagnostics)[:3500]
        normalized_content_type = _normalize_switch_proxy_response_content_type(
            content_type=str(response.headers.get("content-type") or content_type),
            proxy_path=proxy_path_lower,
        )
        if normalized_content_type:
            response.headers["content-type"] = normalized_content_type
        if is_load_status_request:
            _set_switch_proxy_load_status_headers(
                response,
                upstream_state=load_status_upstream_state or _classify_switch_proxy_load_status(response_body),
                rewritten=load_status_rewritten,
                recent_download=_has_recent_switch_proxy_download(device_gate_key),
                started_at=image_download_started_at,
                completion_due=image_download_completion_due,
            )

        _set_switch_proxy_session_cookies(
            response,
            proxy_prefix=proxy_prefix,
            session_token_cookie_value=session_token_cookie_value,
            secure=proxy_cookie_secure,
        )
        if image_download_cookie_needed and image_download_started_at is not None and not image_download_completion_due:
            _set_switch_proxy_image_download_started_cookie(
                response,
                proxy_prefix=proxy_prefix,
                secure=proxy_cookie_secure,
                started_at=image_download_started_at,
            )
        elif image_download_cookie_needed and image_download_completion_due:
            _sync_switch_proxy_image_download_started_cookie(
                response,
                proxy_prefix=proxy_prefix,
                secure=proxy_cookie_secure,
                started_at=image_download_started_at or time.time(),
                completed=True,
            )
        if (
            method == "GET"
            and response.status_code == status.HTTP_200_OK
            and "http_download" in proxy_path_lower
            and _is_switch_proxy_attachment_response(response.headers)
            and _switch_proxy_response_has_download_body(response_body=response_body, headers=response.headers)
        ):
            _mark_switch_proxy_download_completed(device_gate_key)
        return response

    @app.api_route("/web/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/Web/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/hpe/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/device/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/htdocs/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/html/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/cgi/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/cgi-bin/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/xsl/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/wcn/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/wnm/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/en/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/cn/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/images/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/nextgen/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/customdir/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    @app.api_route("/skin/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
    async def proxy_device_web_ui_legacy_root(request: Request, proxy_path: str = "") -> Response:
        root = str(request.url.path or "/").split("/", 2)[1] if str(request.url.path or "").startswith("/") else ""
        redirect_url = _build_switch_proxy_legacy_redirect_url(request=request, root=root, proxy_path=proxy_path)
        if not redirect_url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ressource introuvable.")
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    @app.get("/devices/export")
    @app.get("/devices/export/csv")
    def export_devices(
        device_type: Optional[str] = None,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> StreamingResponse:
        rows = list(api.model.list_devices(device_type=device_type) or [])
        csv_bytes = export_devices_to_csv(rows=rows)
        normalized_type = str(device_type or "").strip().lower()
        suffix = normalized_type if normalized_type else "all"
        filename = f"devices_{suffix}.csv"
        return _csv_stream_response(csv_bytes=csv_bytes, filename=filename)

    @app.get("/device-types", response_model=list[DeviceTypeResponse])
    def list_device_types(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[DeviceTypeResponse]:
        return [DeviceTypeResponse(**_with_type_version_token(row)) for row in api.device_types.list_types()]

    @app.post("/device-types", response_model=DeviceTypeResponse, status_code=status.HTTP_201_CREATED)
    def create_device_type(
        payload: DeviceTypeCreateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceTypeResponse:
        code = api.device_types.create_type(
            label=payload.label,
            monitoring_enabled=bool(payload.monitoring_enabled),
            config_backups_enabled=payload.config_backups_enabled,
        )
        api.model.refresh_type_definitions()
        api.model.notify_state_changed()
        row = api.device_types.get_type(code)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type introuvable apres creation.")
        return DeviceTypeResponse(**_with_type_version_token(row))

    @app.put("/device-types/{type_code}", response_model=DeviceTypeResponse)
    def update_device_type(
        type_code: str,
        payload: DeviceTypeUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceTypeResponse:
        existing_row = api.device_types.get_type(type_code)
        if existing_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type introuvable.")
        _assert_version_token(
            expected=_type_version_token(existing_row),
            received=str(payload.version_token or ""),
            resource_label=f"Type {type_code}",
        )
        code = api.device_types.save_type(
            code=type_code,
            label=payload.label,
            monitoring_enabled=bool(payload.monitoring_enabled),
            config_backups_enabled=payload.config_backups_enabled,
        )
        api.model.refresh_type_definitions()
        api.model.notify_state_changed()
        row = api.device_types.get_type(code)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type introuvable apres mise a jour.")
        return DeviceTypeResponse(**_with_type_version_token(row))

    @app.post("/device-types/{type_code}/credentials/purge", response_model=MessageResponse)
    def purge_device_type_credentials(
        type_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        existing_row = api.device_types.get_type(type_code)
        if existing_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type introuvable.")
        normalized_code = str(existing_row.get("code") or type_code).strip().lower()
        purger = getattr(api.model, "purge_type_credentials", None)
        if not callable(purger):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Purge des identifiants indisponible.")
        try:
            updated_rows = int(purger(normalized_code) or 0)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Purge des identifiants impossible: {exc}") from exc
        return MessageResponse(message=f"Identifiants supprimes sur {updated_rows} equipement(s).")

    @app.delete("/device-types/{type_code}", response_model=MessageResponse)
    def delete_device_type(
        type_code: str,
        cascade_devices: bool = False,
        version_token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        existing_row = api.device_types.get_type(type_code)
        if existing_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type introuvable.")
        _assert_version_token(
            expected=_type_version_token(existing_row),
            received=version_token,
            resource_label=f"Type {type_code}",
        )
        try:
            deleted = api.device_types.delete_type(type_code, cascade_devices=bool(cascade_devices))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type introuvable.")
        api.model.refresh_type_definitions()
        api.model.notify_state_changed()
        return MessageResponse(message="Type supprime.")

    @app.get("/device-types/{type_code}/schema", response_model=DeviceTypeSchemaResponse)
    def get_device_type_schema(
        type_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceTypeSchemaResponse:
        fields, actions = api.device_types.load_schema(type_code)
        return DeviceTypeSchemaResponse(fields=fields, actions=actions, version_token=_schema_version_token(fields=fields, actions=actions))

    @app.put("/device-types/{type_code}/schema", response_model=DeviceTypeSchemaResponse)
    def save_device_type_schema(
        type_code: str,
        payload: DeviceTypeSchemaUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceTypeSchemaResponse:
        existing_fields, existing_actions = api.device_types.load_schema(type_code)
        _assert_version_token(
            expected=_schema_version_token(fields=existing_fields, actions=existing_actions),
            received=str(payload.version_token or ""),
            resource_label=f"Schema type {type_code}",
        )
        try:
            api.device_types.replace_schema(
                type_code=type_code,
                fields=list(payload.fields or []),
                actions=list(payload.actions or []),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        api.model.refresh_type_definitions()
        api.model.notify_state_changed()
        fields, actions = api.device_types.load_schema(type_code)
        return DeviceTypeSchemaResponse(fields=fields, actions=actions, version_token=_schema_version_token(fields=fields, actions=actions))


def _register_logs_routes(app: FastAPI, get_services, require_session, require_monitoring_module) -> None:
    @app.get("/logs", response_model=list[StatusLogResponse])
    def list_logs(
        limit: int = 300,
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[StatusLogResponse]:
        rows = api.logs.list_status_logs(limit=limit, dtype=device_type, device_id=device_id)
        return [StatusLogResponse(**row) for row in rows]


def _register_network_tools_routes(app: FastAPI, get_services, require_session, require_monitoring_module) -> None:
    def _resolve_scan_bounds(scanner: NetworkScanService, payload: NetworkScanRequest) -> tuple[str, str]:
        mode = str(payload.mode or "vlan").strip().lower()
        if mode == "vlan":
            return scanner.vlan_to_range(int(payload.vlan))
        start_ip = str(payload.start_ip or "").strip()
        end_ip = str(payload.end_ip or "").strip()
        scanner.normalize_range(start_ip, end_ip)
        return start_ip, end_ip

    def _scan_host_count(start_ip: str, end_ip: str) -> int:
        start = ipaddress.ip_address(str(start_ip).strip())
        end = ipaddress.ip_address(str(end_ip).strip())
        if not isinstance(start, ipaddress.IPv4Address) or not isinstance(end, ipaddress.IPv4Address):
            raise ValueError("Plage IPv4 uniquement.")
        if int(start) > int(end):
            raise ValueError("Plage invalide: debut > fin.")
        return int(end) - int(start) + 1

    def _assert_scan_span_within_limit(start_ip: str, end_ip: str) -> None:
        total_hosts = _scan_host_count(start_ip, end_ip)
        if total_hosts <= _MAX_NETWORK_SCAN_HOSTS:
            return
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Plage trop large ({total_hosts} IP). "
                f"Maximum autorise: {_MAX_NETWORK_SCAN_HOSTS} IP."
            ),
        )

    def _tool_stream_response(*, runner: Callable[[Callable[[str], None], threading.Event], bool]):
        async def stream_generator():
            queue: Queue[dict] = Queue()
            stop_event = threading.Event()

            def _emit(line: str) -> None:
                queue.put({"type": "line", "line": str(line or "")})

            def _worker() -> None:
                ok = False
                try:
                    ok = bool(runner(_emit, stop_event))
                except Exception as exc:
                    _emit(f"Erreur execution commande: {exc}")
                    ok = False
                finally:
                    queue.put({"type": "done", "ok": ok})

            thread = threading.Thread(target=_worker, daemon=True, name="NetworkToolStream")
            thread.start()
            try:
                while True:
                    try:
                        item = queue.get(timeout=0.25)
                    except Empty:
                        if not thread.is_alive():
                            break
                        await asyncio.sleep(0.05)
                        continue
                    yield f"{json.dumps(item, ensure_ascii=False)}\n"
                    if str(item.get("type", "")) == "done":
                        break
            finally:
                stop_event.set()

        return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

    @app.post("/network-tools/ping", response_model=NetworkToolResponse)
    def run_ping_tool(
        payload: NetworkToolPingRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> NetworkToolResponse:
        ok, output = api.network_tools.ping(str(payload.ip or "").strip())
        return NetworkToolResponse(ok=bool(ok), output=str(output or ""))

    @app.post("/network-tools/ping/stream")
    def run_ping_tool_stream(
        payload: NetworkToolPingRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ):
        ip = str(payload.ip or "").strip()
        return _tool_stream_response(
            runner=lambda on_line, stop_event: api.network_tools.stream_ping(
                ip,
                on_line,
                continuous=True,
                stop_event=stop_event,
            )
        )

    @app.post("/network-tools/port-check", response_model=NetworkToolResponse)
    def run_port_check_tool(
        payload: NetworkToolPortCheckRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> NetworkToolResponse:
        ok, output = api.network_tools.port_check(
            str(payload.ip or "").strip(),
            int(payload.port),
            timeout=float(payload.timeout_seconds),
        )
        return NetworkToolResponse(ok=bool(ok), output=str(output or ""))

    @app.post("/network-tools/traceroute", response_model=NetworkToolResponse)
    def run_traceroute_tool(
        payload: NetworkToolTracerouteRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> NetworkToolResponse:
        ok, output = api.network_tools.traceroute(str(payload.ip or "").strip())
        return NetworkToolResponse(ok=bool(ok), output=str(output or ""))

    @app.post("/network-tools/traceroute/stream")
    def run_traceroute_tool_stream(
        payload: NetworkToolTracerouteRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ):
        ip = str(payload.ip or "").strip()
        return _tool_stream_response(
            runner=lambda on_line, _stop_event: api.network_tools.stream_traceroute(ip, on_line)
        )

    @app.post("/network-tools/dns-lookup", response_model=NetworkToolResponse)
    def run_dns_lookup_tool(
        payload: NetworkToolDnsLookupRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> NetworkToolResponse:
        ok, output = api.network_tools.dns_lookup(str(payload.target or "").strip())
        return NetworkToolResponse(ok=bool(ok), output=str(output or ""))

    @app.post("/network-tools/dns-lookup/stream")
    def run_dns_lookup_tool_stream(
        payload: NetworkToolDnsLookupRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ):
        target = str(payload.target or "").strip()
        return _tool_stream_response(
            runner=lambda on_line, _stop_event: api.network_tools.stream_dns_lookup(target, on_line)
        )

    @app.post("/network-tools/http-check", response_model=NetworkToolResponse)
    def run_http_check_tool(
        payload: NetworkToolHttpCheckRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> NetworkToolResponse:
        ok, output = api.network_tools.http_check(str(payload.url or "").strip())
        return NetworkToolResponse(ok=bool(ok), output=str(output or ""))

    @app.post("/network-tools/snmp-check", response_model=NetworkToolResponse)
    def run_snmp_check_tool(
        payload: NetworkToolSnmpCheckRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> NetworkToolResponse:
        ok, output = api.network_tools.snmp_check(
            str(payload.ip or "").strip(),
            str(payload.community or "").strip(),
            str(payload.oid or "").strip(),
        )
        return NetworkToolResponse(ok=bool(ok), output=str(output or ""))

    @app.post("/network-scan", response_model=list[NetworkScanRowResponse])
    def run_network_scan(
        payload: NetworkScanRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[NetworkScanRowResponse]:
        scanner = NetworkScanService()
        try:
            start_ip, end_ip = _resolve_scan_bounds(scanner, payload)
            _assert_scan_span_within_limit(start_ip, end_ip)
            rows = scanner.scan_range(
                start_ip=start_ip,
                end_ip=end_ip,
                allow_vendor_network=bool(payload.allow_vendor_online),
                timeout_ms=int(payload.timeout_ms),
                max_workers=int(payload.max_workers),
                max_hosts=_MAX_NETWORK_SCAN_HOSTS,
            )
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        rows_by_ip: dict[str, dict] = {}
        for row in rows:
            ip = str((row or {}).get("ip", "")).strip()
            if not ip:
                continue
            rows_by_ip[ip] = {
                "ip": ip,
                "hostname": str((row or {}).get("hostname", "") or ""),
                "vendor": str((row or {}).get("vendor", "") or ""),
                "mac": str((row or {}).get("mac", "") or ""),
                "status": str((row or {}).get("status", "") or ""),
            }
        return [NetworkScanRowResponse(**row) for row in rows_by_ip.values()]

    @app.post("/network-scan/stream")
    def run_network_scan_stream(
        payload: NetworkScanRequest,
        _api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ):
        scanner = NetworkScanService()
        try:
            start_ip, end_ip = _resolve_scan_bounds(scanner, payload)
            _assert_scan_span_within_limit(start_ip, end_ip)
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        def _stream_response():
            queue: Queue[dict] = Queue()
            stop_event = threading.Event()

            def _emit(item: dict) -> None:
                queue.put(dict(item or {}))

            def _progress(done: int, total: int) -> None:
                _emit(
                    {
                        "type": "progress",
                        "done": max(0, int(done)),
                        "total": max(1, int(total)),
                    }
                )

            def _report(row: dict) -> None:
                ip = str((row or {}).get("ip", "")).strip()
                if not ip:
                    return
                _emit(
                    {
                        "type": "row",
                        "row": {
                            "ip": ip,
                            "hostname": str((row or {}).get("hostname", "") or ""),
                            "vendor": str((row or {}).get("vendor", "") or ""),
                            "mac": str((row or {}).get("mac", "") or ""),
                            "status": str((row or {}).get("status", "") or ""),
                        },
                    }
                )

            def _worker() -> None:
                ok = True
                message = ""
                try:
                    scanner.scan_range(
                        start_ip=start_ip,
                        end_ip=end_ip,
                        allow_vendor_network=bool(payload.allow_vendor_online),
                        timeout_ms=int(payload.timeout_ms),
                        max_workers=int(payload.max_workers),
                        max_hosts=_MAX_NETWORK_SCAN_HOSTS,
                        stop_event=stop_event,
                        progress_cb=_progress,
                        report_cb=_report,
                    )
                except Exception as exc:
                    ok = False
                    message = str(exc)
                finally:
                    _emit({"type": "done", "ok": ok, "message": message})

            thread = threading.Thread(target=_worker, daemon=True, name="NetworkScanStream")
            thread.start()

            async def _iter():
                try:
                    while True:
                        try:
                            item = queue.get(timeout=0.25)
                        except Empty:
                            if not thread.is_alive():
                                break
                            await asyncio.sleep(0.05)
                            continue
                        yield f"{json.dumps(item, ensure_ascii=False)}\n"
                        if str(item.get("type", "")) == "done":
                            break
                finally:
                    stop_event.set()

            return StreamingResponse(_iter(), media_type="application/x-ndjson")

        return _stream_response()


def _register_monitoring_routes(app: FastAPI, get_services, require_session, require_websocket_session, require_monitoring_module) -> None:
    @app.get("/monitoring/summary", response_model=MonitoringSummaryResponse)
    def get_monitoring_summary(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MonitoringSummaryResponse:
        snapshot = _build_monitoring_snapshot(api.model, api.monitoring_runtime)
        return snapshot["summary"]

    @app.get("/monitoring/snapshot", response_model=MonitoringSnapshotResponse)
    def get_monitoring_snapshot(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MonitoringSnapshotResponse:
        snapshot = _build_monitoring_snapshot(api.model, api.monitoring_runtime)
        return MonitoringSnapshotResponse(**snapshot)

    @app.get("/monitoring/capabilities", response_model=MonitoringCapabilitiesResponse)
    def get_monitoring_capabilities(
        _api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MonitoringCapabilitiesResponse:
        websocket_supported = _websocket_backend_supported()
        return MonitoringCapabilitiesResponse(
            websocket_supported=websocket_supported,
            recommended_transport="websocket" if websocket_supported else "polling",
        )

    @app.websocket("/monitoring/ws")
    async def monitoring_websocket(
        websocket: WebSocket,
        token: str = Query(default=""),
        interval_ms: int = Query(default=1000, ge=250, le=10000),
    ) -> None:
        api = get_services()
        if require_websocket_session(token, api) is None:
            await websocket.close(code=4401, reason="Session invalide ou expiree.")
            return

        await websocket.accept()
        interval_seconds = max(0.25, float(interval_ms) / 1000.0)
        last_payload = ""
        version = api.monitoring_runtime.state_version()

        try:
            snapshot = _build_monitoring_snapshot(api.model, api.monitoring_runtime)
            payload = {
                "event": "monitoring.snapshot",
                "data": MonitoringSnapshotResponse(**snapshot).model_dump(),
            }
            await websocket.send_json(payload)
            last_payload = json.dumps(payload, sort_keys=True, ensure_ascii=True)
            while True:
                version = await asyncio.to_thread(
                    api.monitoring_runtime.wait_for_change,
                    version,
                    interval_seconds,
                )
                snapshot = _build_monitoring_snapshot(api.model, api.monitoring_runtime)
                payload = {
                    "event": "monitoring.snapshot",
                    "data": MonitoringSnapshotResponse(**snapshot).model_dump(),
                }
                encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True)
                if encoded != last_payload:
                    await websocket.send_json(payload)
                    last_payload = encoded
                await asyncio.sleep(interval_seconds)
        except WebSocketDisconnect:
            return

    @app.post("/monitoring/start/{type_code}", response_model=MessageResponse)
    def start_monitoring_type(
        type_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        if not api.monitoring_runtime.start_monitoring(type_code):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type de monitoring introuvable.")
        return MessageResponse(message=f"Monitoring demarre pour {type_code}.")

    @app.post("/monitoring/stop/{type_code}", response_model=MessageResponse)
    def stop_monitoring_type(
        type_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        if not api.monitoring_runtime.stop_monitoring(type_code):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type de monitoring introuvable.")
        return MessageResponse(message=f"Monitoring arrete pour {type_code}.")

    @app.post("/monitoring/start-all", response_model=MessageResponse)
    def start_monitoring_all(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        started = api.monitoring_runtime.start_all()
        return MessageResponse(message=f"Monitoring demarre pour : {', '.join(started)}")

    @app.post("/monitoring/stop-all", response_model=MessageResponse)
    def stop_monitoring_all(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        stopped = api.monitoring_runtime.stop_all()
        return MessageResponse(message=f"Monitoring arrete pour : {', '.join(stopped)}")


def _register_ui_routes(app: FastAPI, get_services, require_session, require_websocket_session) -> None:
    @app.get("/ui/config", response_model=UiConfigResponse)
    def get_ui_config(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> UiConfigResponse:
        return _build_ui_config_response(api.settings_service.get())

    @app.get("/ui/auth-config", response_model=UiConfigResponse)
    def get_auth_ui_config(api: ApiServices = Depends(get_services)) -> UiConfigResponse:
        settings = api.settings_service.get()
        ui_config = _build_ui_config_response(settings)
        if ui_config.watermark_enabled:
            ui_config = ui_config.model_copy(update={"watermark_url": "/ui/auth-watermark-image"})
        return ui_config

    @app.get("/ui/auth-watermark-image", include_in_schema=False)
    def get_auth_ui_watermark_image(api: ApiServices = Depends(get_services)) -> FileResponse:
        return _resolve_watermark_response(api.settings_service.get())

    @app.get("/ui/watermark-image", include_in_schema=False)
    def get_ui_watermark_image(
        token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
    ) -> FileResponse:
        if require_websocket_session(token, api) is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expiree.")
        return _resolve_watermark_response(api.settings_service.get())

    @app.get("/ui/https-root-certificate/download")
    def download_https_root_certificate(
        _session=Depends(require_session),
    ) -> FileResponse:
        target = Path(tempfile.gettempdir()) / f"nmp_https_root_{uuid.uuid4().hex}.crt"
        try:
            exported = Path(CaddyManager().export_root_certificate(target))
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Export certificat impossible (droits insuffisants): {exc}",
            ) from exc
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certificat racine introuvable: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Export certificat impossible: {exc}",
            ) from exc
        return FileResponse(
            path=exported,
            filename="monitoring-mvl-root.crt",
            media_type="application/x-x509-ca-cert",
            background=BackgroundTask(lambda p=exported: p.unlink(missing_ok=True)),
        )


def _register_config_routes(app: FastAPI, get_services, require_session, require_monitoring_module) -> None:
    def _type_code_from_label(api: ApiServices, type_label: str) -> str:
        label = str(type_label or "").strip().lower()
        for code, meta in api.model.type_definitions.items():
            if str(meta.get("label", code) or code).strip().lower() == label:
                return str(code or "").strip().lower()
        return label

    def _config_storage_state(api: ApiServices) -> ConfigStorageStateResponse:
        settings = api.settings_service.get()
        mode = str(getattr(settings, "config_storage_mode", "local") or "local").strip().lower()
        has_password = bool(str(getattr(settings, "config_smb_password", "") or "").strip())
        local_storage_path = str(api.device_config_files.local_storage_root_dir())
        if mode != "smb3":
            return ConfigStorageStateResponse(
                mode="local",
                can_open_backup_folder=False,
                has_smb_password=False,
                local_storage_path=local_storage_path,
                backup_path="",
                message="Mode local actif: fichiers conserves sur le serveur.",
            )
        dynamic_mounts = api.storage_targets.describe_remote_mounts(include_legacy_monitoring=False)
        monitoring_mounts = [
            mount for mount in dynamic_mounts
            if str(mount.get("service_code") or "").strip() == "monitoring.device_config_files"
        ]
        active_monitoring_mount = next(
            (
                mount for mount in monitoring_mounts
                if (
                    bool(mount.get("automount_active"))
                    or bool(mount.get("mounted"))
                    or bool(mount.get("accessible"))
                )
            ),
            None,
        )
        if active_monitoring_mount is not None:
            backup_path = str(
                active_monitoring_mount.get("target_path")
                or active_monitoring_mount.get("mount_path")
                or ""
            )
            return ConfigStorageStateResponse(
                mode="smb3",
                can_open_backup_folder=True,
                has_smb_password=True,
                local_storage_path=local_storage_path,
                backup_path=backup_path,
                message=str(active_monitoring_mount.get("message") or "Cible de stockage monitoring active."),
            )
        failed_monitoring_mount = next(
            (mount for mount in monitoring_mounts if str(mount.get("last_error") or "").strip()),
            None,
        )
        if failed_monitoring_mount is not None:
            return ConfigStorageStateResponse(
                mode="smb3",
                can_open_backup_folder=False,
                has_smb_password=True,
                local_storage_path=local_storage_path,
                backup_path=str(
                    failed_monitoring_mount.get("target_path")
                    or failed_monitoring_mount.get("mount_path")
                    or ""
                ),
                message=str(
                    failed_monitoring_mount.get("last_error")
                    or failed_monitoring_mount.get("message")
                    or "Cible de stockage monitoring indisponible."
                ),
            )
        backup_path = str(api.config_storage.backup_root_dir())
        unc = str(getattr(settings, "config_smb_unc_path", "") or "").strip()
        user = str(getattr(settings, "config_smb_username", "") or "").strip()
        credentials_required = os.name == "nt"
        if not unc or (credentials_required and not (user and has_password)):
            return ConfigStorageStateResponse(
                mode=mode,
                can_open_backup_folder=False,
                has_smb_password=has_password,
                local_storage_path=local_storage_path,
                backup_path=backup_path,
                message=(
                    "Configuration SMB3 incomplete: chemin, utilisateur et mot de passe requis."
                    if credentials_required
                    else "Chemin distant manquant."
                ),
            )
        ok, info = api.config_storage.ensure_backup_connection()
        return ConfigStorageStateResponse(
            mode=mode,
            can_open_backup_folder=bool(ok),
            has_smb_password=has_password,
            local_storage_path=local_storage_path,
            backup_path=backup_path,
            message=str(info or ""),
        )

    def _monitoring_backup_root(api: ApiServices, storage_state: ConfigStorageStateResponse) -> Path:
        dynamic_path = str(getattr(storage_state, "backup_path", "") or "").strip()
        if dynamic_path and str(getattr(storage_state, "mode", "") or "").strip().lower() == "smb3":
            return Path(dynamic_path)
        return api.config_storage.backup_root_dir()

    @app.get("/config-storage/state", response_model=ConfigStorageStateResponse)
    def get_config_storage_state(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> ConfigStorageStateResponse:
        return _config_storage_state(api)

    @app.post("/config-storage/open-local-folder", response_model=MessageResponse)
    def open_local_config_folder(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        root = api.device_config_files.local_storage_root_dir()
        root.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            return MessageResponse(message=f"Dossier local serveur: {root}")
        try:
            open_path_with_default_app(root)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ouverture dossier local impossible: {exc}") from exc
        return MessageResponse(message=f"Dossier de configuration ouvert: {root}")

    @app.post("/config-storage/open-backup-folder", response_model=MessageResponse)
    def open_backup_config_folder(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        storage_state = _config_storage_state(api)
        if not storage_state.can_open_backup_folder:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=storage_state.message or "Sauvegarde distante indisponible.")
        root = _monitoring_backup_root(api, storage_state)
        if str(storage_state.mode).lower() != "smb3":
            root.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            return MessageResponse(message=f"Dossier de sauvegarde serveur: {root}")
        try:
            open_path_with_default_app(root)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ouverture dossier de sauvegarde impossible: {exc}") from exc
        return MessageResponse(message=f"Dossier de sauvegarde ouvert: {root}")

    @app.post("/config-storage/sync-now", response_model=MessageResponse)
    def run_config_sync_now(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        storage_state = _config_storage_state(api)
        if not storage_state.can_open_backup_folder:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=storage_state.message or "Sauvegarde distante indisponible.")
        backup_root = Path(storage_state.backup_path) if storage_state.backup_path else None
        stats = api.device_config_files.sync_local_versions_to_backup(backup_root=backup_root)
        return MessageResponse(
            message=(
                "Sauvegarde terminee. "
                f"Versions locales analysees: {int(stats.scanned)} | "
                f"Fichiers sauvegardes: {int(stats.copied)}"
            )
        )

    @app.post("/config-storage/test-connection", response_model=ConfigStorageStateResponse)
    def test_config_storage_connection(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> ConfigStorageStateResponse:
        return _config_storage_state(api)

    def _config_file_library_response(api: ApiServices, *, limit: int) -> list[ConfigFileResponse]:
        return [
            ConfigFileResponse(
                id=item.id,
                name=item.name,
                path=item.path,
                modified_at=item.modified_at,
                detail=item.detail,
                size_bytes=item.size_bytes,
                sha256=item.sha256,
                sync_status=item.sync_status,
                sync_error=item.sync_error,
                device_type=item.device_type,
                device_type_label=item.device_type_label,
                device_name=item.device_name,
                device_ip=item.device_ip,
            )
            for item in api.device_config_files.list_all_config_files(limit=limit)
        ]

    @app.get("/config-storage/files", response_model=list[ConfigFileResponse])
    def list_config_storage_files(
        limit: int = Query(default=500, ge=1, le=2000),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[ConfigFileResponse]:
        return _config_file_library_response(api, limit=limit)

    @app.get("/storage/files", response_model=list[ConfigFileResponse])
    def list_storage_files(
        limit: int = Query(default=500, ge=1, le=2000),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> list[ConfigFileResponse]:
        return _config_file_library_response(api, limit=limit)

    @app.get("/config-files", response_model=list[ConfigFileResponse])
    def list_config_files(
        device_type_label: str,
        device_name: str,
        device_type: str = "",
        device_id: str = "",
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[ConfigFileResponse]:
        dtype = str(device_type or "").strip().lower() or _type_code_from_label(api, device_type_label)
        return [
            ConfigFileResponse(
                id=item.id,
                name=item.name,
                path=item.path,
                modified_at=item.modified_at,
                detail=item.detail,
                size_bytes=item.size_bytes,
                sha256=item.sha256,
                sync_status=item.sync_status,
                sync_error=item.sync_error,
                device_type=item.device_type,
                device_type_label=item.device_type_label,
                device_name=item.device_name,
                device_ip=item.device_ip,
            )
            for item in api.device_config_files.list_config_files(
                device_type=dtype,
                device_id=str(device_id or "").strip(),
                device_name=str(device_name or "").strip(),
            )
        ]

    @app.get("/config-files/library", response_model=list[ConfigFileResponse])
    def list_config_file_library(
        limit: int = Query(default=500, ge=1, le=2000),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[ConfigFileResponse]:
        return _config_file_library_response(api, limit=limit)

    def _download_config_file_response(api: ApiServices, file_id: str) -> FileResponse:
        item = api.device_config_files.get_config_file(str(file_id or "").strip())
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable.")
        source = Path(item.path)
        if not source.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier local introuvable.")
        return FileResponse(path=source, filename=source.name, media_type="application/octet-stream")

    @app.get("/config-files/{file_id}/download")
    def download_config_file_by_id(
        file_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> FileResponse:
        return _download_config_file_response(api, file_id)

    @app.get("/storage/files/{file_id}/download")
    def download_storage_file_by_id(
        file_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> FileResponse:
        return _download_config_file_response(api, file_id)

    @app.delete("/config-files/{file_id}", response_model=MessageResponse)
    def delete_config_file_by_id(
        file_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        deleted = api.device_config_files.delete_config_file(str(file_id or "").strip(), delete_physical_file=True)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable ou non supprimable.")
        return MessageResponse(message="Fichier de configuration supprime.")

    @app.delete("/storage/files/{file_id}", response_model=MessageResponse)
    def delete_storage_file_by_id(
        file_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> MessageResponse:
        deleted = api.device_config_files.delete_config_file(str(file_id or "").strip(), delete_physical_file=True)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable ou non supprimable.")
        return MessageResponse(message="Fichier de configuration supprime.")

    def _storage_target_response(target) -> StorageTargetResponse:
        return StorageTargetResponse(
            id=target.id,
            label=target.label,
            service_code=target.service_code,
            service_label=target.service_label,
            kind=target.kind,
            remote_path=target.remote_path,
            username=target.username,
            local_mount_path=target.local_mount_path,
            auto_mount_enabled=target.auto_mount_enabled,
            status=target.status,
            last_error=target.last_error,
            last_checked_at=target.last_checked_at,
            created_at=target.created_at,
            updated_at=target.updated_at,
        )

    @app.get("/storage/targets", response_model=list[StorageTargetResponse])
    def list_storage_targets(
        service_code: str = "",
        limit: int = Query(default=500, ge=1, le=2000),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> list[StorageTargetResponse]:
        return [
            _storage_target_response(target)
            for target in api.storage_targets.list_targets(service_code=service_code, limit=limit)
        ]

    @app.post("/storage/targets", response_model=StorageTargetResponse)
    def upsert_storage_target(
        payload: StorageTargetUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> StorageTargetResponse:
        try:
            target = api.storage_targets.upsert_target(
                target_id=payload.id,
                label=payload.label,
                service_code=payload.service_code,
                service_label=payload.service_label,
                kind=payload.kind,
                remote_path=payload.remote_path,
                username=payload.username,
                password=payload.password,
                local_mount_path=payload.local_mount_path,
                auto_mount_enabled=payload.auto_mount_enabled,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return _storage_target_response(target)

    @app.post("/storage/targets/{target_id}/test", response_model=RemoteStorageMountResponse)
    def test_storage_target(
        target_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> RemoteStorageMountResponse:
        try:
            return RemoteStorageMountResponse(**api.storage_targets.test_target(target_id))
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.delete("/storage/targets/{target_id}", response_model=MessageResponse)
    def delete_storage_target(
        target_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> MessageResponse:
        deleted = api.storage_targets.delete_target(target_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cible de stockage introuvable.")
        return MessageResponse(message="Cible de stockage supprimee.")

    @app.get("/storage/remote-mounts", response_model=list[RemoteStorageMountResponse])
    def list_storage_remote_mounts(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> list[RemoteStorageMountResponse]:
        return [
            RemoteStorageMountResponse(**row)
            for row in api.storage_targets.describe_remote_mounts(include_legacy_monitoring=False)
        ]

    def _storage_target_explorer_path(target) -> Path:
        mount_path = Path(str(target.local_mount_path or "").strip())
        remote_path = str(target.remote_path or "").strip()
        if os.name == "nt":
            return mount_path
        normalized_remote = remote_path
        if normalized_remote.startswith("//"):
            parts = [part for part in normalized_remote.split("/") if part]
        else:
            parts = [part for part in normalized_remote.split("\\") if part]
        if len(parts) > 2:
            return mount_path.joinpath(*parts[2:])
        return mount_path

    def _storage_explorer_dir_accessible(path: Path) -> bool:
        try:
            return path.is_dir() and os.access(path, os.R_OK | os.X_OK)
        except OSError:
            return False

    def _storage_explorer_root_rows(api: ApiServices) -> list[dict[str, object]]:
        local_path = api.device_config_files.local_storage_root_dir()
        try:
            local_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        roots: list[dict[str, object]] = [
            {
                "id": "local:linked_files",
                "label": "Stockage local ITops",
                "service_code": "platform.storage",
                "service_label": "Stockage ITops",
                "kind": "local",
                "path": str(local_path),
                "accessible": _storage_explorer_dir_accessible(local_path),
            }
        ]
        for target in api.storage_targets.list_targets(limit=2000):
            target_path = _storage_target_explorer_path(target)
            roots.append(
                {
                    "id": f"target:{target.id}",
                    "label": target.label,
                    "service_code": target.service_code,
                    "service_label": target.service_label,
                    "kind": target.kind,
                    "path": str(target_path),
                    "accessible": _storage_explorer_dir_accessible(target_path),
                }
            )
        return roots

    def _storage_explorer_root(api: ApiServices, root_id: str) -> dict[str, object]:
        normalized_id = str(root_id or "").strip()
        for row in _storage_explorer_root_rows(api):
            if str(row.get("id") or "").strip() == normalized_id:
                return row
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Racine de stockage introuvable.")

    def _safe_storage_explorer_path(api: ApiServices, *, root_id: str, relative_path: str = "") -> tuple[dict[str, object], Path, str]:
        root = _storage_explorer_root(api, root_id)
        root_path = Path(str(root.get("path") or "")).expanduser().resolve()
        raw_relative = str(relative_path or "").replace("\\", "/").strip()
        raw_parts = [part for part in raw_relative.split("/") if part]
        if any(part in {".", ".."} for part in raw_parts):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chemin relatif invalide.")
        parts = raw_parts
        requested = root_path.joinpath(*parts).resolve()
        try:
            requested.relative_to(root_path)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chemin hors racine interdit.") from exc
        normalized_relative = "/".join(requested.relative_to(root_path).parts)
        return root, requested, normalized_relative

    def _storage_explorer_item_response(path: Path, root_path: Path) -> StorageExplorerItemResponse:
        try:
            stat = path.stat()
            is_dir = path.is_dir()
            relative = "/".join(path.relative_to(root_path).parts)
            return StorageExplorerItemResponse(
                name=path.name,
                path=relative,
                kind="folder" if is_dir else "file",
                size_bytes=0 if is_dir else int(stat.st_size),
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Acces refuse: {path}") from exc
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lecture impossible: {exc}") from exc

    @app.get("/storage/explorer/roots", response_model=list[StorageExplorerRootResponse])
    def list_storage_explorer_roots(
        service_code: str = "",
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> list[StorageExplorerRootResponse]:
        normalized_service = str(service_code or "").strip()
        roots = _storage_explorer_root_rows(api)
        if normalized_service:
            roots = [
                row for row in roots
                if str(row.get("service_code") or "").strip() in {normalized_service, "platform.storage"}
            ]
        return [StorageExplorerRootResponse(**row) for row in roots]

    @app.get("/storage/explorer/list", response_model=StorageExplorerListResponse)
    def list_storage_explorer_items(
        root_id: str,
        path: str = "",
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> StorageExplorerListResponse:
        root, folder, relative = _safe_storage_explorer_path(api, root_id=root_id, relative_path=path)
        if str(root.get("kind") or "").strip().lower() == "local" and not relative:
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except PermissionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Droits insuffisants sur le stockage local: {folder}",
                ) from exc
            except OSError as exc:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation du dossier local impossible: {exc}") from exc
        try:
            if not folder.is_dir():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
            children = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except HTTPException:
            raise
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Acces refuse au dossier: {folder}") from exc
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lecture du dossier impossible: {exc}") from exc
        root_path = Path(str(root.get("path") or "")).expanduser().resolve()
        items = [
            _storage_explorer_item_response(child, root_path)
            for child in children
            if not child.name.startswith(".")
        ]
        parent_path = ""
        if relative:
            parent_path = "/".join(Path(relative).parent.parts)
            if parent_path == ".":
                parent_path = ""
        return StorageExplorerListResponse(
            root_id=str(root.get("id") or ""),
            root_label=str(root.get("label") or ""),
            path=relative,
            parent_path=parent_path,
            items=items,
        )

    @app.post("/storage/explorer/folders", response_model=MessageResponse)
    def create_storage_explorer_folder(
        payload: StorageExplorerFolderCreateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> MessageResponse:
        name = str(payload.name or "").strip()
        if not name or any(sep in name for sep in ("/", "\\")) or name in {".", ".."}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de dossier invalide.")
        _root, folder, _relative = _safe_storage_explorer_path(api, root_id=payload.root_id, relative_path=payload.path)
        if not folder.is_dir():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier parent introuvable.")
        _root, target, _target_relative = _safe_storage_explorer_path(
            api,
            root_id=payload.root_id,
            relative_path="/".join(part for part in [payload.path, name] if str(part or "").strip()),
        )
        try:
            target.mkdir(parents=False, exist_ok=False)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Droits insuffisants pour creer le dossier: {target}") from exc
        except FileExistsError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un dossier ou fichier existe deja avec ce nom.") from exc
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation du dossier impossible: {exc}") from exc
        return MessageResponse(message="Dossier cree.")

    @app.post("/storage/explorer/upload", response_model=MessageResponse)
    def upload_storage_explorer_file(
        payload: StorageExplorerUploadRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> MessageResponse:
        _root, folder, _relative = _safe_storage_explorer_path(api, root_id=payload.root_id, relative_path=payload.path)
        if not folder.is_dir():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier cible introuvable.")
        filename = Path(str(payload.filename or "upload.bin")).name.strip() or "upload.bin"
        if filename in {".", ".."}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de fichier invalide.")
        _root, target, _target_relative = _safe_storage_explorer_path(
            api,
            root_id=payload.root_id,
            relative_path="/".join(part for part in [payload.path, filename] if str(part or "").strip()),
        )
        try:
            target.write_bytes(_decode_base64_payload(content_base64=payload.content_base64))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Droits insuffisants pour ecrire le fichier: {target}") from exc
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ecriture du fichier impossible: {exc}") from exc
        return MessageResponse(message="Fichier envoye.")

    @app.get("/storage/explorer/download")
    def download_storage_explorer_file(
        root_id: str,
        path: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> FileResponse:
        _root, target, _relative = _safe_storage_explorer_path(api, root_id=root_id, relative_path=path)
        if not target.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable.")
        return FileResponse(path=target, filename=target.name, media_type="application/octet-stream")

    @app.delete("/storage/explorer/items", response_model=MessageResponse)
    def delete_storage_explorer_item(
        payload: StorageExplorerDeleteRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> MessageResponse:
        _root, target, relative = _safe_storage_explorer_path(api, root_id=payload.root_id, relative_path=payload.path)
        if not relative:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Suppression de racine interdite.")
        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element introuvable.")
        linked_files = (
            api.linked_files.list_files_under_stored_path(target)
            if target.is_dir()
            else [item for item in [api.linked_files.get_file_by_stored_path(target)] if item is not None]
        )
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Droits insuffisants pour supprimer: {target}") from exc
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Suppression impossible: {exc}") from exc
        if target.exists():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Suppression incomplete: {target}")
        for linked_file in linked_files:
            api.linked_files.delete_file(linked_file.id, delete_physical_file=False)
        return MessageResponse(message="Element supprime.")

    @app.get("/config-files/latest-download")
    def download_latest_config_file(
        device_type: str,
        device_name: str,
        device_ip: str,
        device_id: str = "",
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> FileResponse:
        dtype = str(device_type or "").strip().lower()
        if not dtype:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type de device manquant.")
        if not api.model.is_config_download_type(dtype):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce type ne gere pas les fichiers de configuration.")
        imported = api.device_config_files.latest_imported_config_file(
            device_type=dtype,
            device_id=str(device_id or "").strip(),
            device_name=str(device_name or "").strip(),
        )
        if imported and Path(imported.path).is_file():
            source = Path(imported.path)
            return FileResponse(path=source, filename=source.name, media_type="application/octet-stream")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun fichier de configuration assigne a ce device.")

    @app.post("/config-files/import", response_model=MessageResponse)
    def import_config_file(
        payload: ConfigFileImportRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        dtype = str(payload.device_type or "").strip().lower()
        dname = str(payload.device_name or "").strip()
        if not dtype or not dname:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type ou nom de device manquant.")
        if not api.model.is_config_download_type(dtype):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce type ne gere pas les fichiers de configuration.")
        type_label = str(api.model.type_definitions.get(dtype, {}).get("label", dtype))
        suffix = Path(str(payload.filename or "")).suffix or ".cfg"
        tmp_dir = Path(tempfile.gettempdir())
        tmp_path = tmp_dir / f"nmp_cfg_upload_{uuid.uuid4().hex}{suffix}"
        raw_bytes = _decode_base64_payload(content_base64=payload.content_base64)
        try:
            tmp_path.write_bytes(raw_bytes)
            created_at = api.config_storage.file_created_at(tmp_path)
            imported = api.device_config_files.import_config_file(
                device_type=dtype,
                device_type_label=type_label,
                device_id=str(payload.device_id or "").strip(),
                device_name=dname,
                device_ip=str(payload.device_ip or "").strip(),
                source_file=tmp_path,
                detail=str(payload.detail or "").strip(),
                created_by=str(getattr(_session, "subject", "") or ""),
                stamp_dt=created_at,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Import impossible: {exc}") from exc
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
        return MessageResponse(message=f"Version importee: {imported.path}")


def _register_admin_routes(app: FastAPI, get_services, require_session) -> None:
    def _normalize_single_role(role_codes: list[str]) -> list[str]:
        for item in role_codes or []:
            normalized = str(item or "").strip().lower()
            if normalized:
                return [normalized]
        return []

    def _subject_has_role(*, api: ApiServices, subject: str, role_code: str) -> bool:
        lister = getattr(api.logs, "list_auth_users", None)
        if not callable(lister):
            return False
        normalized_subject = str(subject or "").strip().lower()
        normalized_role = str(role_code or "").strip().lower()
        for row in lister():
            if str(row.get("subject") or "").strip().lower() != normalized_subject:
                continue
            roles = [str(code or "").strip().lower() for code in (row.get("role_codes") or [])]
            return normalized_role in roles
        return False

    def _subject_has_any_module(*, api: ApiServices, subject: str, module_codes: list[str]) -> bool:
        checker = getattr(api.logs, "subject_has_module", None)
        if not callable(checker):
            return False
        normalized_subject = str(subject or "").strip().lower()
        for code in module_codes:
            normalized_code = str(code or "").strip().lower()
            if not normalized_code:
                continue
            if bool(checker(subject=normalized_subject, module_code=normalized_code)):
                return True
        return False

    def require_role_manager_role(
        session=Depends(require_session),
        api: ApiServices = Depends(get_services),
    ):
        normalized_subject = str(getattr(session, "subject", "") or "").strip().lower()
        if normalized_subject == "sa":
            return session
        has_admin_role = _subject_has_role(api=api, subject=normalized_subject, role_code="admin")
        has_admin_module = _subject_has_any_module(api=api, subject=normalized_subject, module_codes=["admin"])
        if not (has_admin_role or has_admin_module):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul le role admin peut gerer les roles.")
        return session

    def require_user_manager_access(
        session=Depends(require_session),
        api: ApiServices = Depends(get_services),
    ):
        subject = str(session.subject or "").strip().lower()
        if _subject_has_role(api=api, subject=subject, role_code="admin"):
            return session
        if _subject_has_any_module(api=api, subject=subject, module_codes=["users_admin", "admin"]):
            return session
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse a la gestion des utilisateurs.")

    @app.get("/admin/database/backup")
    def download_database_backup(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> FileResponse:
        backup_path = _create_database_backup_file(api.logs)
        filename = f"itops-db-{_backup_timestamp()}.sql"
        return FileResponse(
            backup_path,
            media_type="application/sql",
            filename=filename,
            background=BackgroundTask(_safe_unlink, backup_path),
        )

    @app.post("/admin/database/import", response_model=MessageResponse)
    def import_database_backup(
        payload: DatabaseImportRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> MessageResponse:
        if not bool(payload.confirm_replace):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Confirmation obligatoire avant import de la base.",
            )
        raw_bytes = _decode_base64_payload(content_base64=payload.content_base64)
        _restore_database_backup(api.logs, raw_bytes=raw_bytes, filename=str(payload.filename or "backup.sql"))
        return MessageResponse(message="Base de donnees importee. Recharge l'application pour relire les donnees restaurees.")

    def _list_custom_services_or_501(api: ApiServices) -> list[dict]:
        lister = getattr(api.logs, "list_custom_services", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Catalogue services indisponible.")
        try:
            rows = lister()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lecture services impossible: {exc}") from exc
        return list(rows or [])

    def _list_shared_lists_or_501(api: ApiServices) -> list[dict]:
        lister = getattr(api.logs, "list_shared_lists", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Catalogue referentiels indisponible.")
        try:
            rows = lister()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lecture referentiels impossible: {exc}") from exc
        return list(rows or [])

    def _get_shared_list_or_404(api: ApiServices, list_code: str) -> dict:
        getter = getattr(api.logs, "get_shared_list", None)
        normalized = str(list_code or "").strip().lower()
        if callable(getter):
            row = getter(code=normalized)
            if row is not None:
                return row
        for row in _list_shared_lists_or_501(api):
            if str(row.get("code") or "").strip().lower() == normalized:
                return row
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referentiel introuvable.")

    def _resolve_service_field_options(api: ApiServices, fields: list[dict]) -> list[dict]:
        rows = [dict(item or {}) for item in list(fields or [])]
        list_items_loader = getattr(api.logs, "list_shared_list_items", None)
        if not callable(list_items_loader):
            return rows
        cache: dict[str, str] = {}
        for field in rows:
            kind = str(field.get("field_kind") or "").strip().lower()
            source_kind = str(field.get("list_source_kind") or "local").strip().lower()
            shared_list_code = str(field.get("shared_list_code") or "").strip().lower()
            if kind != "list" or source_kind != "shared" or not shared_list_code:
                continue
            if shared_list_code not in cache:
                try:
                    shared_rows = list_items_loader(list_code=shared_list_code)
                except Exception:
                    shared_rows = []
                labels = [
                    str(item.get("label") or "").strip()
                    for item in list(shared_rows or [])
                    if bool(item.get("is_active", True)) and str(item.get("label") or "").strip()
                ]
                cache[shared_list_code] = ",".join(labels)
            field["options"] = str(cache.get(shared_list_code) or "")
        return rows

    def _with_resolved_custom_service(api: ApiServices, row: dict) -> dict:
        payload = dict(row or {})
        payload["fields"] = _resolve_service_field_options(api, list(payload.get("fields") or []))
        try:
            raw_config = str(payload.get("treeview_config") or "")
            parsed_config = json.loads(raw_config) if raw_config else {}
            payload["tile_config"] = parsed_config.get("tile") if isinstance(parsed_config.get("tile"), dict) else {}
            payload["relationship_inheritance"] = parsed_config.get("relationship_inheritance") if isinstance(parsed_config.get("relationship_inheritance"), dict) else {}
        except Exception:
            payload["tile_config"] = {}
            payload["relationship_inheritance"] = {}
        return payload

    def _is_reserved_system_entity_code(api: ApiServices, code: str) -> bool:
        checker = getattr(api.logs, "is_reserved_system_entity_code", None)
        if callable(checker):
            return bool(checker(code))
        return str(code or "").strip().lower() in {
            "utilisateur",
            "utilisateurs",
            "user",
            "users",
            "agent",
            "agents",
            "service",
            "services",
            "ou",
            "ous",
            "organisation",
            "organisations",
            "organization",
            "organizations",
        }

    def _is_system_custom_service_code(api: ApiServices, code: str) -> bool:
        checker = getattr(api.logs, "is_system_custom_service_code", None)
        if callable(checker):
            return bool(checker(code))
        return str(code or "").strip().lower() in {"emails"}

    def _normalize_relation_entity_code(api: ApiServices, code: str) -> str:
        normalizer = getattr(api.logs, "normalize_relation_entity_code", None)
        if callable(normalizer):
            return str(normalizer(code) or "").strip().lower()
        aliases = {
            "utilisateur": "utilisateurs",
            "user": "utilisateurs",
            "users": "utilisateurs",
            "agent": "utilisateurs",
            "agents": "utilisateurs",
            "service": "services",
            "services": "services",
            "ou": "services",
            "ous": "services",
            "organisation": "services",
            "organisations": "services",
            "organization": "services",
            "organizations": "services",
        }
        normalized = str(code or "").strip().lower()
        return aliases.get(normalized, normalized)

    def _get_relation_entity_or_404(api: ApiServices, service_code: str) -> dict:
        normalized = _normalize_relation_entity_code(api, service_code)
        if _is_reserved_system_entity_code(api, normalized):
            labels = {"utilisateurs": "Agents", "services": "Services"}
            return {
                "code": normalized,
                "label": labels.get(normalized, normalized),
                "fields": [],
                "relation_kind": "system",
                "is_active": True,
            }
        return _get_custom_service_or_404(api, normalized)

    def _get_custom_service_or_404(api: ApiServices, service_code: str) -> dict:
        getter = getattr(api.logs, "get_custom_service", None)
        normalized = str(service_code or "").strip().lower()
        if callable(getter):
            row = getter(code=normalized)
            if row is not None:
                return _with_resolved_custom_service(api, row)
        for row in _list_custom_services_or_501(api):
            if str(row.get("code") or "").strip().lower() == normalized:
                return _with_resolved_custom_service(api, row)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable.")

    def _normalize_notification_due_at(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            return f"{raw} 09:00:00"
        candidate = raw.replace("T", " ")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Date de rappel notification invalide.",
            ) from exc
        return parsed.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    def _email_record_label(values: dict) -> str:
        address = str((values or {}).get("address") or "").strip()
        alias = str((values or {}).get("alias") or "").strip()
        return address or alias or "compte Email"

    def _sync_email_status_notification_task(
        api: ApiServices,
        *,
        service_code: str,
        record_id: str,
        values: dict,
        reminder_due_at: str = "",
    ) -> None:
        normalized_service = str(service_code or "").strip().lower()
        if normalized_service != "emails":
            return
        updater = getattr(api.logs, "upsert_notification_task", None)
        canceller = getattr(api.logs, "cancel_notification_tasks_for_source", None)
        status_value = str((values or {}).get("status") or "").strip()
        is_delete_request = status_value.lower() == "a supprimer"
        if not is_delete_request:
            if callable(canceller) and str(record_id or "").strip():
                canceller(
                    source_service_code="emails",
                    source_record_id=str(record_id or "").strip(),
                    trigger_field_key="status",
                    trigger_value="A supprimer",
                )
            return
        due_at = _normalize_notification_due_at(reminder_due_at)
        if not due_at:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Date de rappel requise pour passer un Email a supprimer.",
            )
        if not callable(updater):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Moteur de taches notification indisponible.")
        label = _email_record_label(values)
        updater(
            source_service_code="emails",
            source_record_id=str(record_id or "").strip(),
            trigger_field_key="status",
            trigger_value="A supprimer",
            title=f"Supprimer le compte Email {label}",
            message=f"Le compte Email {label} est marque A supprimer. Suppression prevue le {due_at[:10]}.",
            due_at=due_at,
        )

    def _normalize_custom_service_upsert_payload(api: ApiServices, payload: CustomServiceUpsertRequest, *, code_override: str = "") -> tuple[str, list[dict]]:
        normalized_code = normalize_service_code(code=(code_override or payload.code), label=payload.label)
        if not normalized_code:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Code service invalide.")
        try:
            normalized_fields = normalize_service_fields(list(payload.fields or []))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        normalized_fields = [
            field
            for field in normalized_fields
            if str(field.get("field_key") or "").strip().lower()
            not in {CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY, CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY}
        ]
        normalized_fields = [
            {
                **field,
                "sort_order": (index + 1) * 10,
            }
            for index, field in enumerate(normalized_fields)
        ]
        shared_codes = sorted(
            {
                str(field.get("shared_list_code") or "").strip().lower()
                for field in normalized_fields
                if str(field.get("field_kind") or "").strip().lower() == "list"
                and str(field.get("list_source_kind") or "local").strip().lower() == "shared"
                and str(field.get("shared_list_code") or "").strip()
            }
        )
        for shared_code in shared_codes:
            _get_shared_list_or_404(api, shared_code)
        return normalized_code, normalized_fields

    def _custom_service_system_definition_changed(existing: dict, payload: CustomServiceUpsertRequest, normalized_fields: list[dict]) -> bool:
        existing_fields = normalize_service_fields(list(existing.get("fields") or []))
        existing_fields = [
            field
            for field in existing_fields
            if str(field.get("field_key") or "").strip().lower()
            not in {CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY, CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY}
        ]
        existing_fields = [
            {
                **field,
                "sort_order": (index + 1) * 10,
            }
            for index, field in enumerate(existing_fields)
        ]
        return any(
            (
                str(payload.label or "").strip() != str(existing.get("label") or "").strip(),
                bool(payload.credentials_enabled) != bool(existing.get("credentials_enabled", False)),
                bool(payload.child_enabled) != bool(existing.get("child_enabled", False)),
                (str(payload.child_label or "").strip() or "Elements lies")
                != (str(existing.get("child_label") or "").strip() or "Elements lies"),
                int(payload.sort_order or 100) != int(existing.get("sort_order") or 100),
                normalized_fields != existing_fields,
            )
        )

    def _normalize_record_import_column_mappings(rows: list[dict] | None) -> list[dict[str, str]]:
        output: list[dict[str, str]] = []
        for row in list(rows or []):
            source_column = str((row or {}).get("source_column") or "").strip()
            target_field = str((row or {}).get("target_field") or "").strip() or "__auto__"
            custom_key = str((row or {}).get("custom_key") or "").strip()
            if not source_column:
                continue
            output.append({"source_column": source_column, "target_field": target_field, "custom_key": custom_key})
        return output

    def _with_record_import_created_fields(
        *,
        service: dict,
        headers: list[str],
        rows: list[list[str]],
        column_mappings: list[dict] | None,
    ) -> tuple[list[dict], list[dict[str, str]], list[dict]]:
        base_fields = normalize_service_fields(list(service.get("fields") or []))
        mappings = _normalize_record_import_column_mappings(column_mappings)
        create_sources = {
            str(row.get("source_column") or "").strip()
            for row in mappings
            if str(row.get("target_field") or "").strip() == "__create_field__"
        }
        if not create_sources:
            return base_fields, mappings, []
        create_mappings: list[dict[str, str]] = []
        custom_label_by_source: dict[str, str] = {}
        for header in list(headers or []):
            source = str(header or "").strip()
            selected = next((row for row in mappings if str(row.get("source_column") or "").strip() == source), {})
            if source not in create_sources:
                create_mappings.append({"source_column": source, "target_field": "__ignore__", "custom_key": ""})
                continue
            custom_label = str(selected.get("custom_key") or "").strip()
            custom_label_by_source[source] = custom_label
            create_mappings.append({"source_column": source, "target_field": "__create_field__", "custom_key": custom_label})
        inferred_fields, _detected_rows, _detected_columns = infer_service_fields_from_rows(
            labels=list(headers or []),
            rows=list(rows or []),
            column_mappings=create_mappings,
        )
        existing_keys = {
            str(field.get("field_key") or "").strip().lower()
            for field in base_fields
            if str(field.get("field_key") or "").strip()
        }
        next_sort = max([int(field.get("sort_order") or 0) for field in base_fields if isinstance(field, dict)] or [0])
        created_by_label: dict[str, dict] = {}
        created_fields: list[dict] = []
        for field in inferred_fields:
            row = dict(field or {})
            label = str(row.get("label") or "").strip()
            base_key = normalize_field_key(field_key=row.get("field_key"), label=label, index=len(base_fields) + len(created_fields))
            field_key = base_key
            suffix = 2
            while field_key.lower() in existing_keys:
                field_key = f"{base_key}_{suffix}"
                suffix += 1
            existing_keys.add(field_key.lower())
            next_sort += 10
            row["field_key"] = field_key
            row["sort_order"] = next_sort
            created_by_label[label] = row
            created_fields.append(row)
        created_by_source: dict[str, dict] = {}
        for source in create_sources:
            lookup_label = custom_label_by_source.get(source) or source
            created = created_by_label.get(lookup_label)
            if created:
                created_by_source[source] = created
        resolved_mappings: list[dict[str, str]] = []
        for row in mappings:
            source = str(row.get("source_column") or "").strip()
            if str(row.get("target_field") or "").strip() == "__create_field__":
                created = created_by_source.get(source)
                if created:
                    resolved_mappings.append({**row, "target_field": str(created.get("field_key") or "")})
                continue
            resolved_mappings.append(row)
        return [*base_fields, *created_fields], resolved_mappings, created_fields

    @app.get("/admin/modules", response_model=list[AdminModuleResponse])
    def list_admin_modules(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_user_manager_access),
    ) -> list[AdminModuleResponse]:
        lister = getattr(api.logs, "list_auth_modules", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Catalogue modules indisponible.")
        return [AdminModuleResponse(**row) for row in lister()]

    @app.put("/admin/modules/{module_code}/activation", response_model=AdminModuleResponse)
    def update_admin_module_activation(
        module_code: str,
        payload: AdminModuleActivationRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> AdminModuleResponse:
        setter = getattr(api.logs, "set_auth_module_active", None)
        if not callable(setter):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Catalogue modules indisponible.")
        normalized_code = str(module_code or "").strip().lower()
        if not normalized_code:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Code module invalide.")
        updated = setter(code=normalized_code, is_active=bool(payload.is_active))
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable.")
        return AdminModuleResponse(**updated)

    @app.get("/admin/roles", response_model=list[AdminRoleResponse])
    def list_admin_roles(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_user_manager_access),
    ) -> list[AdminRoleResponse]:
        lister = getattr(api.logs, "list_auth_roles", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des roles indisponible.")
        return [AdminRoleResponse(**_with_role_version_token(row)) for row in lister()]

    @app.post("/admin/roles", response_model=AdminRoleResponse)
    def create_admin_role(
        payload: AdminRoleUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> AdminRoleResponse:
        saver = getattr(api.logs, "save_auth_role", None)
        lister = getattr(api.logs, "list_auth_roles", None)
        if not callable(saver) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des roles indisponible.")
        saver(
            code=payload.code,
            label=payload.label,
            module_codes=list(payload.module_codes or []),
            is_system=bool(payload.is_system),
            sort_order=int(payload.sort_order or 0),
        )
        match = next((row for row in lister() if str(row.get("code")) == str(payload.code).strip().lower()), None)
        if not match:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Role non persiste.")
        return AdminRoleResponse(**_with_role_version_token(match))

    @app.put("/admin/roles/{role_code}", response_model=AdminRoleResponse)
    def update_admin_role(
        role_code: str,
        payload: AdminRoleUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> AdminRoleResponse:
        saver = getattr(api.logs, "save_auth_role", None)
        lister = getattr(api.logs, "list_auth_roles", None)
        if not callable(saver) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des roles indisponible.")
        existing = next((row for row in lister() if str(row.get("code")) == str(role_code).strip().lower()), None)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role introuvable.")
        _assert_version_token(
            expected=_role_version_token(existing),
            received=str(payload.version_token or ""),
            resource_label=f"Role {role_code}",
        )
        saver(
            code=role_code,
            label=payload.label,
            module_codes=list(payload.module_codes or []),
            is_system=bool(payload.is_system),
            sort_order=int(payload.sort_order or 0),
        )
        match = next((row for row in lister() if str(row.get("code")) == str(role_code).strip().lower()), None)
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role introuvable.")
        return AdminRoleResponse(**_with_role_version_token(match))

    @app.delete("/admin/roles/{role_code}", response_model=MessageResponse)
    def delete_admin_role(
        role_code: str,
        version_token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> MessageResponse:
        normalized = str(role_code or "").strip().lower()
        lister = getattr(api.logs, "list_auth_roles", None)
        deleter = getattr(api.logs, "delete_auth_role", None)
        if not callable(lister) or not callable(deleter):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des roles indisponible.")
        role = next((row for row in lister() if str(row.get("code")) == normalized), None)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role introuvable.")
        _assert_version_token(
            expected=_role_version_token(role),
            received=version_token,
            resource_label=f"Role {role_code}",
        )
        if bool(role.get("is_system")):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suppression d'un role systeme interdite.")
        deleted = int(deleter(code=normalized) or 0)
        if deleted <= 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role introuvable.")
        return MessageResponse(message="Role supprime.")

    @app.get("/admin/users", response_model=list[AdminUserResponse])
    def list_admin_users(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_user_manager_access),
    ) -> list[AdminUserResponse]:
        lister = getattr(api.logs, "list_auth_users", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des utilisateurs indisponible.")
        return [AdminUserResponse(**_with_user_version_token(row)) for row in lister()]

    @app.post("/admin/users", response_model=AdminUserResponse)
    def create_admin_user(
        payload: AdminUserCreateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_user_manager_access),
    ) -> AdminUserResponse:
        upsert_user = getattr(api.logs, "upsert_auth_user", None)
        set_roles = getattr(api.logs, "set_auth_user_roles", None)
        lister = getattr(api.logs, "list_auth_users", None)
        if not callable(upsert_user) or not callable(set_roles) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des utilisateurs indisponible.")
        role_codes = _normalize_single_role(list(payload.role_codes or []))
        if not role_codes:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Un role est requis.")
        try:
            upsert_user(
                subject=payload.subject,
                label=payload.label or payload.subject,
                password_hash=AuthService.hash_password(payload.password),
                must_change_password=bool(payload.must_change_password),
                is_active=bool(payload.is_active),
            )
            set_roles(subject=payload.subject, role_codes=role_codes)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        match = next((row for row in lister() if str(row.get("subject")) == str(payload.subject).strip().lower()), None)
        if not match:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Utilisateur non persiste.")
        return AdminUserResponse(**_with_user_version_token(match))

    @app.put("/admin/users/{subject}", response_model=AdminUserResponse)
    def update_admin_user(
        subject: str,
        payload: AdminUserUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_user_manager_access),
    ) -> AdminUserResponse:
        getter = getattr(api.logs, "get_auth_user", None)
        upsert_user = getattr(api.logs, "upsert_auth_user", None)
        set_password = getattr(api.logs, "set_auth_user_password", None)
        set_roles = getattr(api.logs, "set_auth_user_roles", None)
        lister = getattr(api.logs, "list_auth_users", None)
        if not callable(getter) or not callable(upsert_user) or not callable(set_password) or not callable(set_roles) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des utilisateurs indisponible.")
        existing = getter(subject=subject)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
        current_row = next((row for row in lister() if str(row.get("subject")) == str(subject).strip().lower()), None)
        if current_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
        _assert_version_token(
            expected=_user_version_token(current_row),
            received=str(payload.version_token or ""),
            resource_label=f"Utilisateur {subject}",
        )
        role_codes = _normalize_single_role(list(payload.role_codes or []))
        if not role_codes:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Un role est requis.")
        normalized_subject = str(subject or "").strip().lower()
        if normalized_subject == "sa" and role_codes != ["admin"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Le compte sa doit conserver le role admin.")
        try:
            upsert_user(
                subject=normalized_subject,
                label=payload.label or existing.get("label") or normalized_subject,
                password_hash=str(existing.get("password_hash") or ""),
                must_change_password=bool(payload.must_change_password),
                is_active=bool(payload.is_active),
            )
            new_password = str(payload.password or "").strip()
            if new_password:
                set_password(
                    subject=normalized_subject,
                    password_hash=AuthService.hash_password(new_password),
                    must_change_password=bool(payload.must_change_password),
                )
            set_roles(subject=normalized_subject, role_codes=role_codes)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        match = next((row for row in lister() if str(row.get("subject")) == normalized_subject), None)
        if not match:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Utilisateur non persiste.")
        return AdminUserResponse(**_with_user_version_token(match))

    @app.delete("/admin/users/{subject}", response_model=MessageResponse)
    def delete_admin_user(
        subject: str,
        version_token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_user_manager_access),
    ) -> MessageResponse:
        normalized = str(subject or "").strip().lower()
        if normalized in {"sa"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suppression du compte sa interdite.")
        lister = getattr(api.logs, "list_auth_users", None)
        deleter = getattr(api.logs, "delete_auth_user", None)
        if not callable(deleter) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des utilisateurs indisponible.")
        current_row = next((row for row in lister() if str(row.get("subject") or "").strip().lower() == normalized), None)
        if current_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
        _assert_version_token(
            expected=_user_version_token(current_row),
            received=version_token,
            resource_label=f"Utilisateur {subject}",
        )
        deleted = int(deleter(subject=normalized) or 0)
        if deleted <= 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
        return MessageResponse(message="Utilisateur supprime.")

    @app.get("/admin/shared-lists", response_model=list[SharedListResponse])
    def list_admin_shared_lists(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> list[SharedListResponse]:
        return [SharedListResponse(**_with_shared_list_version_token(row)) for row in _list_shared_lists_or_501(api)]

    @app.post("/admin/shared-lists", response_model=SharedListResponse)
    def create_admin_shared_list(
        payload: SharedListUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> SharedListResponse:
        saver = getattr(api.logs, "save_shared_list", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion referentiels indisponible.")
        normalized_code = normalize_service_code(code=payload.code, label=payload.label)
        try:
            row = saver(
                code=normalized_code,
                label=str(payload.label or "").strip(),
                is_system=bool(payload.is_system),
                sort_order=int(payload.sort_order or 100),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return SharedListResponse(**_with_shared_list_version_token(row))

    @app.put("/admin/shared-lists/{list_code}", response_model=SharedListResponse)
    def update_admin_shared_list(
        list_code: str,
        payload: SharedListUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> SharedListResponse:
        saver = getattr(api.logs, "save_shared_list", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion referentiels indisponible.")
        existing = _get_shared_list_or_404(api, list_code)
        _assert_version_token(
            expected=_shared_list_version_token(existing),
            received=str(payload.version_token or ""),
            resource_label=f"Referentiel {list_code}",
        )
        try:
            row = saver(
                code=str(list_code or "").strip().lower(),
                label=str(payload.label or "").strip(),
                is_system=bool(payload.is_system),
                sort_order=int(payload.sort_order or 100),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return SharedListResponse(**_with_shared_list_version_token(row))

    @app.delete("/admin/shared-lists/{list_code}", response_model=MessageResponse)
    def delete_admin_shared_list(
        list_code: str,
        version_token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> MessageResponse:
        deleter = getattr(api.logs, "delete_shared_list", None)
        if not callable(deleter):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion referentiels indisponible.")
        existing = _get_shared_list_or_404(api, list_code)
        _assert_version_token(
            expected=_shared_list_version_token(existing),
            received=version_token,
            resource_label=f"Referentiel {list_code}",
        )
        if bool(existing.get("is_system")):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suppression d'un referentiel systeme interdite.")
        deleted = int(deleter(code=str(list_code or "").strip().lower()) or 0)
        if deleted <= 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referentiel introuvable.")
        return MessageResponse(message="Referentiel supprime.")

    @app.get("/admin/shared-lists/{list_code}/items", response_model=list[SharedListItemResponse])
    def list_admin_shared_list_items(
        list_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> list[SharedListItemResponse]:
        lister = getattr(api.logs, "list_shared_list_items", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion referentiels indisponible.")
        shared_list = _get_shared_list_or_404(api, list_code)
        try:
            rows = lister(list_code=str(shared_list.get("code") or list_code))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lecture valeurs referentiel impossible: {exc}") from exc
        return [SharedListItemResponse(**_with_shared_list_item_version_token(row)) for row in list(rows or [])]

    @app.post("/admin/shared-lists/{list_code}/items", response_model=SharedListItemResponse)
    def create_admin_shared_list_item(
        list_code: str,
        payload: SharedListItemUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> SharedListItemResponse:
        saver = getattr(api.logs, "save_shared_list_item", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion referentiels indisponible.")
        shared_list = _get_shared_list_or_404(api, list_code)
        normalized_item_code = normalize_service_code(code=payload.code, label=payload.label)
        try:
            row = saver(
                list_code=str(shared_list.get("code") or list_code),
                code=normalized_item_code,
                label=str(payload.label or "").strip(),
                is_active=bool(payload.is_active),
                sort_order=int(payload.sort_order or 100),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return SharedListItemResponse(**_with_shared_list_item_version_token(row))

    @app.put("/admin/shared-lists/{list_code}/items/{item_code}", response_model=SharedListItemResponse)
    def update_admin_shared_list_item(
        list_code: str,
        item_code: str,
        payload: SharedListItemUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> SharedListItemResponse:
        saver = getattr(api.logs, "save_shared_list_item", None)
        lister = getattr(api.logs, "list_shared_list_items", None)
        if not callable(saver) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion referentiels indisponible.")
        shared_list = _get_shared_list_or_404(api, list_code)
        rows = list(lister(list_code=str(shared_list.get("code") or list_code)) or [])
        existing = next((row for row in rows if str(row.get("code") or "").strip().lower() == str(item_code or "").strip().lower()), None)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Valeur referentiel introuvable.")
        _assert_version_token(
            expected=_shared_list_item_version_token(existing),
            received=str(payload.version_token or ""),
            resource_label=f"Valeur {item_code}",
        )
        try:
            row = saver(
                list_code=str(shared_list.get("code") or list_code),
                code=str(item_code or "").strip().lower(),
                label=str(payload.label or "").strip(),
                is_active=bool(payload.is_active),
                sort_order=int(payload.sort_order or 100),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return SharedListItemResponse(**_with_shared_list_item_version_token(row))

    @app.delete("/admin/shared-lists/{list_code}/items/{item_code}", response_model=MessageResponse)
    def delete_admin_shared_list_item(
        list_code: str,
        item_code: str,
        version_token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> MessageResponse:
        deleter = getattr(api.logs, "delete_shared_list_item", None)
        lister = getattr(api.logs, "list_shared_list_items", None)
        if not callable(deleter) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion referentiels indisponible.")
        shared_list = _get_shared_list_or_404(api, list_code)
        rows = list(lister(list_code=str(shared_list.get("code") or list_code)) or [])
        existing = next((row for row in rows if str(row.get("code") or "").strip().lower() == str(item_code or "").strip().lower()), None)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Valeur referentiel introuvable.")
        _assert_version_token(
            expected=_shared_list_item_version_token(existing),
            received=version_token,
            resource_label=f"Valeur {item_code}",
        )
        deleted = int(
            deleter(
                list_code=str(shared_list.get("code") or list_code),
                code=str(item_code or "").strip().lower(),
            ) or 0
        )
        if deleted <= 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Valeur referentiel introuvable.")
        return MessageResponse(message="Valeur referentiel supprimee.")

    @app.post("/admin/shared-lists/{list_code}/items/import", response_model=SharedListImportResponse)
    @app.post("/admin/shared-lists/{list_code}/import-items", response_model=SharedListImportResponse)
    def import_admin_shared_list_items(
        list_code: str,
        payload: CustomServiceImportRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> SharedListImportResponse:
        _get_shared_list_or_404(api, list_code)
        raw_bytes = _decode_base64_payload(content_base64=payload.content_base64)
        selected_sheet_name = ""
        available_sheets: list[str] = []
        try:
            selected_sheet_name, available_sheets = resolve_tabular_sheet_selection(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=str(payload.sheet_name or ""),
            )
            parsed = parse_tabular_file_with_metadata(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=selected_sheet_name,
                header_mode=str(payload.header_mode or ""),
                header_row_number=int(payload.header_row_number or 1),
            )
            source_headers = parsed.headers
            source_rows = parsed.rows
            items, detected_rows, detected_columns = infer_shared_list_items_from_rows(
                labels=source_headers,
                rows=source_rows,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analyse du fichier impossible: {exc}") from exc
        return SharedListImportResponse(
            items=items,
            detected_rows=int(detected_rows),
            detected_columns=int(detected_columns),
            source_headers=[str(item or "") for item in list(source_headers or [])],
            source_rows_preview=[
                [str(value or "") for value in list(row or [])]
                for row in list(parsed.source_rows or [])[:12]
            ],
            available_sheets=[str(item or "") for item in list(available_sheets or []) if str(item or "").strip()],
            selected_sheet_name=str(selected_sheet_name or ""),
            detected_header_row_number=int(parsed.detected_header_row_number or 1),
            effective_header_mode=str(parsed.effective_header_mode or "auto"),
        )

    @app.get("/admin/shared-lists/{list_code}/items/export")
    @app.get("/admin/shared-lists/{list_code}/export-items")
    def export_admin_shared_list_items(
        list_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> StreamingResponse:
        lister = getattr(api.logs, "list_shared_list_items", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion referentiels indisponible.")
        shared_list = _get_shared_list_or_404(api, list_code)
        normalized_code = str(shared_list.get("code") or list_code).strip().lower()
        try:
            rows = list(lister(list_code=normalized_code) or [])
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export referentiel impossible: {exc}") from exc
        export_rows = [
            {
                "code": str(row.get("code") or ""),
                "label": str(row.get("label") or ""),
                "is_active": "1" if bool(row.get("is_active", True)) else "0",
                "sort_order": int(row.get("sort_order") or 0),
            }
            for row in rows
        ]
        csv_bytes = encode_csv_bytes(
            headers=["code", "label", "is_active", "sort_order"],
            rows=export_rows,
        )
        filename = f"shared_list_{normalized_code}.csv"
        return _csv_stream_response(csv_bytes=csv_bytes, filename=filename)

    @app.get("/admin/custom-services", response_model=list[CustomServiceResponse])
    def list_admin_custom_services(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> list[CustomServiceResponse]:
        return [CustomServiceResponse(**_with_custom_service_version_token(_with_resolved_custom_service(api, row))) for row in _list_custom_services_or_501(api)]

    @app.get("/admin/custom-services/{service_code}/relations", response_model=list[CustomServiceRelationResponse])
    def list_admin_custom_service_relations(
        service_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> list[CustomServiceRelationResponse]:
        service = _get_relation_entity_or_404(api, service_code)
        lister = getattr(api.logs, "list_custom_service_relations", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des relations indisponible.")
        normalized_code = _normalize_relation_entity_code(api, service.get("code") or service_code)
        try:
            rows = list(lister(service_code=normalized_code) or [])
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lecture relations impossible: {exc}") from exc
        return [CustomServiceRelationResponse(**row) for row in rows]

    @app.put("/admin/custom-services/{service_code}/relations", response_model=list[CustomServiceRelationResponse])
    def replace_admin_custom_service_relations(
        service_code: str,
        payload: CustomServiceRelationsReplaceRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> list[CustomServiceRelationResponse]:
        service = _get_relation_entity_or_404(api, service_code)
        replacer = getattr(api.logs, "replace_custom_service_relations", None)
        if not callable(replacer):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des relations indisponible.")
        normalized_code = _normalize_relation_entity_code(api, service.get("code") or service_code)
        if _is_reserved_system_entity_code(api, normalized_code) or _is_system_custom_service_code(api, normalized_code):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Les relations systeme se configurent depuis le socle annuaire.")
        relations_payload = [
            relation.model_dump() if hasattr(relation, "model_dump") else dict(relation)
            for relation in list(payload.relations or [])
        ]
        try:
            rows = list(replacer(
                service_code=normalized_code,
                relations=relations_payload,
                allow_linked_relation_deletion=bool(payload.allow_linked_relation_deletion),
            ) or [])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Enregistrement relations impossible: {exc}") from exc
        return [CustomServiceRelationResponse(**row) for row in rows]

    @app.post("/admin/custom-services/{service_code}/relations", response_model=CustomServiceRelationResponse)
    def upsert_admin_custom_service_relation(
        service_code: str,
        payload: CustomServiceRelationUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceRelationResponse:
        service = _get_relation_entity_or_404(api, service_code)
        saver = getattr(api.logs, "save_custom_service_relation", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des relations indisponible.")
        normalized_code = _normalize_relation_entity_code(api, service.get("code") or service_code)
        if _is_reserved_system_entity_code(api, normalized_code) or _is_system_custom_service_code(api, normalized_code):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Les relations systeme se configurent depuis le socle annuaire.")
        relation_payload = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
        if not str(relation_payload.get("target_service_code") or "").strip() and str(relation_payload.get("service_code") or "").strip():
            relation_payload["target_service_code"] = str(relation_payload.get("service_code") or "").strip()
        try:
            row = saver(source_service_code=normalized_code, relation=relation_payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Enregistrement relation impossible: {exc}") from exc
        return CustomServiceRelationResponse(**row)

    @app.delete("/admin/custom-services/{service_code}/relations/{relation_id}", response_model=MessageResponse)
    def delete_admin_custom_service_relation(
        service_code: str,
        relation_id: int,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> MessageResponse:
        service = _get_relation_entity_or_404(api, service_code)
        normalized_code = _normalize_relation_entity_code(api, service.get("code") or service_code)
        if _is_reserved_system_entity_code(api, normalized_code) or _is_system_custom_service_code(api, normalized_code):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Une relation systeme ne peut pas etre supprimee depuis les services personnalises.")
        deleter = getattr(api.logs, "delete_custom_service_relation", None)
        if not callable(deleter):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des relations indisponible.")
        try:
            deleted = int(
                deleter(
                    relation_id=relation_id,
                    source_service_code=normalized_code,
                ) or 0
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Suppression relation impossible: {exc}") from exc
        if deleted <= 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relation introuvable.")
        return MessageResponse(message="Relation supprimee.")

    @app.get("/admin/custom-services/{service_code}/relations/{relation_id}/impact", response_model=CustomServiceRelationImpactResponse)
    def get_admin_custom_service_relation_impact(
        service_code: str,
        relation_id: int,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceRelationImpactResponse:
        service = _get_relation_entity_or_404(api, service_code)
        impact_getter = getattr(api.logs, "get_custom_service_relation_impact", None)
        if not callable(impact_getter):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Analyse d'impact relation indisponible.")
        try:
            impact = impact_getter(
                relation_id=int(relation_id or 0),
                service_code=_normalize_relation_entity_code(api, service.get("code") or service_code),
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analyse impact relation impossible: {exc}") from exc
        if not impact:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relation introuvable.")
        return CustomServiceRelationImpactResponse(**impact)

    @app.post("/admin/custom-services/import/fields", response_model=CustomServiceImportResponse)
    @app.post("/admin/custom-services/import-fields", response_model=CustomServiceImportResponse)
    @app.post("/admin/custom-services/fields/import", response_model=CustomServiceImportResponse)
    @app.post("/admin/custom-services/import", response_model=CustomServiceImportResponse)
    def import_admin_custom_service_fields(
        payload: CustomServiceImportRequest,
        _api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceImportResponse:
        raw_bytes = _decode_base64_payload(content_base64=payload.content_base64)
        selected_sheet_name = ""
        available_sheets: list[str] = []
        try:
            selected_sheet_name, available_sheets = resolve_tabular_sheet_selection(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=str(payload.sheet_name or ""),
            )
            parsed = parse_tabular_file_with_metadata(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=selected_sheet_name,
                header_mode=str(payload.header_mode or ""),
                header_row_number=int(payload.header_row_number or 1),
            )
            source_headers = parsed.headers
            source_rows = parsed.rows
            import_until_row = max(0, int(payload.import_until_row_number or 0))
            if import_until_row > 0:
                row_limit = max(0, import_until_row - int(parsed.detected_header_row_number or 1))
                source_rows = list(source_rows or [])[:row_limit]
            fields, detected_rows, detected_columns = infer_service_fields_from_rows(
                labels=source_headers,
                rows=source_rows,
                column_mappings=list(payload.column_mappings or []),
            )
            effective_mapping = resolve_service_field_import_mapping(
                source_headers,
                list(payload.column_mappings or []),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analyse du fichier impossible: {exc}") from exc
        return CustomServiceImportResponse(
            fields=fields,
            detected_rows=int(detected_rows),
            detected_columns=int(detected_columns),
            source_headers=[str(item or "") for item in list(source_headers or [])],
            source_rows_preview=[
                [str(value or "") for value in list(row or [])]
                for row in list(parsed.source_rows or [])[:12]
            ],
            available_sheets=[str(item or "") for item in list(available_sheets or []) if str(item or "").strip()],
            selected_sheet_name=str(selected_sheet_name or ""),
            detected_header_row_number=int(parsed.detected_header_row_number or 1),
            effective_header_mode=str(parsed.effective_header_mode or "auto"),
            effective_mapping=effective_mapping,
        )

    @app.get("/admin/custom-services/{service_code}/fields/export")
    @app.get("/admin/custom-services/{service_code}/export/fields")
    def export_admin_custom_service_fields(
        service_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> StreamingResponse:
        service = _get_custom_service_or_404(api, service_code)
        normalized_code = str(service.get("code") or service_code).strip().lower()
        fields = list(service.get("fields") or [])
        export_rows = [
            {
                "field_key": str(row.get("field_key") or ""),
                "label": str(row.get("label") or ""),
                "field_kind": str(row.get("field_kind") or ""),
                "required": "1" if bool(row.get("required", False)) else "0",
                "list_source_kind": str(row.get("list_source_kind") or "local"),
                "shared_list_code": str(row.get("shared_list_code") or ""),
                "options": str(row.get("options") or ""),
                "default_value": str(row.get("default_value") or ""),
                "sort_order": int(row.get("sort_order") or 0),
            }
            for row in fields
        ]
        csv_bytes = encode_csv_bytes(
            headers=[
                "field_key",
                "label",
                "field_kind",
                "required",
                "list_source_kind",
                "shared_list_code",
                "options",
                "default_value",
                "sort_order",
            ],
            rows=export_rows,
        )
        filename = f"service_fields_{normalized_code}.csv"
        return _csv_stream_response(csv_bytes=csv_bytes, filename=filename)

    @app.post("/admin/custom-services", response_model=CustomServiceResponse)
    def create_admin_custom_service(
        payload: CustomServiceUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceResponse:
        saver = getattr(api.logs, "save_custom_service", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des services indisponible.")
        normalized_code, normalized_fields = _normalize_custom_service_upsert_payload(api, payload)
        if _is_reserved_system_entity_code(api, normalized_code) or _is_system_custom_service_code(api, normalized_code):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ce nom est reserve a un module systeme et ne peut pas etre utilise comme service personnalise.",
            )
        try:
            row = saver(
                code=normalized_code,
                label=str(payload.label or "").strip(),
                is_active=bool(payload.is_active) or bool(payload.is_technical),
                is_technical=bool(payload.is_technical),
                credentials_enabled=bool(payload.credentials_enabled),
                child_enabled=bool(payload.child_enabled),
                child_label=str(payload.child_label or "").strip() or "Elements lies",
                sort_order=int(payload.sort_order or 100),
                fields=normalized_fields,
                icon=str(payload.icon or "").strip(),
                color=str(payload.color or "").strip(),
                treeview_config=json.dumps({"tile": dict(payload.tile_config or {}), "relationship_inheritance": dict(payload.relationship_inheritance or {})}, ensure_ascii=False),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation service impossible: {exc}") from exc
        return CustomServiceResponse(**_with_custom_service_version_token(_with_resolved_custom_service(api, row)))

    @app.put("/admin/custom-services/{service_code}", response_model=CustomServiceResponse)
    def update_admin_custom_service(
        service_code: str,
        payload: CustomServiceUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceResponse:
        saver = getattr(api.logs, "save_custom_service", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des services indisponible.")
        existing = _get_custom_service_or_404(api, service_code)
        _assert_version_token(
            expected=_custom_service_version_token(existing),
            received=str(payload.version_token or ""),
            resource_label=f"Service {service_code}",
        )
        normalized_code, normalized_fields = _normalize_custom_service_upsert_payload(api, payload, code_override=service_code)
        if _is_reserved_system_entity_code(api, normalized_code):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ce nom est reserve a un module systeme et ne peut pas etre utilise comme service personnalise.",
            )
        if _is_system_custom_service_code(api, normalized_code) and _custom_service_system_definition_changed(existing, payload, normalized_fields):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ce module systeme ne peut etre modifie que pour afficher ou masquer sa tuile.",
            )
        if _is_system_custom_service_code(api, normalized_code):
            normalized_fields = normalize_service_fields(list(existing.get("fields") or []))
            payload.label = str(existing.get("label") or "").strip()
            payload.is_technical = bool(existing.get("is_technical", False))
            payload.credentials_enabled = bool(existing.get("credentials_enabled", False))
            payload.child_enabled = bool(existing.get("child_enabled", False))
            payload.child_label = str(existing.get("child_label") or "Elements lies").strip() or "Elements lies"
            payload.sort_order = int(existing.get("sort_order") or 100)
            payload.icon = str(existing.get("icon") or "").strip()
            payload.color = str(existing.get("color") or "").strip()
            payload.tile_config = dict(existing.get("tile_config") or {})
            payload.relationship_inheritance = dict(existing.get("relationship_inheritance") or {})
        try:
            row = saver(
                code=normalized_code,
                label=str(payload.label or "").strip(),
                is_active=bool(payload.is_active) or bool(payload.is_technical),
                is_technical=bool(payload.is_technical),
                credentials_enabled=bool(payload.credentials_enabled),
                child_enabled=bool(payload.child_enabled),
                child_label=str(payload.child_label or "").strip() or "Elements lies",
                sort_order=int(payload.sort_order or 100),
                fields=normalized_fields,
                icon=str(payload.icon or "").strip(),
                color=str(payload.color or "").strip(),
                treeview_config=json.dumps({"tile": dict(payload.tile_config or {}), "relationship_inheritance": dict(payload.relationship_inheritance or {})}, ensure_ascii=False),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Mise a jour service impossible: {exc}") from exc
        return CustomServiceResponse(**_with_custom_service_version_token(_with_resolved_custom_service(api, row)))

    @app.post("/admin/custom-services/{service_code}/credentials/purge", response_model=MessageResponse)
    def purge_admin_custom_service_credentials(
        service_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> MessageResponse:
        service = _get_custom_service_or_404(api, service_code)
        normalized_service_code = str(service.get("code") or service_code).strip().lower()
        purger = getattr(api.logs, "purge_custom_service_record_credentials", None)
        if callable(purger):
            try:
                updated_rows = int(
                    purger(
                        service_code=normalized_service_code,
                        credential_keys=list(CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS),
                    ) or 0
                )
            except Exception as exc:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Purge des identifiants impossible: {exc}") from exc
            return MessageResponse(message=f"Identifiants supprimes sur {updated_rows} fiche(s).")

        lister = getattr(api.logs, "list_custom_service_records", None)
        saver = getattr(api.logs, "save_custom_service_record", None)
        if not callable(lister) or not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Purge des identifiants indisponible.")
        try:
            rows = list(lister(service_code=normalized_service_code) or [])
            updated_rows = 0
            for row in rows:
                values = dict(row.get("values") or {})
                changed = False
                for key in CUSTOM_SERVICE_CREDENTIAL_PURGE_KEYS:
                    if key in values:
                        values.pop(key, None)
                        changed = True
                if not changed:
                    continue
                saver(
                    service_code=normalized_service_code,
                    record_id=str(row.get("id") or ""),
                    values=values,
                    children=list(row.get("children") or []),
                )
                updated_rows += 1
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Purge des identifiants impossible: {exc}") from exc
        return MessageResponse(message=f"Identifiants supprimes sur {updated_rows} fiche(s).")

    @app.get("/admin/custom-services/{service_code}/delete-impact", response_model=CustomServiceDeleteImpactResponse)
    def get_admin_custom_service_delete_impact(
        service_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceDeleteImpactResponse:
        existing = _get_custom_service_or_404(api, service_code)
        impact_getter = getattr(api.logs, "get_custom_service_delete_impact", None)
        if not callable(impact_getter):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Analyse d'impact service indisponible.")
        normalized = str(existing.get("code") or service_code).strip().lower()
        try:
            impact = impact_getter(service_code=normalized)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analyse impact service impossible: {exc}") from exc
        return CustomServiceDeleteImpactResponse(**(impact or {"service_code": normalized}))

    @app.delete("/admin/custom-services/{service_code}", response_model=MessageResponse)
    def delete_admin_custom_service(
        service_code: str,
        version_token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> MessageResponse:
        deleter = getattr(api.logs, "delete_custom_service", None)
        if not callable(deleter):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des services indisponible.")
        normalized = str(service_code or "").strip().lower()
        if _is_reserved_system_entity_code(api, normalized) or _is_system_custom_service_code(api, normalized):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ce module systeme n'est pas un service personnalise.",
            )
        existing = _get_custom_service_or_404(api, service_code)
        _assert_version_token(
            expected=_custom_service_version_token(existing),
            received=version_token,
            resource_label=f"Service {service_code}",
        )
        try:
            deleted = int(deleter(code=normalized) or 0)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Suppression service impossible: {exc}") from exc
        if deleted <= 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable.")
        return MessageResponse(message="Service supprime.")

    @app.post("/admin/custom-services/{service_code}/records/import/preview", response_model=CustomServiceRecordImportPreviewResponse)
    def preview_admin_custom_service_records_import(
        service_code: str,
        payload: CustomServiceRecordImportRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceRecordImportPreviewResponse:
        service = _get_custom_service_or_404(api, service_code)
        raw_bytes = _decode_base64_payload(content_base64=payload.content_base64)
        selected_sheet_name = ""
        available_sheets: list[str] = []
        try:
            selected_sheet_name, available_sheets = resolve_tabular_sheet_selection(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=str(payload.sheet_name or ""),
            )
            parsed = parse_tabular_file_with_metadata(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=selected_sheet_name,
                header_mode=str(payload.header_mode or ""),
                header_row_number=int(payload.header_row_number or 1),
            )
            source_headers = parsed.headers
            source_rows = parsed.rows
            import_until_row = max(0, int(payload.import_until_row_number or 0))
            if import_until_row > 0:
                row_limit = max(0, import_until_row - int(parsed.detected_header_row_number or 1))
                source_rows = list(source_rows or [])[:row_limit]
            effective_fields, resolved_column_mappings, created_fields = _with_record_import_created_fields(
                service=service,
                headers=source_headers,
                rows=source_rows,
                column_mappings=list(payload.column_mappings or []),
            )
            rows, detected_rows, detected_columns, issues = infer_custom_service_records_from_rows(
                headers=source_headers,
                rows=source_rows,
                fields=effective_fields,
                column_mappings=resolved_column_mappings,
                child_enabled=bool(service.get("child_enabled", False)),
                credentials_enabled=bool(service.get("credentials_enabled", False)),
                include_source_values=True,
            )
            effective_mapping = resolve_effective_record_column_mapping(
                headers=source_headers,
                fields=effective_fields,
                column_mappings=resolved_column_mappings,
                credentials_enabled=bool(service.get("credentials_enabled", False)),
            )
            if created_fields:
                issues.append(f"{len(created_fields)} nouveau(x) champ(s) seront crees a l'import.")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analyse du fichier impossible: {exc}") from exc
        return CustomServiceRecordImportPreviewResponse(
            rows=rows,
            fields=effective_fields,
            detected_rows=int(detected_rows),
            detected_columns=int(detected_columns),
            issues=[str(item or "") for item in list(issues or []) if str(item or "").strip()],
            source_headers=[str(item or "") for item in list(source_headers or [])],
            source_rows_preview=[
                [str(value or "") for value in list(row or [])]
                for row in list(parsed.source_rows or [])[:12]
            ],
            available_sheets=[str(item or "") for item in list(available_sheets or []) if str(item or "").strip()],
            selected_sheet_name=str(selected_sheet_name or ""),
            detected_header_row_number=int(parsed.detected_header_row_number or 1),
            effective_header_mode=str(parsed.effective_header_mode or "auto"),
            effective_mapping=effective_mapping,
        )

    @app.post("/admin/custom-services/{service_code}/records/import/apply", response_model=CustomServiceRecordImportApplyResponse)
    def apply_admin_custom_service_records_import(
        service_code: str,
        payload: CustomServiceRecordImportRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceRecordImportApplyResponse:
        service = _get_custom_service_or_404(api, service_code)
        saver = getattr(api.logs, "save_custom_service_record", None)
        lister = getattr(api.logs, "list_custom_service_records", None)
        service_saver = getattr(api.logs, "save_custom_service", None)
        if not callable(saver) or not callable(lister) or not callable(service_saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des donnees service indisponible.")
        raw_bytes = _decode_base64_payload(content_base64=payload.content_base64)
        selected_sheet_name = ""
        try:
            selected_sheet_name, _available_sheets = resolve_tabular_sheet_selection(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=str(payload.sheet_name or ""),
            )
            parsed = parse_tabular_file_with_metadata(
                filename=str(payload.filename or ""),
                content_bytes=raw_bytes,
                sheet_name=selected_sheet_name,
                header_mode=str(payload.header_mode or ""),
                header_row_number=int(payload.header_row_number or 1),
            )
            source_rows = parsed.rows
            import_until_row = max(0, int(payload.import_until_row_number or 0))
            if import_until_row > 0:
                row_limit = max(0, import_until_row - int(parsed.detected_header_row_number or 1))
                source_rows = list(source_rows or [])[:row_limit]
            effective_fields, resolved_column_mappings, created_fields = _with_record_import_created_fields(
                service=service,
                headers=parsed.headers,
                rows=source_rows,
                column_mappings=list(payload.column_mappings or []),
            )
            rows, detected_rows, _detected_columns, parser_issues = infer_custom_service_records_from_rows(
                headers=parsed.headers,
                rows=source_rows,
                fields=effective_fields,
                column_mappings=resolved_column_mappings,
                child_enabled=bool(service.get("child_enabled", False)),
                credentials_enabled=bool(service.get("credentials_enabled", False)),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analyse du fichier impossible: {exc}") from exc

        normalized_service_code = str(service.get("code") or service_code).strip().lower()
        history_date_field_key = str(payload.history_date_field_key or "").strip()
        history_date_source_column = str(payload.history_date_source_column or "").strip()
        if bool(history_date_field_key) != bool(history_date_source_column):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La date d'historique requiert un champ historise et une colonne du fichier.",
            )
        if history_date_field_key:
            history_field = next(
                (field for field in effective_fields if str(field.get("field_key") or "").strip() == history_date_field_key),
                None,
            )
            if not history_field or not bool(history_field.get("track_history")):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Le champ choisi pour la date doit etre configure avec l'historique.",
                )
            matched_history_column = next(
                (header for header in parsed.headers if str(header or "").strip().lower() == history_date_source_column.lower()),
                "",
            )
            if not matched_history_column:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="La colonne de date d'historique est introuvable dans le fichier.",
                )
            history_date_source_column = str(matched_history_column)
        existing_rows = list(lister(service_code=normalized_service_code) or [])
        existing_ids = {str(row.get("id") or "").strip() for row in existing_rows if str(row.get("id") or "").strip()}
        existing_by_id = {
            str(row.get("id") or "").strip(): dict(row or {})
            for row in existing_rows
            if str(row.get("id") or "").strip()
        }
        upsert_existing = bool(payload.upsert_existing)
        relaxed_validation = bool(payload.relaxed_validation)
        credential_mode = normalize_credential_import_mode(payload.credential_mode)
        credentials_enabled = bool(service.get("credentials_enabled", False))
        duplicate_policy = str(payload.duplicate_policy or "skip").strip().lower()
        if duplicate_policy not in {"skip", "update", "create"}:
            duplicate_policy = "skip"
        duplicate_field_key = str(payload.duplicate_field_key or "").strip()
        if not duplicate_field_key and normalized_service_code == "emails":
            duplicate_field_key = "address"

        existing_by_duplicate_value: dict[str, dict] = {}
        if duplicate_field_key:
            for existing in existing_rows:
                existing_values = dict(existing.get("values") or {}) if isinstance(existing, dict) else {}
                duplicate_value = _normalize_custom_service_duplicate_value(
                    duplicate_field_key,
                    existing_values.get(duplicate_field_key),
                )
                if duplicate_value and duplicate_value not in existing_by_duplicate_value:
                    existing_by_duplicate_value[duplicate_value] = dict(existing)

        created = 0
        updated = 0
        skipped = 0
        issues = [str(item or "") for item in list(parser_issues or []) if str(item or "").strip()]
        fields = effective_fields
        child_enabled = bool(service.get("child_enabled", False))
        prepared_rows: list[dict] = []
        for row in rows:
            record_id = str(row.get("record_id") or "").strip()
            row_label = f"Ligne {int(row.get('_row_index') or 0)}" if int(row.get("_row_index") or 0) > 0 else f"Fiche {record_id or '(nouvelle)'}"
            values = dict(row.get("values") or {})
            children = list(row.get("children") or [])
            duplicate_value = _normalize_custom_service_duplicate_value(
                duplicate_field_key,
                values.get(duplicate_field_key),
            ) if duplicate_field_key else ""
            duplicate_row = existing_by_duplicate_value.get(duplicate_value) if duplicate_value else None
            if not record_id and isinstance(duplicate_row, dict):
                duplicate_id = str(duplicate_row.get("id") or "").strip()
                if duplicate_policy == "skip":
                    skipped += 1
                    issues.append(f"{row_label}: doublon detecte selon « {duplicate_field_key} », ligne ignoree.")
                    continue
                if duplicate_policy == "update" and duplicate_id:
                    record_id = duplicate_id
            if record_id and record_id in existing_ids and not upsert_existing:
                skipped += 1
                issues.append(f"{row_label}: fiche {record_id} deja existante, ignoree.")
                continue
            try:
                existing_row = existing_by_id.get(record_id) if record_id else None
                existing_values = dict(existing_row.get("values") or {}) if isinstance(existing_row, dict) else {}
                try:
                    imported_values = validate_record_values(fields=fields, values=values, fill_defaults=not isinstance(existing_row, dict))
                except ValueError as exc:
                    if not relaxed_validation:
                        raise
                    issues.append(f"{row_label}: {exc} Valeur importee quand meme.")
                    imported_values = {
                        str(field.get("field_key") or "").strip(): str(values.get(str(field.get("field_key") or "").strip()) or "").strip()
                        for field in list(fields or [])
                        if str(field.get("field_key") or "").strip() and str(field.get("field_key") or "").strip() in values
                    }
                validated_values = dict(existing_values) if isinstance(existing_row, dict) else {}
                validated_values.update(imported_values)
                if credentials_enabled:
                    imported_credentials = _extract_custom_service_credential_values(values, enabled=True)
                    existing_credentials = _extract_custom_service_credential_values(existing_values, enabled=True)
                    resolved_credentials = resolve_credential_import_values(
                        mode=credential_mode,
                        operation="update" if isinstance(existing_row, dict) else "create",
                        login_present=(
                            CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY in values
                            or "login" in values
                        ),
                        login_value=imported_credentials.get(CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY, ""),
                        password_present=(
                            CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY in values
                            or "password" in values
                        ),
                        password_value=imported_credentials.get(CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY, ""),
                    )
                    effective_credentials: dict[str, str] = {}
                    if isinstance(existing_row, dict):
                        effective_credentials.update(existing_credentials)
                    if resolved_credentials.login is not None:
                        effective_credentials[CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY] = resolved_credentials.login
                    if resolved_credentials.password is not None:
                        effective_credentials[CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY] = resolved_credentials.password
                    if effective_credentials:
                        validated_values.update(effective_credentials)
                elif _custom_service_import_contains_credentials(values):
                    issues.append(
                        f"{row_label}: identifiants importes ignores (gestion des identifiants desactivee)."
                    )
                normalized_children = normalize_child_rows(children) if child_enabled else []
            except ValueError as exc:
                skipped += 1
                issues.append(f"{row_label}: {exc}")
                continue
            prepared_rows.append(
                {
                    "record_id": record_id,
                    "row_label": row_label,
                    "values": validated_values,
                    "children": normalized_children,
                    "history_changed_at_by_field": {
                        history_date_field_key: str((row.get("source_values") or {}).get(history_date_source_column) or "").strip(),
                    } if history_date_field_key and str((row.get("source_values") or {}).get(history_date_source_column) or "").strip() else {},
                }
            )
            if duplicate_value and not isinstance(duplicate_row, dict):
                existing_by_duplicate_value[duplicate_value] = {"id": record_id, "values": values}
        if skipped > 0 and not relaxed_validation:
            return CustomServiceRecordImportApplyResponse(
                processed=int(detected_rows),
                created=0,
                updated=0,
                skipped=int(skipped),
                issues=issues,
            )
        if created_fields:
            if _is_system_custom_service_code(api, normalized_service_code):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Ce module systeme n'autorise pas la creation de nouveaux champs par import. Mappez les colonnes vers les champs existants.",
                )
            try:
                service = service_saver(
                    code=normalized_service_code,
                    label=str(service.get("label") or normalized_service_code),
                    is_active=bool(service.get("is_active", True)),
                    credentials_enabled=bool(service.get("credentials_enabled", False)),
                    child_enabled=child_enabled,
                    child_label=str(service.get("child_label") or "Elements lies"),
                    sort_order=int(service.get("sort_order") or 100),
                    fields=fields,
                )
                issues.append(f"{len(created_fields)} nouveau(x) champ(s) cree(s) dans le service.")
            except Exception as exc:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation colonne service impossible: {exc}") from exc
        email_agent_index = _directory_agent_mail_index(api) if normalized_service_code == "emails" else {}
        email_agent_relation_id = _directory_email_agent_relation_id(api) if normalized_service_code == "emails" else 0
        auto_email_links = 0
        for prepared in prepared_rows:
            record_id = str(prepared.get("record_id") or "").strip()
            row_label = str(prepared.get("row_label") or f"Fiche {record_id or '(nouvelle)'}")
            try:
                saved = saver(
                    service_code=normalized_service_code,
                    record_id=record_id,
                    values=dict(prepared.get("values") or {}),
                    children=list(prepared.get("children") or []),
                    change_source="import",
                    history_changed_at_by_field=dict(prepared.get("history_changed_at_by_field") or {}),
                )
            except ValueError as exc:
                skipped += 1
                issues.append(f"{row_label}: {exc}")
                continue
            except Exception as exc:
                skipped += 1
                issues.append(f"{row_label}: sauvegarde impossible ({exc})")
                continue
            saved_id = str(saved.get("id") or "").strip()
            if record_id and record_id in existing_ids:
                updated += 1
            else:
                created += 1
            if saved_id:
                existing_ids.add(saved_id)
            if normalized_service_code == "emails" and saved_id:
                linked_agent_id = _link_email_record_to_matching_agent(
                    api,
                    email_record=saved,
                    agent_by_mail=email_agent_index,
                    relation_id=email_agent_relation_id,
                )
                if linked_agent_id:
                    auto_email_links += 1
        if auto_email_links:
            issues.append(f"{auto_email_links} lien(s) Agent / Email cree(s) automatiquement par correspondance exacte de l'adresse.")

        return CustomServiceRecordImportApplyResponse(
            processed=int(detected_rows),
            created=int(created),
            updated=int(updated),
            skipped=int(skipped),
            issues=issues,
        )

    @app.post("/admin/custom-services/{service_code}/records/import/active-directory", response_model=CustomServiceRecordImportApplyResponse)
    def apply_admin_custom_service_records_active_directory_import(
        service_code: str,
        payload: CustomServiceRecordActiveDirectoryImportRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceRecordImportApplyResponse:
        service = _get_custom_service_or_404(api, service_code)
        saver = getattr(api.logs, "save_custom_service_record", None)
        lister = getattr(api.logs, "list_custom_service_records", None)
        if not callable(saver) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des donnees service indisponible.")

        target_kind = _normalize_active_directory_sync_target_kind(str(payload.target_kind or "organizational_units"))
        normalized_service_code = str(service.get("code") or service_code).strip().lower()
        service_fields = list(service.get("fields") or [])
        valid_field_keys = {
            str(field.get("field_key") or "").strip()
            for field in service_fields
            if str(field.get("field_key") or "").strip()
        }
        mappings: list[dict[str, str]] = []
        for mapping in list(payload.field_mappings or []):
            if not isinstance(mapping, dict):
                continue
            attribute = str(mapping.get("attribute") or "").strip()
            target = str(mapping.get("target") or "existing").strip().lower()
            field_key = str(mapping.get("field_key") or "").strip()
            if not attribute or target == "ignore" or not field_key or field_key not in valid_field_keys:
                continue
            mappings.append({"attribute": attribute, "field_key": field_key})
        if not mappings:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Aucun mapping AD exploitable pour importer les donnees.")

        entries = api.logs.list_sync_source_cache_entries(
            source_kind="active_directory",
            target_kind=target_kind,
            limit=max(1, min(5000, int(payload.limit or 5000))),
        )
        if not entries:
            try:
                _refresh_active_directory_cache_for_target(api, target_kind)
            except (ValueError, RuntimeError) as exc:
                return CustomServiceRecordImportApplyResponse(
                    processed=0,
                    created=0,
                    updated=0,
                    skipped=0,
                    issues=[f"Cache Active Directory vide et refresh impossible: {exc}"],
                )
            except Exception as exc:
                return CustomServiceRecordImportApplyResponse(
                    processed=0,
                    created=0,
                    updated=0,
                    skipped=0,
                    issues=[f"Cache Active Directory vide et refresh impossible: {exc}"],
                )
            entries = api.logs.list_sync_source_cache_entries(
                source_kind="active_directory",
                target_kind=target_kind,
                limit=max(1, min(5000, int(payload.limit or 5000))),
            )
            if not entries:
                return CustomServiceRecordImportApplyResponse(
                    processed=0,
                    created=0,
                    updated=0,
                    skipped=0,
                    issues=["Cache Active Directory vide apres refresh. Verifiez le type AD choisi et le filtre LDAP."],
                )

        existing_rows = list(lister(service_code=normalized_service_code) or [])
        existing_by_id = {
            str(row.get("id") or "").strip(): dict(row or {})
            for row in existing_rows
            if str(row.get("id") or "").strip()
        }
        existing_ids = set(existing_by_id.keys())
        created = 0
        updated = 0
        skipped = 0
        issues: list[str] = []
        upsert_existing = bool(payload.upsert_existing)
        relaxed_validation = bool(payload.relaxed_validation)

        for index, entry in enumerate(entries, start=1):
            external_id = str(entry.get("external_id") or "").strip()
            raw_payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
            if not external_id:
                skipped += 1
                issues.append(f"Ligne AD {index}: identifiant externe absent, ignoree.")
                continue
            record_id = "ad_" + hashlib.sha1(f"{target_kind}:{external_id}".encode("utf-8")).hexdigest()
            if record_id in existing_ids and not upsert_existing:
                skipped += 1
                issues.append(f"Ligne AD {index}: fiche deja existante, ignoree.")
                continue
            values: dict[str, str] = {}
            for mapping in mappings:
                value = _ldap_entry_attribute_value(raw_payload, mapping["attribute"])
                values[mapping["field_key"]] = _active_directory_import_value_to_text(value)
            existing_row = existing_by_id.get(record_id)
            existing_values = dict(existing_row.get("values") or {}) if isinstance(existing_row, dict) else {}
            try:
                imported_values = validate_record_values(
                    fields=service_fields,
                    values=values,
                    fill_defaults=not isinstance(existing_row, dict),
                )
            except ValueError as exc:
                if not relaxed_validation:
                    skipped += 1
                    issues.append(f"Ligne AD {index}: {exc}")
                    continue
                issues.append(f"Ligne AD {index}: {exc} Valeur importee quand meme.")
                imported_values = {
                    key: str(value or "").strip()
                    for key, value in values.items()
                    if key in valid_field_keys
                }
            merged_values = dict(existing_values)
            merged_values.update(imported_values)
            try:
                saver(
                    service_code=normalized_service_code,
                    record_id=record_id,
                    values=merged_values,
                    children=[],
                    change_source="active_directory",
                    sync_source_kind="active_directory",
                    sync_target_kind=target_kind,
                    sync_external_id=external_id,
                    sync_status="active",
                )
            except ValueError as exc:
                skipped += 1
                issues.append(f"Ligne AD {index}: {exc}")
                continue
            except Exception as exc:
                skipped += 1
                issues.append(f"Ligne AD {index}: sauvegarde impossible ({exc})")
                continue
            if record_id in existing_ids:
                updated += 1
            else:
                created += 1
                existing_ids.add(record_id)
        trasher = getattr(api.logs, "trash_stale_synced_custom_service_records", None)
        if callable(trasher):
            active_external_ids = {
                str(entry.get("external_id") or "").strip()
                for entry in entries
                if str(entry.get("external_id") or "").strip()
            }
            trashed = int(
                trasher(
                    service_code=normalized_service_code,
                    source_kind="active_directory",
                    target_kind=target_kind,
                    active_external_ids=active_external_ids,
                    reason="Absent de la synchronisation Active Directory active",
                )
                or 0
            )
            if trashed:
                issues.append(f"{trashed} fiche(s) AD absente(s) ou inactive(s) deplacee(s) en corbeille.")

        return CustomServiceRecordImportApplyResponse(
            processed=len(entries),
            created=int(created),
            updated=int(updated),
            skipped=int(skipped),
            issues=issues,
        )

    @app.get("/admin/custom-services/{service_code}/records/export")
    @app.get("/admin/custom-services/{service_code}/export/records")
    def export_admin_custom_service_records(
        service_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> StreamingResponse:
        lister = getattr(api.logs, "list_custom_service_records", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des donnees service indisponible.")
        service = _get_custom_service_or_404(api, service_code)
        normalized_service_code = str(service.get("code") or service_code).strip().lower()
        try:
            rows = list(lister(service_code=normalized_service_code) or [])
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export des fiches impossible: {exc}") from exc
        csv_bytes = export_custom_service_records_to_csv(service=service, rows=rows)
        filename = f"service_records_{normalized_service_code}.csv"
        return _csv_stream_response(csv_bytes=csv_bytes, filename=filename)

    @app.get("/admin/custom-services/{service_code}/records/query", response_model=CustomServiceRecordQueryResponse)
    def query_admin_custom_service_records(
        service_code: str,
        search: str = Query(default=""),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        sort: str = Query(default="label"),
        direction: str = Query(default="asc"),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceRecordQueryResponse:
        querier = getattr(api.logs, "query_custom_service_record_index", None)
        if not callable(querier):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Recherche des fiches indisponible.")
        service = _get_custom_service_or_404(api, service_code)
        normalized_service_code = str(service.get("code") or service_code).strip().lower()
        normalized_sort = str(sort or "label").strip().lower()
        if normalized_sort not in {"label", "updated_at", "created_at"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tri invalide.")
        normalized_direction = str(direction or "asc").strip().lower()
        if normalized_direction not in {"asc", "desc"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Direction de tri invalide.")
        try:
            backfill_record_index(manager=api.logs, batch_size=500)
            page = querier(
                service_code=normalized_service_code,
                search=str(search or ""),
                limit=int(limit),
                offset=int(offset),
                sort=normalized_sort,
                direction=normalized_direction,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Recherche des fiches impossible: {exc}") from exc
        page_items = list((page or {}).get("items") or [])
        if normalized_service_code == "emails":
            page_items = _enrich_email_records_with_agent_services(api, page_items)
        items = [
            CustomServiceRecordResponse(
                **_custom_service_record_response_payload(
                    row,
                    credentials_enabled=bool(service.get("credentials_enabled", False)),
                )
            )
            for row in page_items
        ]
        return CustomServiceRecordQueryResponse(
            items=items,
            total=int((page or {}).get("total") or 0),
            limit=int((page or {}).get("limit") or limit),
            offset=int((page or {}).get("offset") or offset),
        )

    @app.get("/admin/custom-services/{service_code}/records", response_model=list[CustomServiceRecordResponse])
    def list_admin_custom_service_records(
        service_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> list[CustomServiceRecordResponse]:
        lister = getattr(api.logs, "list_custom_service_records", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des donnees service indisponible.")
        service = _get_custom_service_or_404(api, service_code)
        try:
            rows = lister(service_code=str(service.get("code") or service_code))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lecture des donnees impossible: {exc}") from exc
        if str(service.get("code") or service_code).strip().lower() == "emails":
            rows = _enrich_email_records_with_agent_services(api, list(rows or []))
        return [
            CustomServiceRecordResponse(
                **_custom_service_record_response_payload(
                    row,
                    credentials_enabled=bool(service.get("credentials_enabled", False)),
                )
            )
            for row in (rows or [])
        ]

    @app.get("/admin/custom-services/{service_code}/records/duplicates")
    def analyze_admin_custom_service_record_duplicates(
        service_code: str,
        field_key: str = Query(min_length=1),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> dict:
        lister = getattr(api.logs, "list_custom_service_records", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Analyse des doublons indisponible.")
        service = _get_custom_service_or_404(api, service_code)
        normalized_field = str(field_key or "").strip()
        known_fields = {str(item.get("field_key") or "").strip() for item in list(service.get("fields") or [])}
        if normalized_field not in known_fields:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Champ de comparaison inconnu.")
        groups: dict[str, list[dict]] = {}
        for row in list(lister(service_code=str(service.get("code") or service_code)) or []):
            values = dict(row.get("values") or {})
            raw_value = str(values.get(normalized_field) or "")
            normalized_value = _normalize_custom_service_duplicate_value(normalized_field, raw_value)
            if normalized_value:
                groups.setdefault(normalized_value, []).append({"id": str(row.get("id") or ""), "value": raw_value, "values": values})
        duplicates = [
            {"value": items[0]["value"], "records": items}
            for items in groups.values() if len(items) > 1
        ]
        return {"field_key": normalized_field, "groups": duplicates, "group_count": len(duplicates), "record_count": sum(len(item["records"]) for item in duplicates)}

    @app.get(
        "/admin/custom-services/{service_code}/records/{record_id}/relations/{relation_id}/links",
        response_model=list[CustomServiceRelationLinkResponse],
    )
    def list_admin_custom_service_record_relation_links(
        service_code: str,
        record_id: str,
        relation_id: int,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> list[CustomServiceRelationLinkResponse]:
        _get_relation_entity_or_404(api, service_code)
        lister = getattr(api.logs, "list_custom_service_record_relation_links", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des relations de fiches indisponible.")
        try:
            rows = list(lister(service_code=_normalize_relation_entity_code(api, service_code), record_id=record_id, relation_id=relation_id) or [])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lecture relations fiche impossible: {exc}") from exc
        return [CustomServiceRelationLinkResponse(**row) for row in rows]

    @app.post(
        "/admin/custom-services/{service_code}/records/relations/{relation_id}/links/batch",
        response_model=dict[str, list[CustomServiceRelationLinkResponse]],
    )
    def list_admin_custom_service_record_relation_links_batch(
        service_code: str,
        relation_id: int,
        payload: CustomServiceRelationLinksBatchRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> dict[str, list[CustomServiceRelationLinkResponse]]:
        _get_relation_entity_or_404(api, service_code)
        lister = getattr(api.logs, "list_custom_service_relation_links_for_record_ids", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des relations de fiches indisponible.")
        record_ids = list(dict.fromkeys(str(item or "").strip() for item in list(payload.record_ids or []) if str(item or "").strip()))
        if not record_ids:
            return {}
        try:
            rows_by_record = lister(
                service_code=_normalize_relation_entity_code(api, service_code),
                record_ids=record_ids,
                relation_id=int(relation_id or 0),
            ) or {}
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lecture relations fiche impossible: {exc}") from exc
        return {
            str(record_id): [CustomServiceRelationLinkResponse(**row) for row in list(links or [])]
            for record_id, links in dict(rows_by_record).items()
        }

    @app.post(
        "/admin/custom-services/{service_code}/records/{record_id}/relations/{relation_id}/links",
        response_model=CustomServiceRelationLinkResponse,
    )
    def create_admin_custom_service_record_relation_link(
        service_code: str,
        record_id: str,
        relation_id: int,
        payload: CustomServiceRelationLinkCreateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceRelationLinkResponse:
        _get_relation_entity_or_404(api, service_code)
        saver = getattr(api.logs, "save_custom_service_record_relation_link", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des relations de fiches indisponible.")
        try:
            row = saver(
                service_code=_normalize_relation_entity_code(api, service_code),
                record_id=record_id,
                relation_id=relation_id,
                linked_record_id=payload.linked_record_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation lien fiche impossible: {exc}") from exc
        return CustomServiceRelationLinkResponse(**row)

    @app.delete(
        "/admin/custom-services/{service_code}/records/{record_id}/relations/{relation_id}/links/{linked_record_id}",
        response_model=MessageResponse,
    )
    def delete_admin_custom_service_record_relation_link(
        service_code: str,
        record_id: str,
        relation_id: int,
        linked_record_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> MessageResponse:
        _get_relation_entity_or_404(api, service_code)
        deleter = getattr(api.logs, "delete_custom_service_record_relation_link", None)
        if not callable(deleter):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des relations de fiches indisponible.")
        try:
            deleted = int(
                deleter(
                    service_code=_normalize_relation_entity_code(api, service_code),
                    record_id=record_id,
                    relation_id=relation_id,
                    linked_record_id=linked_record_id,
                ) or 0
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Suppression lien fiche impossible: {exc}") from exc
        if deleted <= 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lien introuvable.")
        return MessageResponse(message="Lien supprime.")

    @app.post("/admin/custom-services/{service_code}/records", response_model=CustomServiceRecordResponse)
    def create_admin_custom_service_record(
        service_code: str,
        payload: CustomServiceRecordUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceRecordResponse:
        saver = getattr(api.logs, "save_custom_service_record", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des donnees service indisponible.")
        service = _get_custom_service_or_404(api, service_code)
        service_fields = list(service.get("fields") or [])
        credentials_enabled = bool(service.get("credentials_enabled", False))
        normalized_service_code = str(service.get("code") or service_code).strip().lower()
        relation_links = {
            str(relation_id or "").strip(): [str(record_id or "").strip() for record_id in list(record_ids or []) if str(record_id or "").strip()]
            for relation_id, record_ids in dict(payload.relation_links or {}).items()
            if str(relation_id or "").strip()
        }
        relation_lister = getattr(api.logs, "list_custom_service_relations", None)
        relation_link_saver = getattr(api.logs, "save_custom_service_record_relation_link", None)
        relation_link_deleter = getattr(api.logs, "delete_custom_service_record", None)
        required_relations: list[dict] = []
        if callable(relation_lister):
            required_relations = [
                relation
                for relation in list(relation_lister(service_code=normalized_service_code) or [])
                if str(relation.get("source_service_code") or "").strip().lower() == normalized_service_code
                and bool(relation.get("is_active", True))
                and bool(relation.get("required", False))
            ]
            for relation in required_relations:
                if not relation_links.get(str(relation.get("id") or "")):
                    label = str(relation.get("display_label") or relation.get("target_service_code") or "element lie").strip()
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"La relation obligatoire « {label} » doit etre renseignee avant la creation.",
                    )
        try:
            normalized_values = validate_record_values(fields=service_fields, values=dict(payload.values or {}), fill_defaults=True)
            normalized_values.update(
                _extract_custom_service_credential_values(
                    dict(payload.values or {}),
                    enabled=credentials_enabled,
                )
            )
            normalized_children = normalize_child_rows([row.model_dump() for row in list(payload.children or [])])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        if not bool(service.get("child_enabled")) and normalized_children:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce service n'autorise pas les elements lies.")
        if str(service.get("code") or service_code).strip().lower() == "emails" and str(normalized_values.get("status") or "").strip().lower() == "a supprimer":
            if not _normalize_notification_due_at(str(payload.reminder_due_at or "")):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Date de rappel requise pour passer un Email a supprimer.",
                )
        try:
            row = saver(
                service_code=normalized_service_code,
                values=normalized_values,
                children=normalized_children,
                record_id="",
                change_source="manual",
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation de la fiche impossible: {exc}") from exc
        try:
            if relation_links and not callable(relation_link_saver):
                raise ValueError("Gestion des relations de fiches indisponible.")
            relations_by_id = {
                str(relation.get("id") or ""): relation
                for relation in list(relation_lister(service_code=normalized_service_code) or [])
                if str(relation.get("id") or "").strip()
            } if callable(relation_lister) else {}

            def relation_link_sort_key(item: tuple[str, list[str]]) -> tuple[int, int, int, int, str]:
                relation_id, _linked_record_ids = item
                relation = relations_by_id.get(str(relation_id)) or {}
                try:
                    numeric_id = int(relation_id)
                except (TypeError, ValueError):
                    numeric_id = 0
                # Required links and links carrying a scoped unique value must
                # exist before candidate filters can assess shared relations.
                return (
                    0 if bool(relation.get("required", False)) else 1,
                    0 if str(relation.get("unique_value_field_key") or "").strip() else 1,
                    0 if not bool(relation.get("filter_candidates_by_shared_relation", False)) else 1,
                    numeric_id,
                    str(relation_id),
                )

            for relation_id, linked_record_ids in sorted(relation_links.items(), key=relation_link_sort_key):
                for linked_record_id in linked_record_ids:
                    relation_link_saver(
                        service_code=normalized_service_code,
                        record_id=str(row.get("id") or ""),
                        relation_id=int(relation_id or 0),
                        linked_record_id=linked_record_id,
                    )
        except Exception as exc:
            if callable(relation_link_deleter):
                try:
                    relation_link_deleter(service_code=normalized_service_code, record_id=str(row.get("id") or ""))
                except Exception:
                    pass
            if isinstance(exc, ValueError):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation relation obligatoire impossible: {exc}") from exc
        _sync_email_status_notification_task(
            api,
            service_code=normalized_service_code,
            record_id=str(row.get("id") or ""),
            values=dict(row.get("values") or normalized_values),
            reminder_due_at=str(payload.reminder_due_at or ""),
        )
        return CustomServiceRecordResponse(
            **_custom_service_record_response_payload(
                row,
                credentials_enabled=credentials_enabled,
            )
        )

    @app.put("/admin/custom-services/{service_code}/records/{record_id}", response_model=CustomServiceRecordResponse)
    def update_admin_custom_service_record(
        service_code: str,
        record_id: str,
        payload: CustomServiceRecordUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> CustomServiceRecordResponse:
        saver = getattr(api.logs, "save_custom_service_record", None)
        lister = getattr(api.logs, "list_custom_service_records", None)
        if not callable(saver) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des donnees service indisponible.")
        service = _get_custom_service_or_404(api, service_code)
        normalized_service_code = str(service.get("code") or service_code)
        credentials_enabled = bool(service.get("credentials_enabled", False))
        rows = lister(service_code=normalized_service_code)
        existing = next((row for row in rows if str(row.get("id") or "") == str(record_id or "")), None)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiche introuvable.")
        _assert_version_token(
            expected=_custom_service_record_version_token(existing),
            received=str(payload.version_token or ""),
            resource_label=f"Fiche {record_id}",
        )
        service_fields = list(service.get("fields") or [])
        try:
            normalized_values = validate_record_values(fields=service_fields, values=dict(payload.values or {}), fill_defaults=False)
            normalized_values.update(
                _extract_custom_service_credential_values(
                    dict(payload.values or {}),
                    enabled=credentials_enabled,
                )
            )
            merged_values = dict(existing.get("values") or {})
            merged_values.update(normalized_values)
            normalized_children = normalize_child_rows([row.model_dump() for row in list(payload.children or [])])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        history_events = build_field_history_events(
            fields=service_fields,
            old_values=dict(existing.get("values") or {}),
            new_values=merged_values,
        )
        skip_history_changes = bool(payload.skip_history_changes)
        if history_events and not bool(payload.confirm_history_changes) and not skip_history_changes:
            labels_by_key = {
                str(field.get("field_key") or ""): str(field.get("label") or field.get("field_key") or "")
                for field in service_fields
            }
            changed_labels = [
                labels_by_key.get(str(event.get("field_key") or ""), str(event.get("field_key") or ""))
                for event in history_events
            ]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Confirmation requise pour historiser: {', '.join(changed_labels)}",
            )
        if not bool(service.get("child_enabled")) and normalized_children:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce service n'autorise pas les elements lies.")
        old_status = str((existing.get("values") or {}).get("status") or "").strip().lower()
        new_status = str((merged_values or {}).get("status") or "").strip().lower()
        if normalized_service_code.strip().lower() == "emails" and new_status == "a supprimer" and old_status != "a supprimer":
            if not _normalize_notification_due_at(str(payload.reminder_due_at or "")):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Date de rappel requise pour passer un Email a supprimer.",
                )
        try:
            row = saver(
                service_code=normalized_service_code,
                values=merged_values,
                children=normalized_children,
                record_id=str(record_id or ""),
                change_source="manual",
                record_history=not skip_history_changes,
                history_changed_at=str(payload.history_changed_at or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Mise a jour de la fiche impossible: {exc}") from exc
        if normalized_service_code.strip().lower() == "emails":
            if new_status == "a supprimer" and (old_status != "a supprimer" or str(payload.reminder_due_at or "").strip()):
                _sync_email_status_notification_task(
                    api,
                    service_code=normalized_service_code,
                    record_id=str(row.get("id") or record_id),
                    values=dict(row.get("values") or merged_values),
                    reminder_due_at=str(payload.reminder_due_at or ""),
                )
            elif old_status == "a supprimer" and new_status != "a supprimer":
                _sync_email_status_notification_task(
                    api,
                    service_code=normalized_service_code,
                    record_id=str(row.get("id") or record_id),
                    values=dict(row.get("values") or merged_values),
                    reminder_due_at="",
                )
        return CustomServiceRecordResponse(
            **_custom_service_record_response_payload(
                row,
                credentials_enabled=credentials_enabled,
            )
        )

    @app.post("/admin/custom-services/{service_code}/records/{record_id}/credentials/reveal", response_model=DeviceCredentialRevealResponse)
    def reveal_admin_custom_service_record_credentials(
        service_code: str,
        record_id: str,
        payload: DeviceCredentialRevealRequest,
        api: ApiServices = Depends(get_services),
        session=Depends(require_role_manager_role),
    ) -> DeviceCredentialRevealResponse:
        lister = getattr(api.logs, "list_custom_service_records", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des donnees service indisponible.")
        service = _get_custom_service_or_404(api, service_code)
        if not bool(service.get("credentials_enabled", False)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce service ne gere pas les mots de passe.")
        subject = str(getattr(session, "subject", "") or "").strip()
        if not api.auth.verify_user_password(subject, str(payload.session_password or "")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mot de passe de session invalide.")
        rows = lister(service_code=str(service.get("code") or service_code))
        row = next((item for item in list(rows or []) if str(item.get("id") or "") == str(record_id or "")), None)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiche introuvable.")
        values = dict(row.get("values") or {})
        password = str(values.get(CUSTOM_SERVICE_CREDENTIAL_PASSWORD_KEY) or values.get("password") or "")
        if not password:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun mot de passe stocke pour cette fiche.")
        return DeviceCredentialRevealResponse(
            device_login=str(values.get(CUSTOM_SERVICE_CREDENTIAL_LOGIN_KEY) or values.get("login") or ""),
            device_password=password,
        )

    @app.get("/admin/custom-services/{service_code}/records/{record_id}/history", response_model=list[CustomServiceRecordHistoryResponse])
    def list_admin_custom_service_record_history(
        service_code: str,
        record_id: str,
        field_key: str = Query(default=""),
        limit: int = Query(default=200, ge=1, le=1000),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> list[CustomServiceRecordHistoryResponse]:
        lister = getattr(api.logs, "list_custom_service_record_history", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Historique des fiches indisponible.")
        service = _get_custom_service_or_404(api, service_code)
        rows = lister(
            service_code=str(service.get("code") or service_code),
            record_id=str(record_id or ""),
            field_key=str(field_key or ""),
            limit=int(limit),
        )
        return [CustomServiceRecordHistoryResponse(**row) for row in list(rows or [])]

    @app.delete("/admin/custom-services/{service_code}/records/{record_id}", response_model=MessageResponse)
    def delete_admin_custom_service_record(
        service_code: str,
        record_id: str,
        version_token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_role_manager_role),
    ) -> MessageResponse:
        deleter = getattr(api.logs, "delete_custom_service_record", None)
        lister = getattr(api.logs, "list_custom_service_records", None)
        if not callable(deleter) or not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des donnees service indisponible.")
        service = _get_custom_service_or_404(api, service_code)
        rows = lister(service_code=str(service.get("code") or service_code))
        existing = next((row for row in rows if str(row.get("id") or "") == str(record_id or "")), None)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiche introuvable.")
        _assert_version_token(
            expected=_custom_service_record_version_token(existing),
            received=version_token,
            resource_label=f"Fiche {record_id}",
        )
        try:
            deleted = int(deleter(service_code=str(service.get("code") or service_code), record_id=str(record_id or "")) or 0)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Suppression de la fiche impossible: {exc}") from exc
        if deleted <= 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiche introuvable.")
        return MessageResponse(message="Fiche supprimee.")


def _directory_payload_value(payload: dict, *keys: str) -> str:
    for key in keys:
        value = payload.get(key) if isinstance(payload, dict) else ""
        if isinstance(value, list):
            value = value[0] if value else ""
        value = str(value or "").strip()
        if value:
            return value
    return ""


def _directory_agent_status(payload: dict) -> str:
    raw_value = _directory_payload_value(payload, "userAccountControl")
    try:
        account_control = int(str(raw_value or "0").strip())
    except ValueError:
        account_control = 0
    return "Desactive" if account_control & 2 else "Actif"


def _directory_dn_parts(dn: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escaped = False
    for char in str(dn or ""):
        if char == "\\" and not escaped:
            escaped = True
            current.append(char)
            continue
        if char == "," and not escaped:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            escaped = False
            continue
        current.append(char)
        escaped = False
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def _directory_dn_component_value(dn: str, prefix: str) -> str:
    wanted = str(prefix or "").strip().upper()
    for part in _directory_dn_parts(dn):
        if part.upper().startswith(f"{wanted}="):
            return part.split("=", 1)[1].replace("\\,", ",").strip()
    return ""


def _directory_dn_ou_values(dn: str) -> list[str]:
    values = []
    for part in _directory_dn_parts(dn):
        if part.upper().startswith("OU="):
            value = part.split("=", 1)[1].replace("\\,", ",").strip()
            if value:
                values.append(value)
    return values


def _directory_service_path_parts(dn: str) -> list[str]:
    return list(reversed(_directory_dn_ou_values(dn)))


def _directory_service_path_label(parts: list[str], fallback: str = "") -> str:
    return " / ".join(str(part or "").strip() for part in parts if str(part or "").strip()) or str(fallback or "").strip()


def _directory_shared_path_prefix_length(paths: list[list[str]]) -> int:
    non_empty_paths = [path for path in paths if path]
    if not non_empty_paths:
        return 0
    prefix_length = 0
    for values in zip(*non_empty_paths):
        if len({str(value).casefold() for value in values}) != 1:
            break
        prefix_length += 1
    return prefix_length


def _directory_normalized_dn(dn: str) -> str:
    return ",".join(part.strip().lower() for part in _directory_dn_parts(dn))


def _directory_agent_service_dns(dn: str) -> list[str]:
    parts = _directory_dn_parts(dn)
    output = []
    for index, part in enumerate(parts):
        if part.upper().startswith("OU="):
            service_dn = ",".join(parts[index:])
            if service_dn:
                output.append(service_dn)
    return output


TECHNICAL_ACTIVE_DIRECTORY_OU_NAMES = frozenset(
    {
        "computer",
        "computers",
        "ordinateur",
        "ordinateurs",
        "profil",
        "profils",
        "profile",
        "profiles",
        "pret",
        "prets",
        "utilisateur",
        "utilisateurs",
        "user",
        "users",
    }
)


def _directory_normalized_label(value: str) -> str:
    return (
        unicodedata.normalize("NFD", str(value or ""))
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
    )


def _directory_business_agent_service_dns(dn: str) -> list[str]:
    parts = _directory_dn_parts(dn)
    output = []
    for index, part in enumerate(parts):
        if not part.upper().startswith("OU="):
            continue
        ou_name = part.split("=", 1)[1].replace("\\,", ",").strip()
        if _directory_normalized_label(ou_name) in TECHNICAL_ACTIVE_DIRECTORY_OU_NAMES:
            continue
        service_dn = ",".join(parts[index:])
        if service_dn:
            output.append(service_dn)
    return output


def _directory_record_primary_label(record: dict) -> str:
    values = record.get("values") if isinstance(record.get("values"), dict) else {}
    service_code = str(record.get("service_code") or "").strip().lower()
    if service_code in {"utilisateurs", "users", "agents"}:
        keys = ("display_name", "label", "name", "login", "mail", "email", "address")
    elif service_code in {"emails", "mails"}:
        keys = ("address", "email", "mail", "name", "label", "code")
    elif service_code in {"services", "service", "ou", "ous"}:
        keys = ("path_label", "name", "label", "code")
    else:
        keys = ("name", "label", "code", "display_name", "login", "address", "email", "mail")
    for key in keys:
        value = str(values.get(key) if key in values else record.get(key, "")).strip()
        if value:
            return value
    return str(record.get("id") or "").strip()


def _directory_custom_record_label(service: dict, record: dict) -> str:
    values = record.get("values") if isinstance(record.get("values"), dict) else {}
    fields = sorted(
        [item for item in list(service.get("fields") or []) if str(item.get("field_key") or "").strip()],
        key=lambda item: (int(item.get("sort_order") or 0), str(item.get("field_key") or "")),
    )
    for field in fields:
        value = str(values.get(str(field.get("field_key") or "").strip()) or "").strip()
        if value:
            return value
    return _directory_record_primary_label(record)


def _directory_agent_inherited_module_sections(api: ApiServices, rows: list[dict]) -> None:
    """Attach materialized direct and Service-inherited no-code links to Agents."""
    service_lister = getattr(api.logs, "list_custom_services", None)
    record_lister = getattr(api.logs, "list_custom_service_records", None)
    relation_lister = getattr(api.logs, "list_custom_service_relations", None)
    batch_link_lister = getattr(api.logs, "list_custom_service_relation_links_for_record_ids", None)
    if not rows or not all(callable(item) for item in (service_lister, record_lister, relation_lister, batch_link_lister)):
        return
    agent_by_id = {str(row.get("id") or "").strip(): row for row in rows if str(row.get("id") or "").strip()}
    agent_ids_by_service: dict[str, set[str]] = {}
    for row in rows:
        row["inherited_module_sections"] = []
        agent_id = str(row.get("id") or "").strip()
        if not agent_id:
            continue
        for service_id in {
            str(value or "").strip()
            for value in list(row.get("linked_service_ids") or [])
            if str(value or "").strip()
        }:
            agent_ids_by_service.setdefault(service_id, set()).add(agent_id)
    for raw_service in list(service_lister() or []):
        service = dict(raw_service or {})
        module_code = str(service.get("code") or "").strip().lower()
        if not module_code or module_code in {"utilisateurs", "services"} or not bool(service.get("is_active", True)):
            continue
        try:
            config = json.loads(str(service.get("treeview_config") or "") or "{}")
        except (TypeError, ValueError):
            config = {}
        inheritance = config.get("relationship_inheritance") if isinstance(config, dict) else {}
        try:
            inheritance_relation_id = int((inheritance or {}).get("relation_id") or 0)
        except (TypeError, ValueError):
            inheritance_relation_id = 0
        if not isinstance(inheritance, dict) or not bool(inheritance.get("enabled")) or inheritance_relation_id <= 0:
            continue
        relations = [dict(item or {}) for item in list(relation_lister(service_code=module_code) or [])]
        service_relation = next((item for item in relations if (
            int(item.get("id") or 0) == inheritance_relation_id
            and bool(item.get("is_active", True))
            and {str(item.get("source_service_code") or "").strip().lower(), str(item.get("target_service_code") or "").strip().lower()}
            == {module_code, "services"}
        )), None)
        if service_relation is None:
            continue
        records = [dict(item or {}) for item in list(record_lister(service_code=module_code) or [])]
        record_ids = [str(item.get("id") or "").strip() for item in records if str(item.get("id") or "").strip()]
        if not record_ids:
            continue
        service_links = batch_link_lister(
            service_code=module_code,
            record_ids=record_ids,
            relation_id=inheritance_relation_id,
        ) or {}
        direct_agent_relations = [item for item in relations if (
            bool(item.get("is_active", True))
            and {str(item.get("source_service_code") or "").strip().lower(), str(item.get("target_service_code") or "").strip().lower()}
            == {module_code, "utilisateurs"}
        )]
        direct_links_by_relation = [
            batch_link_lister(
                service_code=module_code,
                record_ids=record_ids,
                relation_id=int(relation.get("id") or 0),
            ) or {}
            for relation in direct_agent_relations
        ]
        records_by_agent: dict[str, dict[str, dict]] = {agent_id: {} for agent_id in agent_by_id}
        for record in records:
            record_id = str(record.get("id") or "").strip()
            if not record_id:
                continue
            linked_service_ids = {
                str((link.get("linked_record") or {}).get("id") or "").strip()
                for link in list(service_links.get(record_id, []) or [])
                if isinstance(link, dict)
            }
            linked_service_ids.discard("")
            direct_agent_ids = {
                str((link.get("linked_record") or {}).get("id") or "").strip()
                for links_by_record in direct_links_by_relation
                for link in list(links_by_record.get(record_id, []) or [])
                if isinstance(link, dict)
            }
            direct_agent_ids.discard("")
            linked_agent_ids = set(direct_agent_ids)
            for service_id in linked_service_ids:
                linked_agent_ids.update(agent_ids_by_service.get(service_id, set()))
            record_summary = {
                "id": record_id,
                "label": _directory_custom_record_label(service, record),
            }
            for agent_id in linked_agent_ids:
                if agent_id in records_by_agent:
                    records_by_agent[agent_id][record_id] = record_summary
        module_label = str(service.get("label") or module_code).strip() or module_code
        for agent_id, linked_records in records_by_agent.items():
            if linked_records:
                agent_by_id[agent_id]["inherited_module_sections"].append({
                    "service_code": module_code,
                    "label": module_label,
                    "records": list(linked_records.values()),
                })


def _directory_normalized_email(value: str) -> str:
    raw = str(value or "").strip().lower()
    match = re.search(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", raw)
    return match.group(0) if match else raw


def _directory_payload_email_addresses(payload: dict) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    def append_email(value: object) -> None:
        email = _directory_normalized_email(str(value or ""))
        if not email or "@" not in email or email in seen:
            return
        seen.add(email)
        output.append(email)

    append_email(_directory_payload_value(payload, "mail"))
    proxy_values = payload.get("proxyAddresses") if isinstance(payload, dict) else []
    for item in proxy_values if isinstance(proxy_values, list) else [proxy_values]:
        raw = str(item or "").strip()
        _prefix, _separator, value = raw.partition(":")
        append_email(value or raw)
    other_values = payload.get("otherMailbox") if isinstance(payload, dict) else []
    for item in other_values if isinstance(other_values, list) else [other_values]:
        append_email(item)
    return output


def _directory_email_record_address(values: dict) -> str:
    for key in ("address", "email", "mail", "device_login", "alias"):
        value = _directory_normalized_email(str((values or {}).get(key) or ""))
        if "@" in value:
            return value
    return ""


def _directory_agent_mail_index(api: ApiServices, *, limit: int = 5000) -> dict[str, str]:
    entries = api.logs.list_sync_source_cache_entries(
        source_kind="active_directory",
        target_kind="users",
        limit=max(1, min(int(limit or 5000), 5000)),
    )
    output: dict[str, str] = {}
    for entry in list(entries or []):
        payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
        agent_id = str(entry.get("external_id") or entry.get("id") or "").strip()
        email = _directory_normalized_email(_directory_payload_value(payload, "mail", "userPrincipalName"))
        if agent_id and email and "@" in email:
            output[email] = agent_id
    return output


def _directory_email_agent_relation_id(api: ApiServices) -> int:
    lister = getattr(api.logs, "list_custom_service_relations", None)
    if not callable(lister):
        return 0
    for relation in list(lister(service_code="utilisateurs") or []):
        if (
            str(relation.get("source_service_code") or "").strip().lower() == "utilisateurs"
            and str(relation.get("target_service_code") or "").strip().lower() == "emails"
            and str(relation.get("cardinality") or "").strip().lower() == "many_to_many"
            and bool(relation.get("is_active", True))
        ):
            return int(relation.get("id") or 0)
    return 0


def _link_email_record_to_matching_agent(api: ApiServices, *, email_record: dict, agent_by_mail: dict[str, str] | None = None, relation_id: int = 0) -> str:
    values = email_record.get("values") if isinstance(email_record.get("values"), dict) else {}
    email = _directory_email_record_address(values)
    if not email:
        return ""
    agent_index = agent_by_mail if agent_by_mail is not None else _directory_agent_mail_index(api)
    agent_id = str((agent_index or {}).get(email) or "").strip()
    if not agent_id:
        return ""
    resolved_relation_id = int(relation_id or 0) or _directory_email_agent_relation_id(api)
    if resolved_relation_id <= 0:
        return ""
    saver = getattr(api.logs, "save_custom_service_record_relation_link", None)
    if not callable(saver):
        return ""
    try:
        saver(
            service_code="utilisateurs",
            record_id=agent_id,
            relation_id=resolved_relation_id,
            linked_record_id=str(email_record.get("id") or "").strip(),
        )
    except Exception:
        return ""
    return agent_id


def _enrich_email_records_with_agent_services(api: ApiServices, rows: list[dict]) -> list[dict]:
    if not rows:
        return rows
    relation_id = _directory_email_agent_relation_id(api)
    link_lister = getattr(api.logs, "list_custom_service_record_relation_links", None)
    if relation_id <= 0 or not callable(link_lister):
        return rows
    for row in rows:
        values = dict(row.get("values") or {})
        service_labels: list[str] = []
        agent_labels: list[str] = []
        try:
            links = list(
                link_lister(
                    service_code="emails",
                    record_id=str(row.get("id") or ""),
                    relation_id=relation_id,
                )
                or []
            )
        except Exception:
            links = []
        for link in links:
            linked_record = link.get("linked_record") if isinstance(link, dict) else {}
            linked_values = linked_record.get("values") if isinstance(linked_record, dict) and isinstance(linked_record.get("values"), dict) else {}
            agent_label = _directory_record_primary_label(linked_record if isinstance(linked_record, dict) else {})
            service_label = str(linked_values.get("service") or "").strip()
            if not service_label:
                agent_dn = str(linked_values.get("distinguished_name") or "").strip()
                business_dns = _directory_business_agent_service_dns(agent_dn)
                service_label = _directory_dn_component_value(business_dns[0], "OU") if business_dns else ""
            if agent_label and agent_label not in agent_labels:
                agent_labels.append(agent_label)
            if service_label and service_label not in service_labels:
                service_labels.append(service_label)
        values["agents_lies"] = ", ".join(agent_labels)
        values["services_deduits"] = ", ".join(service_labels) or str(values.get("service_reference") or "").strip() or "Non affecte"
        row["values"] = values
    return rows


def _register_directory_routes(
    app: FastAPI,
    get_services,
    require_directory_agents_module,
    require_directory_services_module,
) -> None:
    @app.get("/directory/agents")
    def list_directory_agents(
        limit: int = 500,
        record_id: str = "",
        api: ApiServices = Depends(get_services),
        _session=Depends(require_directory_agents_module),
    ) -> dict:
        normalized_record_id = str(record_id or "").strip()
        if normalized_record_id:
            entries = api.logs.list_sync_source_cache_entries_by_external_ids(
                source_kind="active_directory",
                target_kind="users",
                external_ids=[normalized_record_id],
            )
        else:
            entries = api.logs.list_sync_source_cache_entries(
                source_kind="active_directory",
                target_kind="users",
                limit=max(1, min(int(limit or 500), 5000)),
            )
        rows = []
        for entry in entries:
            payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
            distinguished_name = _directory_payload_value(payload, "distinguishedName", "dn")
            cn = _directory_dn_component_value(distinguished_name, "CN")
            identity = (
                cn
                or _directory_payload_value(payload, "displayName", "cn", "name")
                or str(entry.get("display_label") or "")
            )
            rows.append(
                {
                    "id": str(entry.get("external_id") or entry.get("id") or ""),
                    "label": identity,
                    "identity": identity,
                    "cn": cn,
                    "login": _directory_payload_value(payload, "sAMAccountName", "userPrincipalName", "cn"),
                    "status": _directory_agent_status(payload),
                    "mail": _directory_payload_value(payload, "mail", "userPrincipalName"),
                    "ad_emails": _directory_payload_email_addresses(payload),
                    "linked_services": "",
                    "linked_services_source": "",
                    "linked_service_ids": [],
                    "linked_emails": "",
                    "linked_email_ids": [],
                    "ad_email_ids": [],
                    "distinguished_name": distinguished_name,
                    "synced_at": str(entry.get("synced_at") or ""),
                }
            )
        relation_lister = getattr(api.logs, "list_custom_service_relations", None)
        batch_link_lister = getattr(api.logs, "list_custom_service_relation_links_for_record_ids", None)
        if callable(relation_lister) and callable(batch_link_lister) and rows:
            try:
                relation_by_target = {}
                for item in list(relation_lister(service_code="utilisateurs") or []):
                    if (
                        str(item.get("source_service_code") or "").strip().lower() == "utilisateurs"
                        and str(item.get("cardinality") or "").strip().lower() == "many_to_many"
                        and bool(item.get("is_active", True))
                    ):
                        relation_by_target[str(item.get("target_service_code") or "").strip().lower()] = item
                for target_code, label_key, id_key, source_key in (
                    ("services", "linked_services", "linked_service_ids", "linked_services_source"),
                    ("emails", "linked_emails", "linked_email_ids", ""),
                ):
                    relation = relation_by_target.get(target_code)
                    if not relation:
                        continue
                    links_by_agent = batch_link_lister(
                        service_code="utilisateurs",
                        record_ids=[str(row.get("id") or "") for row in rows],
                        relation_id=int(relation.get("id") or 0),
                    )
                    for row in rows:
                        links = list(links_by_agent.get(str(row.get("id") or ""), []) or [])
                        labels = [
                            _directory_record_primary_label(link.get("linked_record") if isinstance(link, dict) else {})
                            for link in links
                        ]
                        ids = [
                            str((link.get("linked_record") or {}).get("id") or "").strip()
                            for link in links
                            if isinstance(link, dict)
                        ]
                        explicit_labels = [label for label in labels if label]
                        explicit_ids = [item for item in ids if item]
                        if explicit_labels:
                            if target_code == "services":
                                row[label_key] = ", ".join(explicit_labels[:3])
                                row[id_key] = explicit_ids[:3]
                                row[source_key] = "relation"
                            else:
                                protected_emails = {
                                    _directory_normalized_email(item)
                                    for item in list(row.get("ad_emails") or [])
                                    if _directory_normalized_email(item)
                                }
                                primary_email = _directory_normalized_email(str(row.get("mail") or ""))
                                protected_ids: list[str] = []
                                secondary_labels: list[str] = []
                                secondary_ids: list[str] = []
                                for link in links:
                                    linked_record = link.get("linked_record") if isinstance(link, dict) else {}
                                    linked_values = linked_record.get("values") if isinstance(linked_record, dict) and isinstance(linked_record.get("values"), dict) else {}
                                    linked_id = str(linked_record.get("id") if isinstance(linked_record, dict) else "").strip()
                                    linked_email = _directory_email_record_address(linked_values)
                                    if linked_id and linked_email in protected_emails and linked_id not in protected_ids:
                                        protected_ids.append(linked_id)
                                    if linked_email and primary_email and linked_email == primary_email:
                                        continue
                                    label = _directory_record_primary_label(linked_record if isinstance(linked_record, dict) else {})
                                    if label and label not in secondary_labels:
                                        secondary_labels.append(label)
                                        if linked_id:
                                            secondary_ids.append(linked_id)
                                row[label_key] = ", ".join(secondary_labels)
                                row[id_key] = secondary_ids
                                row["ad_email_ids"] = protected_ids
                            if source_key:
                                row[source_key] = "relation"
            except Exception:
                pass
        try:
            _directory_agent_inherited_module_sections(api, rows)
        except Exception:
            for row in rows:
                row.setdefault("inherited_module_sections", [])
        return {"items": rows, "total": len(rows)}

    @app.get("/directory/services")
    def list_directory_services(
        limit: int = 500,
        record_id: str = "",
        api: ApiServices = Depends(get_services),
        _session=Depends(require_directory_services_module),
    ) -> dict:
        normalized_record_id = str(record_id or "").strip()
        if normalized_record_id:
            entries = api.logs.list_sync_source_cache_entries_by_external_ids(
                source_kind="active_directory",
                target_kind="organizational_units",
                external_ids=[normalized_record_id],
            )
        else:
            entries = api.logs.list_sync_source_cache_entries(
                source_kind="active_directory",
                target_kind="organizational_units",
                limit=max(1, min(int(limit or 500), 5000)),
            )
        rows = []
        for entry in entries:
            payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
            label = str(entry.get("display_label") or "")
            path_parts = _directory_service_path_parts(
                _directory_payload_value(payload, "distinguishedName", "dn"),
            )
            rows.append(
                {
                    "id": str(entry.get("external_id") or entry.get("id") or ""),
                    "label": label,
                    "path_parts": path_parts,
                    "path_label": _directory_service_path_label(path_parts, label),
                    "code": _directory_payload_value(payload, "ou", "name", "cn"),
                    "description": _directory_payload_value(payload, "description"),
                    "manager": _directory_payload_value(payload, "managedBy"),
                    "distinguished_name": _directory_payload_value(payload, "distinguishedName", "dn"),
                    "synced_at": str(entry.get("synced_at") or ""),
                    "source": "active_directory",
                    "is_manual": False,
                }
            )
        manual_lister = getattr(api.logs, "list_manual_organization_units", None)
        if callable(manual_lister):
            try:
                for manual in list(manual_lister() or []):
                    rows.append(
                        {
                            "id": str(manual.get("id") or ""),
                            "label": str(manual.get("name") or manual.get("code") or "Service"),
                            "path_parts": [],
                            "path_label": f"Manuel / {str(manual.get('name') or manual.get('code') or 'Service')}",
                            "code": str(manual.get("code") or ""),
                            "description": str(manual.get("description") or ""),
                            "manager": str(manual.get("manager") or ""),
                            "distinguished_name": str(manual.get("distinguished_name") or ""),
                            "synced_at": str(manual.get("updated_at") or ""),
                            "source": "manual",
                            "is_manual": True,
                        }
                    )
            except Exception:
                pass
        shared_path_prefix_length = _directory_shared_path_prefix_length([
            list(row.get("path_parts") or [])
            for row in rows
            if not bool(row.get("is_manual"))
        ])
        for row in rows:
            path_parts = list(row.pop("path_parts", []) or [])
            if path_parts and not bool(row.get("is_manual")):
                visible_parts = path_parts[shared_path_prefix_length:] or path_parts[-1:]
                row["path_label"] = _directory_service_path_label(visible_parts, str(row.get("label") or ""))
        relation_lister = getattr(api.logs, "list_custom_service_relations", None)
        batch_link_lister = getattr(api.logs, "list_custom_service_relation_links_for_record_ids", None)
        if callable(relation_lister) and callable(batch_link_lister) and rows:
            try:
                agent_relation = next(
                    (
                        relation
                        for relation in list(relation_lister(service_code="services") or [])
                        if bool(relation.get("is_active", True))
                        and {
                            str(relation.get("source_service_code") or "").strip().lower(),
                            str(relation.get("target_service_code") or "").strip().lower(),
                        } == {"services", "utilisateurs"}
                    ),
                    None,
                )
                if agent_relation:
                    links_by_service = batch_link_lister(
                        service_code="services",
                        record_ids=[str(row.get("id") or "") for row in rows],
                        relation_id=int(agent_relation.get("id") or 0),
                    )
                    for row in rows:
                        links = list(links_by_service.get(str(row.get("id") or ""), []) or [])
                        row["linked_agents"] = ", ".join(
                            label for label in (
                                _directory_record_primary_label(link.get("linked_record") if isinstance(link, dict) else {})
                                for link in links
                            ) if label
                        )
                        row["linked_agent_ids"] = [
                            str((link.get("linked_record") or {}).get("id") or "").strip()
                            for link in links
                            if isinstance(link, dict) and str((link.get("linked_record") or {}).get("id") or "").strip()
                        ]
            except Exception:
                pass
        return {"items": rows, "total": len(rows)}

    @app.post("/directory/services/manual")
    def create_manual_directory_service(
        payload: CustomServiceRecordUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_directory_services_module),
    ) -> dict:
        saver = getattr(api.logs, "save_manual_organization_unit", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des Services indisponible.")
        values = {str(key or "").strip(): str(value or "").strip() for key, value in dict(payload.values or {}).items()}
        if not values.get("name"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le nom du Service est obligatoire.")
        try:
            return saver(values=values)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation du Service impossible: {exc}") from exc

    @app.put("/directory/services/manual/{record_id}")
    def update_manual_directory_service(
        record_id: str,
        payload: CustomServiceRecordUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_directory_services_module),
    ) -> dict:
        lister = getattr(api.logs, "get_manual_organization_unit", None)
        saver = getattr(api.logs, "save_manual_organization_unit", None)
        if not callable(lister) or not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Gestion des Services indisponible.")
        existing = lister(record_id=str(record_id or ""))
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service manuel introuvable.")
        values = {
            "name": str(existing.get("name") or ""),
            "code": str(existing.get("code") or ""),
            "description": str(existing.get("description") or ""),
            "manager": str(existing.get("manager") or ""),
            **{str(key or "").strip(): str(value or "").strip() for key, value in dict(payload.values or {}).items()},
        }
        if not values.get("name"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le nom du Service est obligatoire.")
        try:
            return saver(values=values, record_id=str(record_id or ""))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Mise a jour du Service impossible: {exc}") from exc


def _register_settings_routes(app: FastAPI, get_services, require_admin_module) -> None:
    @app.get("/dashboard-preferences/{scope}", response_model=DashboardPreferencesResponse)
    def get_dashboard_preferences(
        scope: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> DashboardPreferencesResponse:
        lister = getattr(api.logs, "list_dashboard_preferences", None)
        if not callable(lister):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Preferences dashboard indisponibles sans stockage relationnel.",
            )
        normalized_scope = _normalize_dashboard_scope(scope)
        return _build_dashboard_preferences_response(normalized_scope, lister(scope=normalized_scope))

    @app.put("/dashboard-preferences/{scope}", response_model=DashboardPreferencesResponse)
    def update_dashboard_preferences(
        scope: str,
        payload: DashboardPreferencesUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> DashboardPreferencesResponse:
        saver = getattr(api.logs, "save_dashboard_preferences", None)
        if not callable(saver):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Preferences dashboard indisponibles sans stockage relationnel.",
            )
        normalized_scope = _normalize_dashboard_scope(scope)
        rows = saver(
            scope=normalized_scope,
            cards_order=_normalize_dashboard_card_ids(payload.cards_order),
            hidden_cards=_normalize_dashboard_card_ids(payload.hidden_cards),
            pinned_cards=_normalize_dashboard_card_ids(payload.pinned_cards),
        )
        return _build_dashboard_preferences_response(normalized_scope, rows)

    @app.get("/settings", response_model=SettingsResponse)
    def get_settings(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> SettingsResponse:
        payload = _serialize_settings(api.settings_service.get())
        payload["version_token"] = _settings_version_token(payload)
        return SettingsResponse(**payload)

    @app.put("/settings", response_model=SettingsResponse)
    def update_settings(
        payload: SettingsUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> SettingsResponse:
        current_settings = api.settings_service.get()
        current_payload = _serialize_settings(current_settings)
        _assert_version_token(
            expected=_settings_version_token(current_payload),
            received=str(payload.version_token or ""),
            resource_label="Parametres",
        )
        payload_data = payload.model_dump()
        payload_data.pop("version_token", None)
        smtp_password = str(payload_data.pop("smtp_password", "") or "")
        config_smb_password = str(payload_data.pop("config_smb_password", "") or "")
        active_directory_bind_password = str(payload_data.pop("active_directory_bind_password", "") or "")
        reverse_proxy = _normalize_reverse_proxy_type(payload_data.get("web_server_reverse_proxy_type"))
        public_url = str(payload_data.get("web_server_public_url", "") or "").strip()
        if reverse_proxy != "aucun" and not public_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="URL publique obligatoire quand un reverse proxy est active.",
            )
        payload_data["web_server_reverse_proxy_type"] = reverse_proxy
        payload_data["web_server_use_public_url"] = reverse_proxy != "aucun"
        payload_data["web_server_public_url"] = public_url
        payload_data["web_server_port"] = max(1, int(payload_data.get("web_server_port", 8000) or 8000))
        web_runtime_changed = _web_server_runtime_changed(
            current_settings=current_settings,
            next_payload=payload_data,
            reverse_proxy=reverse_proxy,
            public_url=public_url,
        )
        if web_runtime_changed and _reverse_proxy_runtime_changed(
            current_settings=current_settings,
            reverse_proxy=reverse_proxy,
            public_url=public_url,
            upstream_port=int(payload_data["web_server_port"]),
        ):
            resolved_public_url = _sync_reverse_proxy_runtime(
                reverse_proxy=reverse_proxy,
                public_url=public_url,
                upstream_port=int(payload_data["web_server_port"]),
            )
        else:
            resolved_public_url = public_url
        payload_data["web_server_public_url"] = str(resolved_public_url or "").strip() or public_url
        if not str(payload_data.get("active_directory_ca_certificate_file_id") or "").strip():
            payload_data["active_directory_ca_certificate_file_id"] = current_settings.active_directory_ca_certificate_file_id
        if not str(payload_data.get("active_directory_ca_certificate_path") or "").strip():
            payload_data["active_directory_ca_certificate_path"] = current_settings.active_directory_ca_certificate_path
        settings = NotificationSettings(**payload_data)
        settings.password = smtp_password if smtp_password.strip() else current_settings.password
        settings.github_token = current_settings.github_token
        settings.config_smb_password = config_smb_password if config_smb_password.strip() else current_settings.config_smb_password
        settings.active_directory_bind_password = active_directory_bind_password if active_directory_bind_password else current_settings.active_directory_bind_password
        api.settings_service.save(settings)
        api.monitoring.apply_notification_settings(settings)
        api.auth.set_session_ttl_seconds(settings.web_session_ttl_seconds)
        if web_runtime_changed:
            save_hebergement_web_config(
                HebergementWebConfig(
                    hote_ecoute=str(settings.web_server_host or "0.0.0.0").strip() or "0.0.0.0",
                    port_ecoute=max(1, int(settings.web_server_port or 8000)),
                    demarrage_auto_service=bool(settings.web_server_autostart),
                    utiliser_url_publique_reverse_proxy=bool(settings.web_server_use_public_url),
                    url_publique=str(settings.web_server_public_url or "").strip(),
                    reverse_proxy_actif=reverse_proxy != "aucun",
                    reverse_proxy_type=reverse_proxy,
                )
            )
        updated_payload = _serialize_settings(api.settings_service.get())
        updated_payload["version_token"] = _settings_version_token(updated_payload)
        return SettingsResponse(**updated_payload)

    @app.post("/settings/active-directory/test", response_model=MessageResponse)
    def test_active_directory_settings(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> MessageResponse:
        try:
            message = ActiveDirectorySyncEngine().test_connection(api.settings_service.get())
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Test Active Directory echoue: {exc}") from exc
        return MessageResponse(message=message)

    @app.post("/settings/active-directory/sync-now", response_model=MessageResponse)
    def run_active_directory_sync_now(
        payload: ActiveDirectorySyncNowRequest | None = None,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> MessageResponse:
        sync_mode = _normalize_active_directory_sync_now_mode((payload or ActiveDirectorySyncNowRequest()).mode)
        try:
            reset_summary = {}
            resetter = getattr(api.logs, "reset_active_directory_derived_data", None)
            if callable(resetter):
                reset_summary = resetter(
                    delete_agent_service_links=True,
                    delete_agent_email_links=True,
                    delete_email_records=sync_mode == "reset_ad",
                    delete_cache_entries=sync_mode in {"force_rebuild", "reset_ad"},
                ) or {}
            user_count = _refresh_active_directory_cache_for_target(api, "users")
            ou_count = _refresh_active_directory_cache_for_target(api, "organizational_units")
            email_summary = {}
            if bool(getattr(api.settings_service.get(), "active_directory_sync_email_accounts", False)):
                email_syncer = getattr(api.logs, "sync_active_directory_email_accounts", None)
                if callable(email_syncer):
                    email_summary = email_syncer() or {}
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Synchronisation Active Directory echouee: {exc}",
            ) from exc
        return MessageResponse(
            message=(
                "Cache Active Directory mis a jour: "
                f"{user_count} utilisateur(s), {ou_count} OU/service(s). "
                + (
                    "Reconstruction forcee appliquee. "
                    if sync_mode == "force_rebuild"
                    else (
                        f"Donnees AD reinitialisees: {int(reset_summary.get('deleted_cache_entries') or 0)} entree(s) cache, "
                        f"{int(reset_summary.get('deleted_email_records') or 0)} compte(s) Email AD, "
                        f"{int(reset_summary.get('deleted_agent_service_links') or 0) + int(reset_summary.get('deleted_agent_email_links') or 0)} lien(s) AD. "
                        if sync_mode == "reset_ad"
                        else ""
                    )
                )
                + (
                    f"{int(email_summary.get('emails') or 0)} compte(s) Email synchronise(s), "
                    f"{int(email_summary.get('links') or 0)} lien(s) Agent/Email. "
                    if email_summary
                    else ""
                )
                +
                "Les modules peuvent maintenant utiliser ce tampon local."
            )
        )

    @app.get("/settings/active-directory/certificate", response_model=ActiveDirectoryCertificateResponse)
    def get_active_directory_certificate(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> ActiveDirectoryCertificateResponse:
        settings = api.settings_service.get()
        linked_file = api.linked_files.get_file(str(settings.active_directory_ca_certificate_file_id or ""))
        return ActiveDirectoryCertificateResponse(
            filename=str(linked_file.filename if linked_file else ""),
            imported=bool(linked_file and Path(linked_file.stored_path).is_file()),
        )

    @app.post("/settings/active-directory/certificate", response_model=ActiveDirectoryCertificateResponse)
    def import_active_directory_certificate(
        payload: ActiveDirectoryCertificateImportRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> ActiveDirectoryCertificateResponse:
        raw_bytes = _decode_base64_payload(content_base64=payload.content_base64)
        try:
            pem = (
                raw_bytes.decode("ascii")
                if b"-----BEGIN CERTIFICATE-----" in raw_bytes
                else ssl.DER_cert_to_PEM_cert(raw_bytes)
            )
            ssl.create_default_context().load_verify_locations(cadata=pem)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Certificat CA invalide: {exc}") from exc
        previous = api.settings_service.get()
        stored = api.linked_files.store_bytes(
            owner_kind="sync_source",
            owner_id="active_directory",
            module_code="platform",
            category="active_directory_ca",
            filename=Path(str(payload.filename or "active-directory-ca.pem")).with_suffix(".pem").name,
            content=pem.encode("ascii"),
            detail="Certificat d'autorite pour la synchronisation Active Directory",
        )
        previous_id = str(previous.active_directory_ca_certificate_file_id or "")
        previous.active_directory_ca_certificate_file_id = stored.id
        previous.active_directory_ca_certificate_path = stored.stored_path
        api.settings_service.save(previous)
        if previous_id and previous_id != stored.id:
            api.linked_files.delete_file(previous_id, delete_physical_file=True)
        return ActiveDirectoryCertificateResponse(filename=stored.filename, imported=True)

    @app.get("/sync/active-directory/profiles", response_model=ActiveDirectorySyncProfileListResponse)
    def list_active_directory_sync_profiles(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> ActiveDirectorySyncProfileListResponse:
        profiles = [
            _active_directory_sync_profile_response(profile)
            for profile in api.logs.list_sync_source_profiles(source_kind="active_directory")
        ]
        return ActiveDirectorySyncProfileListResponse(
            profiles=profiles,
            available_attributes=ACTIVE_DIRECTORY_SYNC_AVAILABLE_ATTRIBUTES,
        )

    @app.post("/sync/active-directory/profiles", response_model=ActiveDirectorySyncProfile)
    def save_active_directory_sync_profile(
        payload: ActiveDirectorySyncProfileUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> ActiveDirectorySyncProfile:
        target_kind = _normalize_active_directory_sync_target_kind(payload.target_kind)
        selected_attributes = [
            str(attribute or "").strip()
            for attribute in list(payload.selected_attributes or [])
            if str(attribute or "").strip()
        ]
        if not selected_attributes:
            selected_attributes = list(ACTIVE_DIRECTORY_SYNC_AVAILABLE_ATTRIBUTES[target_kind][:6])
        saved = api.logs.save_sync_source_profile(
            profile={
                "id": payload.id,
                "source_kind": "active_directory",
                "code": payload.code,
                "label": payload.label,
                "target_kind": target_kind,
                "search_base": payload.search_base,
                "search_filter": payload.search_filter or ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS[target_kind],
                "selected_attributes": selected_attributes,
                "options": _normalize_active_directory_profile_options(payload.options, target_kind),
                "is_active": payload.is_active,
            }
        )
        return _active_directory_sync_profile_response(saved)

    @app.delete("/sync/active-directory/profiles/{profile_id}", response_model=MessageResponse)
    def delete_active_directory_sync_profile(
        profile_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> MessageResponse:
        deleted = api.logs.delete_sync_source_profile(profile_id=profile_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil de synchronisation introuvable.")
        return MessageResponse(message="Profil de synchronisation supprime.")

    @app.post("/sync/active-directory/profiles/{profile_id}/preview", response_model=ActiveDirectorySyncProfilePreviewResponse)
    def preview_active_directory_sync_profile(
        profile_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> ActiveDirectorySyncProfilePreviewResponse:
        raw_profile = api.logs.get_sync_source_profile(profile_id=profile_id)
        if raw_profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil de synchronisation introuvable.")
        profile = _active_directory_sync_profile_response(raw_profile)
        settings = api.settings_service.get()
        attributes = list(profile.selected_attributes or ACTIVE_DIRECTORY_SYNC_AVAILABLE_ATTRIBUTES[profile.target_kind][:6])
        fetch_attributes = _active_directory_fetch_attributes_for_profile(attributes, profile.target_kind)
        try:
            entries = ActiveDirectorySyncEngine().fetch_entries(
                settings,
                search_base=_active_directory_profile_search_base(profile, settings.active_directory_base_dn),
                search_filter=profile.search_filter or ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS[profile.target_kind],
                attributes=fetch_attributes,
                limit=500,
            )
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Preview Active Directory echoue: {exc}") from exc
        entries = _filter_active_directory_entries_for_profile(entries, profile, profile.target_kind)
        rows = [
            {attribute: _json_safe_ldap_value(_ldap_entry_attribute_value(row, attribute)) for attribute in attributes}
            for row in entries[:50]
        ]
        return ActiveDirectorySyncProfilePreviewResponse(
            profile=profile,
            attributes=attributes,
            rows=rows,
            total_preview_rows=len(rows),
        )

    @app.post("/sync/active-directory/preview", response_model=ActiveDirectorySyncProfilePreviewResponse)
    def preview_active_directory_sync_profile_draft(
        payload: ActiveDirectorySyncProfileUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> ActiveDirectorySyncProfilePreviewResponse:
        target_kind = _normalize_active_directory_sync_target_kind(payload.target_kind)
        attributes = [
            str(attribute or "").strip()
            for attribute in list(payload.selected_attributes or [])
            if str(attribute or "").strip()
        ] or list(ACTIVE_DIRECTORY_SYNC_AVAILABLE_ATTRIBUTES[target_kind][:6])
        profile = ActiveDirectorySyncProfile(
            id="",
            source_kind="active_directory",
            code=str(payload.code or ""),
            label=str(payload.label or ""),
            target_kind=target_kind,
            search_base=str(payload.search_base or ""),
            search_filter=str(payload.search_filter or ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS[target_kind]),
            selected_attributes=attributes,
            options=_normalize_active_directory_profile_options(payload.options, target_kind),
            is_active=payload.is_active,
        )
        settings = api.settings_service.get()
        fetch_attributes = _active_directory_fetch_attributes_for_profile(attributes, target_kind)
        try:
            entries = ActiveDirectorySyncEngine().fetch_entries(
                settings,
                search_base=_active_directory_profile_search_base(profile, settings.active_directory_base_dn),
                search_filter=profile.search_filter or ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS[target_kind],
                attributes=fetch_attributes,
                limit=500,
            )
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Preview Active Directory echoue: {exc}") from exc
        entries = _filter_active_directory_entries_for_profile(entries, profile, target_kind)
        rows = [
            {attribute: _json_safe_ldap_value(_ldap_entry_attribute_value(row, attribute)) for attribute in attributes}
            for row in entries[:50]
        ]
        return ActiveDirectorySyncProfilePreviewResponse(
            profile=profile,
            attributes=attributes,
            rows=rows,
            total_preview_rows=len(rows),
        )

    @app.post("/sync/active-directory/cache/refresh", response_model=ActiveDirectoryCacheRefreshResponse)
    def refresh_active_directory_cache(
        payload: ActiveDirectoryCacheRefreshRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> ActiveDirectoryCacheRefreshResponse:
        target_kind = _normalize_active_directory_sync_target_kind(payload.target_kind)
        try:
            count = _refresh_active_directory_cache_for_target(api, target_kind)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Refresh cache Active Directory echoue: {exc}") from exc
        return ActiveDirectoryCacheRefreshResponse(
            target_kind=target_kind,
            refreshed=count,
            message=f"Cache Active Directory mis a jour: {count} objet(s).",
        )

    @app.get("/sync/active-directory/cache/preview", response_model=ActiveDirectoryCachePreviewResponse)
    def preview_active_directory_cache(
        target_kind: str = Query("organizational_units"),
        limit: int = Query(200, ge=1, le=1000),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> ActiveDirectoryCachePreviewResponse:
        normalized_target = _normalize_active_directory_sync_target_kind(target_kind)
        entries = api.logs.list_sync_source_cache_entries(
            source_kind="active_directory",
            target_kind=normalized_target,
            limit=limit,
        )
        attributes = ACTIVE_DIRECTORY_CACHE_ATTRIBUTES[normalized_target]
        rows = [entry.get("payload") or {} for entry in entries]
        return ActiveDirectoryCachePreviewResponse(
            target_kind=normalized_target,
            attributes=attributes,
            rows=rows,
            total_rows=len(rows),
            synced_at=api.logs.latest_sync_source_cache_timestamp(
                source_kind="active_directory",
                target_kind=normalized_target,
            ),
        )

    @app.post("/settings/notifications/test", response_model=MessageResponse)
    def test_notification_settings(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> MessageResponse:
        settings = api.settings_service.get()
        try:
            send_alert_email(
                subject="ITops - Test notification SMTP",
                body="Test SMTP valide depuis la configuration portail.",
                settings=settings,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Test SMTP echoue: {exc}",
            ) from exc
        return MessageResponse(message="Test SMTP envoye.")

    @app.get("/notifications/tasks", response_model=list[NotificationTaskResponse])
    def list_notification_tasks(
        status_filter: str = Query(default=""),
        limit: int = Query(default=500, ge=1, le=1000),
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> list[NotificationTaskResponse]:
        lister = getattr(api.logs, "list_notification_tasks", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Taches notification indisponibles.")
        rows = lister(status_filter=str(status_filter or ""), limit=int(limit))
        return [NotificationTaskResponse(**dict(row or {})) for row in list(rows or [])]

    @app.put("/notifications/tasks/{task_id}/status", response_model=NotificationTaskResponse)
    def update_notification_task_status(
        task_id: str,
        payload: NotificationTaskStatusUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> NotificationTaskResponse:
        updater = getattr(api.logs, "set_notification_task_status", None)
        if not callable(updater):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Taches notification indisponibles.")
        try:
            row = updater(task_id=str(task_id or ""), status=str(payload.status or ""))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tache notification introuvable.")
        return NotificationTaskResponse(**dict(row or {}))

    @app.get("/notifications/templates", response_model=list[NotificationTemplateResponse])
    def list_notification_templates(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> list[NotificationTemplateResponse]:
        lister = getattr(api.logs, "list_notification_templates", None)
        if not callable(lister):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Templates notification indisponibles.")
        return [NotificationTemplateResponse(**dict(row or {})) for row in list(lister(limit=1000) or [])]

    @app.post("/notifications/templates", response_model=NotificationTemplateResponse)
    def create_notification_template(
        payload: NotificationTemplateUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> NotificationTemplateResponse:
        saver = getattr(api.logs, "save_notification_template", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Templates notification indisponibles.")
        try:
            row = saver(**payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return NotificationTemplateResponse(**dict(row or {}))

    @app.put("/notifications/templates/{template_code}", response_model=NotificationTemplateResponse)
    def update_notification_template(
        template_code: str,
        payload: NotificationTemplateUpsertRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> NotificationTemplateResponse:
        saver = getattr(api.logs, "save_notification_template", None)
        if not callable(saver):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Templates notification indisponibles.")
        data = payload.model_dump()
        data["code"] = str(template_code or data.get("code") or "").strip().lower()
        try:
            row = saver(**data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return NotificationTemplateResponse(**dict(row or {}))

    @app.delete("/notifications/templates/{template_code}", response_model=MessageResponse)
    def delete_notification_template(
        template_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> MessageResponse:
        deleter = getattr(api.logs, "delete_notification_template", None)
        if not callable(deleter):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Templates notification indisponibles.")
        deleted = deleter(code=template_code)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template notification introuvable.")
        return MessageResponse(message="Template notification supprime.")

    @app.get("/settings/watermark/state", response_model=WatermarkStateResponse)
    def get_watermark_state(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> WatermarkStateResponse:
        return _build_watermark_state_response(api.settings_service.get())

    @app.post("/settings/watermark/apply", response_model=WatermarkStateResponse)
    def apply_watermark(
        payload: WatermarkApplyRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_admin_module),
    ) -> WatermarkStateResponse:
        current_settings = api.settings_service.get()
        _apply_watermark_settings(current_settings, payload)
        api.settings_service.save(current_settings)
        return _build_watermark_state_response(api.settings_service.get())


def _serialize_settings(settings: NotificationSettings) -> dict:
    data = settings.__dict__.copy()
    data.pop("password", None)
    data.pop("github_token", None)
    data.pop("config_smb_password", None)
    data.pop("active_directory_bind_password", None)
    data.pop("active_directory_ca_certificate_path", None)
    return data


ACTIVE_DIRECTORY_SYNC_AVAILABLE_ATTRIBUTES: dict[str, list[str]] = {
    "users": [
        "objectGUID",
        "sAMAccountName",
        "userPrincipalName",
        "displayName",
        "givenName",
        "sn",
        "mail",
        "proxyAddresses",
        "otherMailbox",
        "telephoneNumber",
        "mobile",
        "title",
        "department",
        "company",
        "manager",
        "memberOf",
        "distinguishedName",
        "whenChanged",
        "userAccountControl",
    ],
    "organizational_units": [
        "ou",
        "name",
        "description",
        "distinguishedName",
        "managedBy",
        "whenChanged",
    ],
}


ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS: dict[str, str] = {
    "users": "(&(objectCategory=person)(objectClass=user))",
    "organizational_units": "(objectClass=organizationalUnit)",
}

LEGACY_ACTIVE_DIRECTORY_ACTIVE_USERS_FILTER = "(&(objectCategory=person)(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"


ACTIVE_DIRECTORY_CACHE_ATTRIBUTES: dict[str, list[str]] = {
    key: list(values)
    for key, values in ACTIVE_DIRECTORY_SYNC_AVAILABLE_ATTRIBUTES.items()
}


def _refresh_active_directory_cache_for_target(api: ApiServices, target_kind: str) -> int:
    normalized_target = _normalize_active_directory_sync_target_kind(target_kind)
    settings = api.settings_service.get()
    raw_profiles = api.logs.list_sync_source_profiles(source_kind="active_directory")
    profiles = [
        _active_directory_sync_profile_response(profile)
        for profile in raw_profiles
        if _normalize_active_directory_sync_target_kind(str((profile or {}).get("target_kind") or "")) == normalized_target
        and bool((profile or {}).get("is_active", True))
    ]
    if profiles:
        entries = []
        seen = set()
        engine = ActiveDirectorySyncEngine()
        for profile in profiles:
            profile_attributes = _active_directory_fetch_attributes_for_profile(
                list(profile.selected_attributes or []),
                normalized_target,
            )
            fetch_attributes = list(dict.fromkeys([
                *ACTIVE_DIRECTORY_CACHE_ATTRIBUTES[normalized_target],
                *profile_attributes,
            ]))
            fetched = engine.fetch_entries(
                settings,
                search_base=_active_directory_profile_search_base(profile, settings.active_directory_base_dn),
                search_filter=(
                    ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS[normalized_target]
                    if normalized_target == "users" and str(profile.search_filter or "").strip() == LEGACY_ACTIVE_DIRECTORY_ACTIVE_USERS_FILTER
                    else profile.search_filter or ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS[normalized_target]
                ),
                attributes=fetch_attributes,
                limit=5000,
            )
            for entry in _filter_active_directory_entries_for_profile(fetched, profile, normalized_target):
                key = _active_directory_entry_cache_key(entry)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(entry)
    else:
        entries = ActiveDirectorySyncEngine().fetch_entries(
            settings,
            search_base=settings.active_directory_base_dn,
            search_filter=ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS[normalized_target],
            attributes=ACTIVE_DIRECTORY_CACHE_ATTRIBUTES[normalized_target],
            limit=5000,
        )
    resetter = getattr(api.logs, "reset_active_directory_derived_data", None)
    if callable(resetter) and normalized_target in {"users", "organizational_units"}:
        resetter(
            delete_agent_service_links=True,
            delete_agent_email_links=False,
            delete_email_records=False,
            delete_cache_entries=False,
        )
    refreshed = int(
        api.logs.replace_sync_source_cache_entries(
            source_kind="active_directory",
            target_kind=normalized_target,
            entries=entries,
        )
        or 0
    )
    relation_syncer = getattr(api.logs, "sync_active_directory_agent_service_links", None)
    if callable(relation_syncer) and normalized_target in {"users", "organizational_units"}:
        relation_syncer()
    return refreshed


def _normalize_active_directory_sync_now_mode(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    aliases = {
        "normal": "normal",
        "standard": "normal",
        "force": "force_rebuild",
        "forced": "force_rebuild",
        "force_rebuild": "force_rebuild",
        "rebuild": "force_rebuild",
        "reset": "reset_ad",
        "reset_ad": "reset_ad",
        "reinitialisation": "reset_ad",
    }
    return aliases.get(normalized, "normal")


def _normalize_active_directory_sync_target_kind(value: str) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "user": "users",
        "utilisateur": "users",
        "utilisateurs": "users",
        "ou": "organizational_units",
        "ous": "organizational_units",
        "organizational_unit": "organizational_units",
        "organizational-units": "organizational_units",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in ACTIVE_DIRECTORY_SYNC_AVAILABLE_ATTRIBUTES else "users"


def _active_directory_list_option(value) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = re.split(r"[\n;]+", str(value or ""))
    items: list[str] = []
    for item in raw_items:
        for part in str(item or "").split(",") if not _looks_like_distinguished_name(item) else [item]:
            normalized = str(part or "").strip()
            if normalized and normalized not in items:
                items.append(normalized)
    return items


def _looks_like_distinguished_name(value) -> bool:
    return bool(re.search(r"(^|,)\s*(OU|CN|DC)=", str(value or ""), flags=re.IGNORECASE))


def _normalize_custom_service_duplicate_value(field_key: str, value: object) -> str:
    """Normalize a stable identifier consistently for import and duplicate analysis."""
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    normalized = " ".join(normalized.split())
    stable_key = re.sub(r"[^a-z0-9]", "", str(field_key or "").casefold())
    if any(token in stable_key for token in ("serial", "serie", "srie", "inventaire", "asset", "mac")):
        if re.fullmatch(r"\d+\.0+", normalized):
            normalized = normalized.split(".", 1)[0]
        normalized = re.sub(r"[\s._:-]", "", normalized)
    return normalized


def _normalize_active_directory_profile_options(options, target_kind: str = "users") -> dict:
    normalized_target = _normalize_active_directory_sync_target_kind(target_kind)
    source = dict(options) if isinstance(options, dict) else {}
    normalized = dict(source)
    if normalized_target != "organizational_units":
        return normalized

    root_dn = str(source.get("ou_root_dn") or source.get("root_dn") or "").strip()
    if root_dn:
        normalized["ou_root_dn"] = root_dn
    else:
        normalized.pop("ou_root_dn", None)
    raw_depth = source.get("ou_max_depth", source.get("max_depth", None))
    if raw_depth is None or str(raw_depth).strip() == "":
        normalized.pop("ou_max_depth", None)
    else:
        try:
            normalized["ou_max_depth"] = max(0, min(50, int(raw_depth)))
        except (TypeError, ValueError):
            normalized.pop("ou_max_depth", None)
    excluded_names = _active_directory_list_option(source.get("excluded_ou_names", source.get("ou_excluded_names", [])))
    excluded_dns = _active_directory_list_option(source.get("excluded_ou_dns", source.get("ou_excluded_dns", [])))
    if excluded_names:
        normalized["excluded_ou_names"] = excluded_names
    else:
        normalized.pop("excluded_ou_names", None)
    if excluded_dns:
        normalized["excluded_ou_dns"] = excluded_dns
    else:
        normalized.pop("excluded_ou_dns", None)
    return normalized


def _active_directory_fetch_attributes_for_profile(attributes: list[str], target_kind: str) -> list[str]:
    values = [str(attribute or "").strip() for attribute in list(attributes or []) if str(attribute or "").strip()]
    if _normalize_active_directory_sync_target_kind(target_kind) == "organizational_units":
        values.extend(["distinguishedName", "ou", "name"])
    return list(dict.fromkeys(values))


def _active_directory_profile_search_base(profile: ActiveDirectorySyncProfile, default_base_dn: str) -> str:
    options = profile.options if isinstance(profile.options, dict) else {}
    if _normalize_active_directory_sync_target_kind(profile.target_kind) == "organizational_units":
        root_dn = str(options.get("ou_root_dn") or "").strip()
        if root_dn:
            return root_dn
    return str(profile.search_base or default_base_dn or "").strip()


def _active_directory_entry_cache_key(entry: dict) -> str:
    for attribute in ("objectGUID", "distinguishedName", "sAMAccountName", "userPrincipalName", "name", "ou"):
        value = _ldap_entry_attribute_value(entry, attribute)
        text = _active_directory_scalar_text(value)
        if text:
            return f"{attribute.lower()}:{text.lower()}"
    return json.dumps(_json_safe_ldap_value(entry), ensure_ascii=False, sort_keys=True)


def _active_directory_scalar_text(value) -> str:
    if isinstance(value, (list, tuple)):
        return _active_directory_scalar_text(value[0] if value else "")
    if isinstance(value, bytes):
        return value.hex()
    return str(value or "").strip()


def _split_active_directory_dn(dn: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escaped = False
    for char in str(dn or ""):
        if char == "\\" and not escaped:
            escaped = True
            current.append(char)
            continue
        if char == "," and not escaped:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            escaped = False
            continue
        current.append(char)
        escaped = False
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def _normalize_active_directory_dn(dn: str) -> str:
    return ",".join(part.strip().lower() for part in _split_active_directory_dn(dn))


def _active_directory_dn_is_under(dn: str, root_dn: str) -> bool:
    normalized_dn = _normalize_active_directory_dn(dn)
    normalized_root = _normalize_active_directory_dn(root_dn)
    return bool(normalized_dn and normalized_root and (normalized_dn == normalized_root or normalized_dn.endswith(f",{normalized_root}")))


def _active_directory_dn_depth_from_root(dn: str, root_dn: str) -> int | None:
    if not _active_directory_dn_is_under(dn, root_dn):
        return None
    dn_parts = _split_active_directory_dn(dn)
    root_parts = _split_active_directory_dn(root_dn)
    return max(0, len(dn_parts) - len(root_parts))


def _active_directory_entry_dn(entry: dict) -> str:
    return _active_directory_scalar_text(_ldap_entry_attribute_value(entry, "distinguishedName"))


def _active_directory_entry_ou_name(entry: dict) -> str:
    return (
        _active_directory_scalar_text(_ldap_entry_attribute_value(entry, "ou"))
        or _active_directory_scalar_text(_ldap_entry_attribute_value(entry, "name"))
    )


def _filter_active_directory_entries_for_profile(entries: list[dict], profile: ActiveDirectorySyncProfile, target_kind: str) -> list[dict]:
    if _normalize_active_directory_sync_target_kind(target_kind) != "organizational_units":
        return list(entries or [])
    options = _normalize_active_directory_profile_options(profile.options, target_kind)
    root_dn = str(options.get("ou_root_dn") or "").strip()
    max_depth = options.get("ou_max_depth")
    excluded_names = {
        _directory_normalized_label(item)
        for item in list(options.get("excluded_ou_names") or [])
        if str(item or "").strip()
    }
    excluded_names.update(TECHNICAL_ACTIVE_DIRECTORY_OU_NAMES)
    excluded_dns = [str(item or "").strip() for item in list(options.get("excluded_ou_dns") or []) if str(item or "").strip()]
    filtered: list[dict] = []
    for entry in list(entries or []):
        dn = _active_directory_entry_dn(entry)
        if root_dn:
            depth = _active_directory_dn_depth_from_root(dn, root_dn)
            if depth is None:
                continue
            if max_depth is not None and depth > int(max_depth):
                continue
        if dn and any(_active_directory_dn_is_under(dn, excluded_dn) for excluded_dn in excluded_dns):
            continue
        name = _directory_normalized_label(_active_directory_entry_ou_name(entry))
        if name and name in excluded_names:
            continue
        filtered.append(entry)
    return filtered


def _active_directory_sync_profile_response(profile: dict) -> ActiveDirectorySyncProfile:
    target_kind = _normalize_active_directory_sync_target_kind(str((profile or {}).get("target_kind") or "users"))
    search_filter = str((profile or {}).get("search_filter") or ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS[target_kind])
    if target_kind == "users" and search_filter.strip() == LEGACY_ACTIVE_DIRECTORY_ACTIVE_USERS_FILTER:
        search_filter = ACTIVE_DIRECTORY_SYNC_DEFAULT_FILTERS[target_kind]
    selected = [
        str(attribute or "").strip()
        for attribute in list((profile or {}).get("selected_attributes") or [])
        if str(attribute or "").strip()
    ]
    return ActiveDirectorySyncProfile(
        id=str((profile or {}).get("id") or ""),
        source_kind="active_directory",
        code=str((profile or {}).get("code") or ""),
        label=str((profile or {}).get("label") or ""),
        target_kind=target_kind,
        search_base=str((profile or {}).get("search_base") or ""),
        search_filter=search_filter,
        selected_attributes=selected or list(ACTIVE_DIRECTORY_SYNC_AVAILABLE_ATTRIBUTES[target_kind][:6]),
        options=_normalize_active_directory_profile_options((profile or {}).get("options"), target_kind),
        is_active=bool((profile or {}).get("is_active", True)),
        created_at=str((profile or {}).get("created_at") or ""),
        updated_at=str((profile or {}).get("updated_at") or ""),
    )


def _json_safe_ldap_value(value):
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_json_safe_ldap_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_ldap_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe_ldap_value(item) for key, item in value.items()}
    return str(value)


def _active_directory_import_value_to_text(value) -> str:
    safe_value = _json_safe_ldap_value(value)
    if isinstance(safe_value, list):
        return ", ".join(str(item or "").strip() for item in safe_value if str(item or "").strip())
    if isinstance(safe_value, dict):
        return json.dumps(safe_value, ensure_ascii=False, sort_keys=True)
    return str(safe_value or "").strip()


def _ldap_entry_attribute_value(row: dict, attribute: str):
    if not isinstance(row, dict):
        return None
    raw_attribute = str(attribute or "").strip()
    if raw_attribute in row:
        return row.get(raw_attribute)
    wanted = raw_attribute.lower()
    for key, value in row.items():
        if str(key or "").strip().lower() == wanted:
            return value
    return None


def _normalize_dashboard_scope(scope: str) -> str:
    normalized = str(scope or "").strip().lower()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Scope dashboard requis.")
    if not re.fullmatch(r"[a-z0-9_-]{1,80}", normalized):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Scope dashboard invalide.")
    return normalized


def _normalize_dashboard_card_ids(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        card_id = str(value or "").strip()
        if not card_id or card_id in seen:
            continue
        if len(card_id) > 160:
            continue
        seen.add(card_id)
        normalized.append(card_id)
    return normalized


def _build_dashboard_preferences_response(scope: str, rows: list[dict]) -> DashboardPreferencesResponse:
    ordered: list[str] = []
    hidden: list[str] = []
    pinned: list[str] = []
    for row in list(rows or []):
        card_id = str(row.get("card_id") or "").strip()
        if not card_id:
            continue
        ordered.append(card_id)
        if bool(row.get("is_hidden")):
            hidden.append(card_id)
        if bool(row.get("is_pinned", True)):
            pinned.append(card_id)
    return DashboardPreferencesResponse(scope=scope, cards_order=ordered, hidden_cards=hidden, pinned_cards=pinned)


def _settings_version_token(settings_payload: dict) -> str:
    payload = {str(key): value for key, value in dict(settings_payload or {}).items() if str(key) != "version_token"}
    return _stable_version_token(payload)


def _build_monitoring_snapshot(model: DevicesModel, runtime: MonitoringRuntimeService) -> dict:
    types: list[MonitoringTypeStateResponse] = []
    total_online = total_offline = total_idle = total_devices = 0
    with model.lock:
        for type_code, meta in model.type_definitions.items():
            devices = list(model.device_data.get(type_code, {}).values())
            online = sum(1 for device in devices if str(getattr(device, "status", "")).strip().lower() == "online")
            offline = sum(1 for device in devices if str(getattr(device, "status", "")).strip().lower() == "offline")
            idle = sum(1 for device in devices if str(getattr(device, "status", "")).strip().lower() == "idle")
            total = len(devices)
            total_online += online
            total_offline += offline
            total_idle += idle
            total_devices += total
            types.append(
                MonitoringTypeStateResponse(
                    type_code=str(type_code),
                    label=str(meta.get("label", type_code)),
                    monitoring_enabled=bool(meta.get("monitoring_enabled", True)),
                    config_backups_enabled=meta.get("config_backups_enabled", None),
                    running=bool(model.do_run.get(type_code, False)),
                    total=total,
                    online=online,
                    offline=offline,
                    idle=idle,
                )
            )
    state = runtime.state()
    return {
        "summary": MonitoringSummaryResponse(
            running_types=state.running_types,
            monitored_types=state.monitored_types,
            running_any=state.running_any,
            running_all=state.running_all,
            total=total_devices,
            online=total_online,
            offline=total_offline,
            idle=total_idle,
        ),
        "types": types,
        "devices": model.build_status_snapshot(),
    }


def _watermark_assets_root() -> Path:
    app_data_root = Path(os.environ.get("LOCALAPPDATA") or str(Path.home()))
    target_dir = app_data_root / "NetworkMonitoringProject" / "assets"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def _watermark_source_target_path() -> Path:
    return _watermark_assets_root() / "custom_watermark_source.png"


def _watermark_rendered_target_path() -> Path:
    return _watermark_assets_root() / "custom_watermark.png"


def _safe_watermark_opacity(value: object, default: float = 0.16) -> float:
    try:
        normalized = float(value if value is not None else default)
    except (TypeError, ValueError):
        normalized = float(default)
    return min(1.0, max(0.05, normalized))


def _safe_watermark_zoom_percent(value: object, default: int = 100) -> int:
    try:
        normalized = int(value if value is not None else default)
    except (TypeError, ValueError):
        normalized = int(default)
    return min(220, max(40, normalized))


def _safe_watermark_offset(value: object, *, minimum: int, maximum: int, default: int = 0) -> int:
    try:
        normalized = int(value if value is not None else default)
    except (TypeError, ValueError):
        normalized = int(default)
    return min(maximum, max(minimum, normalized))


def _store_watermark_source_from_bytes(raw_bytes: bytes) -> str:
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image de fond vide.")
    if len(raw_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image de fond trop volumineuse.")
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Traitement image indisponible (Pillow manquant).",
        ) from exc

    source_path = _watermark_source_target_path()
    try:
        with Image.open(BytesIO(raw_bytes)) as image:
            image.convert("RGBA").save(source_path, format="PNG")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Image invalide: {exc}") from exc
    return str(source_path)


def _materialize_watermark(
    *,
    source_path: str,
    opacity: float,
    offset_x: int,
    offset_y: int,
    zoom_percent: int,
    source_baseline_opacity: float = 1.0,
) -> str:
    src = Path(str(source_path or "").strip())
    if not src.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image source introuvable.")
    try:
        from PIL import Image, ImageEnhance  # type: ignore
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Traitement image indisponible (Pillow manquant).",
        ) from exc

    target_opacity = _safe_watermark_opacity(opacity, default=0.16)
    baseline_opacity = _safe_watermark_opacity(source_baseline_opacity, default=1.0)
    zoom_factor = max(0.4, min(2.2, float(zoom_percent) / 100.0))
    canvas_width, canvas_height = 720, 420

    try:
        with Image.open(src) as image:
            wm = image.convert("RGBA")
        scaled_width = max(1, int(round(wm.width * zoom_factor)))
        scaled_height = max(1, int(round(wm.height * zoom_factor)))
        wm = wm.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        left = int(round((canvas_width - scaled_width) / 2.0 + float(offset_x)))
        top = int(round((canvas_height - scaled_height) / 2.0 + float(offset_y)))
        canvas.alpha_composite(wm, (left, top))
        alpha = canvas.split()[-1]
        alpha = ImageEnhance.Brightness(alpha).enhance(target_opacity / baseline_opacity)
        canvas.putalpha(alpha)
        target = _watermark_rendered_target_path()
        canvas.save(target, format="PNG")
        return str(target)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Traitement image impossible: {exc}",
        ) from exc


def _build_watermark_state_response(settings: NotificationSettings) -> WatermarkStateResponse:
    watermark_path = str(getattr(settings, "watermark_image_path", "") or "").strip()
    enabled = bool(watermark_path and Path(watermark_path).is_file())
    return WatermarkStateResponse(
        enabled=enabled,
        opacity=_safe_watermark_opacity(getattr(settings, "watermark_opacity", 0.16), default=0.16),
        offset_x=_safe_watermark_offset(getattr(settings, "watermark_offset_x", 0), minimum=-300, maximum=300, default=0),
        offset_y=_safe_watermark_offset(getattr(settings, "watermark_offset_y", 0), minimum=-220, maximum=220, default=0),
        zoom_percent=_safe_watermark_zoom_percent(getattr(settings, "watermark_zoom_percent", 100), default=100),
        image_url="/ui/watermark-image" if enabled else "",
    )


def _apply_watermark_settings(settings: NotificationSettings, payload: WatermarkApplyRequest) -> None:
    source_payload = str(getattr(payload, "content_base64", "") or "").strip()
    current_rendered = str(getattr(settings, "watermark_image_path", "") or "").strip()
    current_source = str(getattr(settings, "watermark_source_path", "") or "").strip()
    current_opacity = _safe_watermark_opacity(getattr(settings, "watermark_opacity", 0.16), default=0.16)

    opacity = _safe_watermark_opacity(getattr(payload, "opacity", 0.16), default=0.16)
    offset_x = _safe_watermark_offset(getattr(payload, "offset_x", 0), minimum=-300, maximum=300, default=0)
    offset_y = _safe_watermark_offset(getattr(payload, "offset_y", 0), minimum=-220, maximum=220, default=0)
    zoom_percent = _safe_watermark_zoom_percent(getattr(payload, "zoom_percent", 100), default=100)

    baseline_opacity = 1.0
    if source_payload:
        raw_bytes = _decode_base64_payload(content_base64=source_payload)
        source_path = _store_watermark_source_from_bytes(raw_bytes)
    else:
        if current_source and Path(current_source).is_file():
            source_path = current_source
        elif current_rendered and Path(current_rendered).is_file():
            source_path = current_rendered
            baseline_opacity = current_opacity
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune image de fond configuree. Utiliser Importer d'abord.",
            )

    rendered_path = _materialize_watermark(
        source_path=source_path,
        opacity=opacity,
        offset_x=offset_x,
        offset_y=offset_y,
        zoom_percent=zoom_percent,
        source_baseline_opacity=baseline_opacity,
    )

    try:
        has_dedicated_source = bool(Path(source_path).resolve() != Path(rendered_path).resolve())
    except Exception:
        has_dedicated_source = source_path != rendered_path

    settings.watermark_source_path = source_path if has_dedicated_source else ""
    settings.watermark_image_path = rendered_path
    settings.watermark_opacity = opacity
    settings.watermark_offset_x = offset_x
    settings.watermark_offset_y = offset_y
    settings.watermark_zoom_percent = zoom_percent


def _resolve_watermark_response(settings: NotificationSettings) -> FileResponse:
    watermark_path = str(getattr(settings, "watermark_image_path", "") or "").strip()
    if not watermark_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun watermark configure.")
    path = Path(watermark_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier watermark introuvable.")
    return FileResponse(path)


def _build_ui_config_response(settings: NotificationSettings) -> UiConfigResponse:
    theme_overrides_json = str(getattr(settings, "theme_overrides_json", "") or "")
    theme = resolve_theme(
        str(getattr(settings, "ui_theme", "light") or "light"),
        theme_overrides_json,
    )
    theme_palettes = {
        key: dict(resolve_theme(key, theme_overrides_json).colors)
        for key in ("light", "dark")
    }
    watermark_path = str(getattr(settings, "watermark_image_path", "") or "").strip()
    watermark_enabled = bool(watermark_path and Path(watermark_path).is_file())
    return UiConfigResponse(
        app_version=APP_VERSION,
        ui_theme=theme.key,
        theme_colors=dict(theme.colors),
        theme_palettes=theme_palettes,
        theme_editor_color_keys=list(list_editor_color_keys()),
        watermark_enabled=watermark_enabled,
        watermark_opacity=_safe_watermark_opacity(getattr(settings, "watermark_opacity", 0.16), default=0.16),
        watermark_offset_x=_safe_watermark_offset(getattr(settings, "watermark_offset_x", 0), minimum=-300, maximum=300, default=0),
        watermark_offset_y=_safe_watermark_offset(getattr(settings, "watermark_offset_y", 0), minimum=-220, maximum=220, default=0),
        watermark_zoom_percent=_safe_watermark_zoom_percent(getattr(settings, "watermark_zoom_percent", 100), default=100),
        watermark_url="/ui/watermark-image" if watermark_enabled else "",
    )


def _websocket_backend_supported() -> bool:
    return importlib.util.find_spec("websockets") is not None or importlib.util.find_spec("wsproto") is not None
