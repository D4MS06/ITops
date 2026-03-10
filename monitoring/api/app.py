from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status

from monitoring.api.schemas import (
    AuthStatusResponse,
    BootstrapPasswordRequest,
    ConfigFileResponse,
    DeviceCreateRequest,
    DeviceResponse,
    DeviceTypeResponse,
    DeviceTypeSchemaResponse,
    DeviceUpdateRequest,
    LoginRequest,
    MessageResponse,
    SessionInfoResponse,
    SettingsResponse,
    SettingsUpdateRequest,
    StatusLogResponse,
    TokenResponse,
)
from monitoring.config.settings import NotificationSettings, load_settings, save_settings
from monitoring.backend.app_backend import ApplicationBackend, build_application_backend
from monitoring.models.devices_model import DevicesModel
from monitoring.services.auth_service import AuthService
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.services.device_type_service import DeviceTypeService
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.utils.config_files import list_local_config_versions


@dataclass
class ApiServices:
    model: DevicesModel
    auth: AuthService
    device_types: DeviceTypeService
    config_storage: ConfigStorageService
    logs: SQLiteFileManager
    settings_loader: Callable[[], NotificationSettings]
    settings_saver: Callable[[NotificationSettings], None]


def create_app(
    *,
    backend: Optional[ApplicationBackend] = None,
    model: Optional[DevicesModel] = None,
    auth_service: Optional[AuthService] = None,
    device_type_service: Optional[DeviceTypeService] = None,
    config_storage_service: Optional[ConfigStorageService] = None,
    logs_manager: Optional[SQLiteFileManager] = None,
    settings_loader: Callable[[], NotificationSettings] = load_settings,
    settings_saver: Callable[[NotificationSettings], None] = save_settings,
) -> FastAPI:
    app = FastAPI(title="Network Monitoring API", version="1.0.7-prep")
    backend = backend or build_application_backend(
        manager=logs_manager,
        settings_loader=settings_loader,
        settings_saver=settings_saver,
    )
    model = model or backend.model
    shared_manager = logs_manager or backend.manager
    services = ApiServices(
        model=model,
        auth=auth_service or backend.auth_service,
        device_types=device_type_service or backend.device_type_service,
        config_storage=config_storage_service or backend.config_storage_service,
        logs=shared_manager,
        settings_loader=settings_loader or backend.settings_loader,
        settings_saver=settings_saver or backend.settings_saver,
    )
    app.state.services = services

    def get_services() -> ApiServices:
        return app.state.services

    def get_bearer_token(authorization: Optional[str] = Header(default=None)) -> str:
        raw = str(authorization or "").strip()
        if not raw.lower().startswith("bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
        token = raw[7:].strip()
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empty bearer token.")
        return token

    def require_session(
        token: str = Depends(get_bearer_token),
        api: ApiServices = Depends(get_services),
    ):
        session = api.auth.get_session(token)
        if session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")
        return session

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

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
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bootstrap already completed.")
        api.auth.set_admin_password(payload.password)
        return MessageResponse(message="Admin password configured.")

    @app.post("/auth/login", response_model=TokenResponse)
    def login(payload: LoginRequest, api: ApiServices = Depends(get_services)) -> TokenResponse:
        session = api.auth.login(payload.password)
        if session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
        return TokenResponse(access_token=session.token, expires_at=session.expires_at.isoformat())

    @app.post("/auth/logout", response_model=MessageResponse)
    def logout(
        token: str = Depends(get_bearer_token),
        api: ApiServices = Depends(get_services),
    ) -> MessageResponse:
        if not api.auth.logout(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")
        return MessageResponse(message="Logged out.")

    @app.get("/auth/me", response_model=SessionInfoResponse)
    def auth_me(session=Depends(require_session)) -> SessionInfoResponse:
        return SessionInfoResponse(subject=session.subject, expires_at=session.expires_at.isoformat())

    @app.get("/devices", response_model=list[DeviceResponse])
    def list_devices(
        device_type: Optional[str] = None,
        q: Optional[str] = None,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> list[DeviceResponse]:
        if q:
            rows = api.model.search_devices(q, device_type=device_type)
        else:
            rows = api.model.list_devices(device_type=device_type)
        return [DeviceResponse(**row) for row in rows]

    @app.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
    def create_device(
        payload: DeviceCreateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> DeviceResponse:
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
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate device IP for this type.")
        row = next(item for item in api.model.list_devices(device_type=payload.device_type) if item["id"] == device_id)
        return DeviceResponse(**row)

    @app.put("/devices/{device_type}/{device_id}", response_model=DeviceResponse)
    def update_device(
        device_type: str,
        device_id: str,
        payload: DeviceUpdateRequest,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> DeviceResponse:
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found or invalid update.")
        row = next(item for item in api.model.list_devices(device_type=device_type) if item["id"] == device_id)
        return DeviceResponse(**row)

    @app.delete("/devices/{device_type}/{device_id}", response_model=MessageResponse)
    def delete_device(
        device_type: str,
        device_id: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> MessageResponse:
        if not api.model.delete_device(device_type, device_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
        return MessageResponse(message="Device deleted.")

    @app.get("/device-types", response_model=list[DeviceTypeResponse])
    def list_device_types(
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> list[DeviceTypeResponse]:
        return [DeviceTypeResponse(**row) for row in api.device_types.list_types()]

    @app.get("/device-types/{type_code}/schema", response_model=DeviceTypeSchemaResponse)
    def get_device_type_schema(
        type_code: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> DeviceTypeSchemaResponse:
        fields, actions = api.device_types.load_schema(type_code)
        return DeviceTypeSchemaResponse(fields=fields, actions=actions)

    @app.get("/logs", response_model=list[StatusLogResponse])
    def list_logs(
        limit: int = 300,
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> list[StatusLogResponse]:
        rows = api.logs.list_status_logs(limit=limit, dtype=device_type, device_id=device_id)
        return [StatusLogResponse(**row) for row in rows]

    @app.get("/config-files", response_model=list[ConfigFileResponse])
    def list_config_files(
        device_type_label: str,
        device_name: str,
        api: ApiServices = Depends(get_services),
        _session=Depends(require_session),
    ) -> list[ConfigFileResponse]:
        rows = list_local_config_versions(
            local_versions_root=api.config_storage.local_versions_root_dir(),
            device_type_label=device_type_label,
            device_name=device_name,
        )
        return [ConfigFileResponse(**row) for row in rows]

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
        settings = NotificationSettings(**payload.model_dump())
        settings.password = api.settings_loader().password
        settings.github_token = api.settings_loader().github_token
        settings.config_smb_password = api.settings_loader().config_smb_password
        api.settings_saver(settings)
        return SettingsResponse(**_serialize_settings(api.settings_loader()))

    return app


def _serialize_settings(settings: NotificationSettings) -> dict:
    data = settings.__dict__.copy()
    data.pop("password", None)
    data.pop("github_token", None)
    data.pop("config_smb_password", None)
    return data
