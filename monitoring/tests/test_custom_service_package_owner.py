from monitoring.api.app import _apply_custom_service_package_import
from monitoring.api.schemas import CustomServicePackageImportRequest


class _PackageStore:
    def __init__(self):
        self.saved = []

    def list_custom_services(self):
        return [{"code": "existing"}]

    def save_custom_service(self, **values):
        self.saved.append(values)

    def list_custom_service_relations(self):
        return []


def test_imported_modules_keep_existing_owner_and_assign_importer_to_new_module():
    store = _PackageStore()
    package = {
        "format": "itops-custom-service-package-v1",
        "services": [{"code": "existing"}, {"code": "new"}],
    }
    options = CustomServicePackageImportRequest(
        content_base64="x", include_records=False, include_shared_lists=False,
    )

    result = _apply_custom_service_package_import(store, package, options, changed_by="admin-user")

    assert result["services_created"] == 1
    assert result["services_updated"] == 1
    owners = {row["code"]: row["owner_subject"] for row in store.saved}
    assert owners == {"existing": "", "new": "admin-user"}
