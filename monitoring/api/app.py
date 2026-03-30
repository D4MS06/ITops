from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import tempfile
import uuid
from queue import Empty, Queue
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
import threading

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from monitoring.versioning import resolve_display_version
from monitoring.api.schemas import (
    AuthStatusResponse,
    BootstrapPasswordRequest,
    ConfigFileResponse,
    ConfigFileImportRequest,
    ConfigStorageStateResponse,
    DeviceCreateRequest,
    DeviceResponse,
    DeviceTypeCreateRequest,
    DeviceTypeResponse,
    DeviceTypeSchemaResponse,
    DeviceTypeUpdateRequest,
    DeviceUpdateRequest,
    LoginRequest,
    MessageResponse,
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
    SessionInfoResponse,
    SettingsResponse,
    SettingsUpdateRequest,
    StatusLogResponse,
    TokenResponse,
    UiConfigResponse,
)
from monitoring.backend.app_backend import ApplicationBackend, build_application_backend
from monitoring.config.settings import NotificationSettings, load_settings, save_settings
from monitoring.models.devices_model import DevicesModel
from monitoring.services.auth_service import AuthService
from monitoring.services.auth_service import PasswordChangeRequiredError
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.services.device_type_service import DeviceTypeService
from monitoring.services.monitoring_runtime_service import MonitoringRuntimeService
from monitoring.services.monitoring_service import MonitoringService
from monitoring.services.settings_service import SettingsService
from monitoring.services.caddy_manager import CaddyManager
from monitoring.services.device_action_policy import validate_action_double_click
from monitoring.controllers.network_tools_controller import NetworkToolsController
from monitoring.services.network_scan_service import NetworkScanService
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.ui.theme_manager import resolve_theme
from monitoring.utils.config_files import list_local_config_versions
from monitoring.utils.config_files import has_local_config_versions
from monitoring.utils.config_files import open_path_with_default_app
from monitoring.utils.logger import log_with_timestamp

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
FAVICON_PATH = Path(__file__).resolve().parent.parent / "ui" / "assets" / "app.ico"
APP_VERSION = resolve_display_version()


@dataclass
class ApiServices:
    model: DevicesModel
    auth: AuthService
    device_types: DeviceTypeService
    monitoring: MonitoringService
    monitoring_runtime: MonitoringRuntimeService
    config_storage: ConfigStorageService
    network_tools: NetworkToolsController
    logs: SQLiteFileManager
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
    logs_manager: Optional[SQLiteFileManager] = None,
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
    app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")

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

    _register_base_routes(app, get_services)
    _register_auth_routes(app, get_services, get_bearer_token, require_session)
    _register_devices_routes(app, get_services, require_session, require_monitoring_module)
    _register_logs_routes(app, get_services, require_session, require_monitoring_module)
    _register_network_tools_routes(app, get_services, require_session, require_monitoring_module)
    _register_monitoring_routes(app, get_services, require_session, require_websocket_session, require_monitoring_module)
    _register_ui_routes(app, get_services, require_session, require_websocket_session)
    _register_config_routes(app, get_services, require_session, require_monitoring_module)
    _register_settings_routes(app, get_services, require_session)
    return app


def _build_api_services(
    *,
    backend: Optional[ApplicationBackend],
    model: Optional[DevicesModel],
    auth_service: Optional[AuthService],
    device_type_service: Optional[DeviceTypeService],
    monitoring_runtime_service: Optional[MonitoringRuntimeService],
    config_storage_service: Optional[ConfigStorageService],
    logs_manager: Optional[SQLiteFileManager],
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
        network_tools=NetworkToolsController(),
        logs=shared_manager,
        settings_service=backend.settings_service,
        settings_loader=settings_loader or backend.settings_loader,
        settings_saver=settings_saver or backend.settings_saver,
    )


def _build_lifespan(services: ApiServices, stop_runtime_on_shutdown: bool):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = services
        try:
            yield
        finally:
            if stop_runtime_on_shutdown:
                try:
                    services.monitoring_runtime.stop_all()
                    services.monitoring.shutdown()
                except Exception as exc:
                    log_with_timestamp(f"Erreur arret runtime API: {exc}", level="WARNING")

    return lifespan


