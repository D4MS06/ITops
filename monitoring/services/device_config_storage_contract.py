"""Stable ownership contract for network-equipment configuration storage.

The former Monitoring identifier is intentionally kept as a read-compatible
alias.  Existing storage targets and every linked configuration version remain
valid; no database row or physical file needs to be moved during the module
split.
"""

NETWORK_EQUIPMENT_CONFIG_STORAGE_SERVICE_CODE = "network_equipment.device_config_files"
LEGACY_MONITORING_CONFIG_STORAGE_SERVICE_CODE = "monitoring.device_config_files"
DEVICE_CONFIG_STORAGE_SERVICE_CODES = frozenset(
    {
        NETWORK_EQUIPMENT_CONFIG_STORAGE_SERVICE_CODE,
        LEGACY_MONITORING_CONFIG_STORAGE_SERVICE_CODE,
    }
)


def is_device_config_storage_service_code(value: object) -> bool:
    return str(value or "").strip().lower() in DEVICE_CONFIG_STORAGE_SERVICE_CODES
