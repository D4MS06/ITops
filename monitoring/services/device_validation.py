from __future__ import annotations

from typing import Dict

from monitoring.models.device import Device


def validate_device_type(device_type: str, type_definitions: Dict[str, dict]) -> str:
    normalized_type = str(device_type or "").strip()
    if not normalized_type or normalized_type not in type_definitions:
        raise ValueError("Type d'equipement inconnu.")
    return normalized_type


def validate_device_fields(
    *,
    device_type: str,
    type_definitions: Dict[str, dict],
    existing_devices: Dict[str, Dict[str, Device]],
    name: str,
    ip: str,
    exclude_device_id: str | None = None,
) -> None:
    if not name:
        raise ValueError("Nom d'equipement requis.")
    if bool(type_definitions.get(device_type, {}).get("monitoring_enabled", True)) and not ip:
        raise ValueError("Adresse IP requise.")
    if not ip:
        return
    for current_id, device in existing_devices.get(device_type, {}).items():
        if exclude_device_id is not None and str(current_id) == str(exclude_device_id):
            continue
        if str(getattr(device, "ip", "")).strip() == ip:
            raise ValueError("Adresse IP deja utilisee pour ce type.")