def _register_base_routes(app: FastAPI, get_services) -> None:
    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def web_portal_index() -> FileResponse:
        return FileResponse(WEB_DIR / "portal.html")

    @app.get("/portal", include_in_schema=False)
    def web_portal_alias() -> FileResponse:
        return FileResponse(WEB_DIR / "portal.html")

    @app.get("/monitoring", include_in_schema=False)
    def web_app_index(
        token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
    ):
        session = api.auth.get_session(str(token or "").strip())
        if session is None:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        checker = getattr(api.logs, "subject_has_module", None)
        if callable(checker):
            allowed = bool(checker(subject=str(session.subject), module_code="monitoring"))
        else:
            allowed = str(session.subject).strip().lower() in {"sa", "admin"}
        if not allowed:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/monitoring/", include_in_schema=False)
    def web_app_index_slash(
        token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
    ):
        session = api.auth.get_session(str(token or "").strip())
        if session is None:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        checker = getattr(api.logs, "subject_has_module", None)
        if callable(checker):
            allowed = bool(checker(subject=str(session.subject), module_code="monitoring"))
        else:
            allowed = str(session.subject).strip().lower() in {"sa", "admin"}
        if not allowed:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(FAVICON_PATH)


def _register_auth_routes(app: FastAPI, get_services, get_bearer_token, require_session) -> None:
    @app.get("/auth/status", response_model=AuthStatusResponse)
    def auth_status(api: ApiServices = Depends(get_services)) -> AuthStatusResponse:
        return AuthStatusResponse(has_admin_password=api.auth.has_admin_password())

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

    @app.get("/auth/me/modules", response_model=list[ModuleAccessResponse])
    def auth_me_modules(
        session=Depends(require_session),
        api: ApiServices = Depends(get_services),
    ) -> list[ModuleAccessResponse]:
        lister = getattr(api.logs, "list_subject_modules", None)
        if callable(lister):
            rows = lister(subject=str(session.subject))
        else:
            rows = [
                {
                    "code": "monitoring",
                    "label": "Monitoring",
                    "route_path": "/monitoring",
                    "is_active": True,
                    "granted": str(session.subject).strip().lower() in {"sa", "admin"},
                }
            ]
        return [ModuleAccessResponse(**row) for row in rows]


