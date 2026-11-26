"""Build a password inventory from authorized module records, without exposing secrets."""

from __future__ import annotations


def build_password_inventory(*, devices, custom_services, can_view_devices, can_manage_devices, can_view, can_manage,
                             device_credentials, custom_records, custom_password_exists):
    rows = []
    if can_view_devices:
        for device in devices:
            dtype = str(device.get("device_type") or "").strip().lower()
            device_id = str(device.get("id") or "").strip()
            if not dtype or not device_id:
                continue
            for access in ("web", "ssh", "remote_desktop"):
                credentials = device_credentials(dtype, device_id, access)
                if not credentials.get("login") and not credentials.get("password"):
                    continue
                rows.append({"kind": "device", "module_code": "network_equipment", "module_label": "Équipements réseau",
                             "record_id": device_id, "device_type": dtype, "access": access,
                             "label": str(device.get("name") or device_id), "login": str(credentials.get("login") or ""),
                             "has_password": bool(credentials.get("password")), "can_manage": can_manage_devices})
    for service in custom_services:
        code = str(service.get("code") or "").strip().lower()
        if not code or not service.get("credentials_enabled") or not can_view(code):
            continue
        module_can_manage = bool(can_manage(code))
        for record in custom_records(code):
            record_id = str(record.get("id") or "").strip()
            if not record_id:
                continue
            values = dict(record.get("values") or {})
            login = str(values.get("device_login") or "")
            has_password = bool(custom_password_exists(code, record_id) or values.get("device_password") or values.get("password"))
            if not login and not has_password:
                continue
            label = str(values.get("name") or values.get("address") or values.get("nom") or record_id)
            rows.append({"kind": "custom", "module_code": code, "module_label": str(service.get("label") or code),
                         "record_id": record_id, "device_type": "", "access": "", "label": label,
                         "login": login, "has_password": has_password, "can_manage": module_can_manage})
    return rows
