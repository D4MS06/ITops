from monitoring.config.settings import NotificationSettings
from monitoring.services.config_storage_service import ConfigStorageService
from monitoring.services.device_config_storage_contract import (
    LEGACY_MONITORING_CONFIG_STORAGE_SERVICE_CODE,
    NETWORK_EQUIPMENT_CONFIG_STORAGE_SERVICE_CODE,
    is_device_config_storage_service_code,
)


def test_config_storage_uses_network_equipment_as_its_canonical_owner():
    service = ConfigStorageService(settings_provider=NotificationSettings)

    descriptor = service.remote_mount_descriptors()[0]

    assert descriptor["service_code"] == NETWORK_EQUIPMENT_CONFIG_STORAGE_SERVICE_CODE
    assert descriptor["service_label"] == "Équipements réseau - fichiers de configuration"


def test_legacy_monitoring_storage_identifier_remains_read_compatible():
    assert is_device_config_storage_service_code(NETWORK_EQUIPMENT_CONFIG_STORAGE_SERVICE_CODE)
    assert is_device_config_storage_service_code(LEGACY_MONITORING_CONFIG_STORAGE_SERVICE_CODE)
    assert not is_device_config_storage_service_code("monitoring.logs")