def _register_devices_routes(app: FastAPI, get_services, require_session, require_monitoring_module) -> None:
    def _device_with_saved_config(api: ApiServices, row: dict) -> dict:
        payload = dict(row or {})
        dtype = str(payload.get("device_type") or payload.get("type") or "").strip().lower()
        if not dtype:
            payload["has_saved_config"] = False
            return payload
        if not api.model.is_config_download_type(dtype):
            payload["has_saved_config"] = False
            return payload
        type_label = str(api.model.type_definitions.get(dtype, {}).get("label", dtype)).strip() or dtype
        device_name = str(payload.get("name", "")).strip()
        try:
            payload["has_saved_config"] = bool(
                has_local_config_versions(
                    local_versions_root=api.config_storage.local_versions_root_dir(),
                    device_type_label=type_label,
                    device_name=device_name,
                )
            )
        except Exception:
            payload["has_saved_config"] = False
        return payload

    @app.get("/devices", response_model=list[DeviceResponse])
    def list_devices(
        device_type: Optional[str] = None,
        q: Optional[str] = None,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[DeviceResponse]:
        rows = api.model.search_devices(q, device_type=device_type) if q else api.model.list_devices(device_type=device_type)
        return [DeviceResponse(**_device_with_saved_config(api, row)) for row in rows]

    @app.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
    def create_device(
        payload: DeviceCreateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceResponse:
        fields, actions = api.device_types.load_schema(payload.device_type)
        try:
            validate_action_double_click(
                fields=fields,
                actions=actions,
                device_subtype=str(payload.device_subtype or ""),
                action_double_click=str(payload.action_double_click or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
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
            custom_data=payload.custom_data,
            notify=payload.notify,
        )
        if device_id is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Adresse IP deja utilisee pour ce type.")
        row = next(item for item in api.model.list_devices(device_type=payload.device_type) if item["id"] == device_id)
        return DeviceResponse(**_device_with_saved_config(api, row))

    @app.put("/devices/{device_type}/{device_id}", response_model=DeviceResponse)
    def update_device(
        device_type: str,
        device_id: str,
        payload: DeviceUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceResponse:
        fields, actions = api.device_types.load_schema(device_type)
        try:
            validate_action_double_click(
                fields=fields,
                actions=actions,
                device_subtype=str(payload.device_subtype or ""),
                action_double_click=str(payload.action_double_click or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
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
            custom_data=payload.custom_data,
            notify=payload.notify,
        )
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable ou mise a jour invalide.")
        row = next(item for item in api.model.list_devices(device_type=device_type) if item["id"] == device_id)
        return DeviceResponse(**_device_with_saved_config(api, row))

    @app.delete("/devices/{device_type}/{device_id}", response_model=MessageResponse)
    def delete_device(
        device_type: str,
        device_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
        if not api.model.delete_device(device_type, device_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipement introuvable.")
        return MessageResponse(message="Equipement supprime.")

    @app.get("/device-types", response_model=list[DeviceTypeResponse])
    def list_device_types(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[DeviceTypeResponse]:
        return [DeviceTypeResponse(**row) for row in api.device_types.list_types()]

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
        row = next(item for item in api.device_types.list_types() if str(item.get("code", "")) == str(code))
        return DeviceTypeResponse(**row)

    @app.put("/device-types/{type_code}", response_model=DeviceTypeResponse)
    def update_device_type(
        type_code: str,
        payload: DeviceTypeUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> DeviceTypeResponse:
        code = api.device_types.save_type(
            code=type_code,
            label=payload.label,
            monitoring_enabled=bool(payload.monitoring_enabled),
            config_backups_enabled=payload.config_backups_enabled,
        )
        api.model.refresh_type_definitions()
        api.model.notify_state_changed()
        row = next(item for item in api.device_types.list_types() if str(item.get("code", "")) == str(code))
        return DeviceTypeResponse(**row)

    @app.delete("/device-types/{type_code}", response_model=MessageResponse)
    def delete_device_type(
        type_code: str,
        cascade_devices: bool = False,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> MessageResponse:
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
        return DeviceTypeSchemaResponse(fields=fields, actions=actions)


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
        mode = str(payload.mode or "vlan").strip().lower()
        if mode == "vlan":
            start_ip, end_ip = scanner.vlan_to_range(int(payload.vlan))
        else:
            start_ip = str(payload.start_ip or "").strip()
            end_ip = str(payload.end_ip or "").strip()
            scanner.normalize_range(start_ip, end_ip)

        rows = scanner.scan_range(
            start_ip=start_ip,
            end_ip=end_ip,
            allow_vendor_network=bool(payload.allow_vendor_online),
            timeout_ms=int(payload.timeout_ms),
            max_workers=int(payload.max_workers),
        )
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
        mode = str(payload.mode or "vlan").strip().lower()
        if mode == "vlan":
            start_ip, end_ip = scanner.vlan_to_range(int(payload.vlan))
        else:
            start_ip = str(payload.start_ip or "").strip()
            end_ip = str(payload.end_ip or "").strip()
            scanner.normalize_range(start_ip, end_ip)

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
        return _build_ui_config_response(api.settings_loader())

    @app.get("/ui/auth-config", response_model=UiConfigResponse)
    def get_auth_ui_config(api: ApiServices = Depends(get_services)) -> UiConfigResponse:
        settings = api.settings_loader()
        ui_config = _build_ui_config_response(settings)
        if ui_config.watermark_enabled:
            ui_config = ui_config.model_copy(update={"watermark_url": "/ui/auth-watermark-image"})
        return ui_config

    @app.get("/ui/auth-watermark-image", include_in_schema=False)
    def get_auth_ui_watermark_image(api: ApiServices = Depends(get_services)) -> FileResponse:
        return _resolve_watermark_response(api.settings_loader())

    @app.get("/ui/watermark-image", include_in_schema=False)
    def get_ui_watermark_image(
        token: str = Query(default=""),
        api: ApiServices = Depends(get_services),
    ) -> FileResponse:
        if require_websocket_session(token, api) is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expiree.")
        return _resolve_watermark_response(api.settings_loader())

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
    def _config_storage_state(api: ApiServices) -> ConfigStorageStateResponse:
        settings = api.settings_loader()
        mode = str(getattr(settings, "config_storage_mode", "local") or "local").strip().lower()
        has_password = bool(str(getattr(settings, "config_smb_password", "") or "").strip())
        if mode != "smb3":
            return ConfigStorageStateResponse(
                mode=mode,
                can_open_backup_folder=True,
                has_smb_password=has_password,
                message="Mode local",
            )
        unc = str(getattr(settings, "config_smb_unc_path", "") or "").strip()
        user = str(getattr(settings, "config_smb_username", "") or "").strip()
        if not (unc and user and has_password):
            return ConfigStorageStateResponse(
                mode=mode,
                can_open_backup_folder=False,
                has_smb_password=has_password,
                message="Configuration SMB3 incomplete",
            )
        ok, info = api.config_storage.ensure_backup_connection()
        return ConfigStorageStateResponse(
            mode=mode,
            can_open_backup_folder=bool(ok),
            has_smb_password=has_password,
            message=str(info or ""),
        )

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
        root = api.config_storage.local_versions_root_dir()
        root.mkdir(parents=True, exist_ok=True)
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
        root = api.config_storage.backup_root_dir()
        if str(storage_state.mode).lower() != "smb3":
            root.mkdir(parents=True, exist_ok=True)
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
        stats = api.config_storage.sync_local_versions_to_backup()
        return MessageResponse(
            message=(
                "Sauvegarde terminee. "
                f"Versions locales analysees: {int(stats.scanned)} | "
                f"Fichiers sauvegardes: {int(stats.copied)}"
            )
        )

    @app.get("/config-files", response_model=list[ConfigFileResponse])
    def list_config_files(
        device_type_label: str,
        device_name: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> list[ConfigFileResponse]:
        rows = list_local_config_versions(
            local_versions_root=api.config_storage.local_versions_root_dir(),
            device_type_label=device_type_label,
            device_name=device_name,
        )
        return [ConfigFileResponse(**row) for row in rows]

    @app.get("/config-files/latest-download")
    def download_latest_config_file(
        device_type: str,
        device_name: str,
        device_ip: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_monitoring_module),
    ) -> FileResponse:
        dtype = str(device_type or "").strip().lower()
        if not dtype:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type de device manquant.")
        if not api.model.is_config_download_type(dtype):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce type ne gere pas les fichiers de configuration.")
        matches = api.config_storage.find_device_backup_files(
            device_name=str(device_name or "").strip(),
            device_ip=str(device_ip or "").strip(),
            max_results=1,
        )
        if not matches:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune sauvegarde trouvee.")
        source = Path(matches[0])
        return FileResponse(path=source, filename=source.name, media_type="application/octet-stream")

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
        try:
            raw_bytes = base64.b64decode(str(payload.content_base64 or ""), validate=True)
            tmp_path.write_bytes(raw_bytes)
            created_at = api.config_storage.file_created_at(tmp_path)
            target = api.config_storage.import_device_config_version(
                device_type_label=type_label,
                device_name=dname,
                source_file=tmp_path,
                detail=str(payload.detail or "").strip(),
                stamp_dt=created_at,
            )
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Contenu base64 invalide: {exc}") from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Import impossible: {exc}") from exc
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
        return MessageResponse(message=f"Version importee: {target}")


def _register_settings_routes(app: FastAPI, get_services, require_session) -> None:
    @app.get("/settings", response_model=SettingsResponse)
    def get_settings(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> SettingsResponse:
        return SettingsResponse(**_serialize_settings(api.settings_loader()))

    @app.put("/settings", response_model=SettingsResponse)
    def update_settings(
        payload: SettingsUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> SettingsResponse:
        current_settings = api.settings_loader()
        settings = NotificationSettings(**payload.model_dump())
        settings.password = current_settings.password
        settings.github_token = current_settings.github_token
        settings.config_smb_password = current_settings.config_smb_password
        api.settings_saver(settings)
        return SettingsResponse(**_serialize_settings(api.settings_loader()))


def _serialize_settings(settings: NotificationSettings) -> dict:
    data = settings.__dict__.copy()
    data.pop("password", None)
    data.pop("github_token", None)
    data.pop("config_smb_password", None)
    return data


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


def _resolve_watermark_response(settings: NotificationSettings) -> FileResponse:
    watermark_path = str(getattr(settings, "watermark_image_path", "") or "").strip()
    if not watermark_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun watermark configure.")
    path = Path(watermark_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier watermark introuvable.")
    return FileResponse(path)


def _build_ui_config_response(settings: NotificationSettings) -> UiConfigResponse:
    theme = resolve_theme(str(getattr(settings, "ui_theme", "light") or "light"))
    watermark_path = str(getattr(settings, "watermark_image_path", "") or "").strip()
    watermark_enabled = bool(watermark_path and Path(watermark_path).is_file())
    return UiConfigResponse(
        app_version=APP_VERSION,
        ui_theme=theme.key,
        theme_colors=dict(theme.colors),
        watermark_enabled=watermark_enabled,
        watermark_opacity=min(1.0, max(0.0, float(getattr(settings, "watermark_opacity", 0.16) or 0.16))),
        watermark_url="/ui/watermark-image" if watermark_enabled else "",
    )


def _websocket_backend_supported() -> bool:
    return importlib.util.find_spec("websockets") is not None or importlib.util.find_spec("wsproto") is not None
