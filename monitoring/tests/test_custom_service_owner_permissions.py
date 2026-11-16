import json

from monitoring.services.module_permissions import MODULE_PERMISSION_CODES, custom_service_module_code
from monitoring.storage.mariadb_manager import MariaDBFileManager


MODULE = custom_service_module_code("projets")


class _Connection:
    def __init__(self, *, subject="alice", role_permissions=None, active=True, module_active=True, admin=False):
        self.subject = subject
        self.role_permissions = role_permissions or {}
        self.active = active
        self.module_active = module_active
        self.admin = admin
        self.last_query = ""
        self.last_params = ()
        self.batches = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self

    def execute(self, query, params=()):
        self.last_query = query
        self.last_params = params

    def executemany(self, query, rows):
        self.batches.append((query, list(rows)))

    def fetchall(self):
        if "FROM auth_modules m" in self.last_query:
            return [
                (MODULE, "Projets", "/#service=projets", int(self.module_active), 0, "", "", "", "projets", "alice")
            ]
        if "SELECT code, label, is_active, sort_order" in self.last_query:
            return [("projets", "Projets", 1, 100)]
        if "SELECT code, route_path" in self.last_query:
            return [(MODULE, "/#service=projets")]
        if "SELECT rm.module_code, rm.permissions_json" in self.last_query:
            return [(MODULE, json.dumps(self.role_permissions[self.subject]))] if self.subject in self.role_permissions else []
        if "SELECT ur.role_code, rm.permissions_json" in self.last_query:
            return [("lecteur", json.dumps(self.role_permissions[self.subject]))] if self.subject in self.role_permissions and self.module_active and self.active else []
        raise AssertionError(f"Unexpected query: {self.last_query}")

    def fetchone(self):
        if "SELECT u.is_active, EXISTS" in self.last_query:
            return self.active, self.admin
        if "SELECT cs.code, cs.owner_subject" in self.last_query:
            return ("projets", "alice", self.admin) if self.active and self.module_active else None
        raise AssertionError(f"Unexpected query: {self.last_query}")


def _manager(conn):
    manager = object.__new__(MariaDBFileManager)
    manager._ensure_database = lambda: None
    manager._connect = lambda: conn
    return manager


def test_owner_keeps_full_personal_rights_after_role_loses_module_access():
    conn = _Connection(role_permissions={})
    manager = _manager(conn)

    assert manager.subject_effective_module_permissions(subject="alice", module_code=MODULE) == list(MODULE_PERMISSION_CODES)
    assert manager.subject_has_module_permission(subject="alice", module_code=MODULE, permission="create")


def test_colleague_with_same_role_only_gets_its_shared_rights():
    conn = _Connection(subject="bob", role_permissions={"bob": ["read"]})
    manager = _manager(conn)

    assert manager.subject_effective_module_permissions(subject="bob", module_code=MODULE) == ["read"]
    assert not manager.subject_has_module_permission(subject="bob", module_code=MODULE, permission="create")


def test_admin_role_gets_full_access_without_a_module_grant():
    conn = _Connection(subject="admin-user", admin=True)

    assert _manager(conn).subject_effective_module_permissions(subject="admin-user", module_code=MODULE) == list(MODULE_PERMISSION_CODES)


def test_inactive_user_or_module_has_no_effective_record_rights():
    for active, module_active in ((False, True), (True, False)):
        conn = _Connection(active=active, module_active=module_active, admin=True)
        assert _manager(conn).subject_effective_module_permissions(subject="alice", module_code=MODULE) == []


def test_module_listing_uses_the_same_owner_and_admin_rules_as_api_checks():
    owner = _manager(_Connection()).list_subject_modules(subject="alice")[0]
    colleague = _manager(_Connection(subject="bob", role_permissions={"bob": ["read"]})).list_subject_modules(subject="bob")[0]
    admin = _manager(_Connection(subject="admin-user", admin=True)).list_subject_modules(subject="admin-user")[0]
    inactive = _manager(_Connection(module_active=False, admin=True)).list_subject_modules(subject="alice")[0]

    assert owner["is_owner"] and owner["granted"] and owner["permissions"] == list(MODULE_PERMISSION_CODES)
    assert not colleague["is_owner"] and colleague["granted"] and colleague["permissions"] == ["read"]
    assert admin["granted"] and admin["permissions"] == list(MODULE_PERMISSION_CODES)
    assert not inactive["granted"] and inactive["permissions"] == []


def test_sync_no_longer_grants_the_creators_whole_role_access():
    conn = _Connection()

    _manager(conn)._sync_custom_service_auth_modules(conn)

    assert not any("owner_role_code" in query for query, _rows in conn.batches)
