from __future__ import annotations

from dataclasses import dataclass, replace
import ssl
from threading import RLock
from typing import Any, Callable

from monitoring.config.settings import NotificationSettings


@dataclass(frozen=True)
class ActiveDirectoryConnection:
    host: str
    port: int
    use_ssl: bool
    validate_certificates: bool
    ca_certificate_path: str
    bind_username: str
    bind_password: str
    base_dn: str
    user_filter: str


class ActiveDirectorySyncEngine:
    """Connecteur LDAP reutilisable; les modules conservent leur propre mapping."""

    DEFAULT_USER_FILTER = "(&(objectCategory=person)(objectClass=user))"
    DEFAULT_ATTRIBUTES = [
        "objectGUID",
        "sAMAccountName",
        "displayName",
        "givenName",
        "sn",
        "mail",
        "proxyAddresses",
        "otherMailbox",
        "userPrincipalName",
        "telephoneNumber",
        "department",
        "manager",
        "memberOf",
        "userAccountControl",
    ]

    @classmethod
    def connection_from_settings(cls, settings: object) -> ActiveDirectoryConnection:
        return ActiveDirectoryConnection(
            host=str(getattr(settings, "active_directory_host", "") or "").strip(),
            port=max(1, min(65535, int(getattr(settings, "active_directory_port", 636) or 636))),
            use_ssl=bool(getattr(settings, "active_directory_use_ssl", True)),
            validate_certificates=bool(getattr(settings, "active_directory_validate_certificates", True)),
            ca_certificate_path=str(getattr(settings, "active_directory_ca_certificate_path", "") or "").strip(),
            bind_username=str(getattr(settings, "active_directory_bind_username", "") or "").strip(),
            bind_password=str(getattr(settings, "active_directory_bind_password", "") or ""),
            base_dn=str(getattr(settings, "active_directory_base_dn", "") or "").strip(),
            user_filter=str(getattr(settings, "active_directory_user_filter", "") or "").strip() or cls.DEFAULT_USER_FILTER,
        )

    @staticmethod
    def validate(connection: ActiveDirectoryConnection) -> None:
        for value, label in ((connection.host, "Serveur Active Directory"), (connection.base_dn, "Base DN Active Directory"), (connection.bind_username, "Compte de lecture Active Directory"), (connection.bind_password, "Mot de passe du compte Active Directory")):
            if not value:
                raise ValueError(f"{label} requis.")

    def test_connection(self, settings: object) -> str:
        connection = self.connection_from_settings(settings)
        self.validate(connection)
        try:
            import ldap3  # type: ignore
        except ImportError as exc:  # pragma: no cover - deployment dependency
            raise RuntimeError("Le composant LDAP n'est pas installe. Installez la dependance 'ldap3'.") from exc
        tls = ldap3.Tls(
            validate=ssl.CERT_REQUIRED if connection.validate_certificates else ssl.CERT_NONE,
            ca_certs_file=connection.ca_certificate_path or None,
        )
        server = ldap3.Server(connection.host, port=connection.port, use_ssl=connection.use_ssl, tls=tls)
        client = ldap3.Connection(server, user=connection.bind_username, password=connection.bind_password, auto_bind=True)
        try:
            return f"Connexion Active Directory valide : {connection.host}:{connection.port}."
        finally:
            client.unbind()

    def fetch_users(self, settings: object, *, limit: int = 5000) -> list[dict[str, Any]]:
        """Retourne des entrees AD normalisees; le mapping reste au module consommateur."""
        return self.fetch_entries(
            settings,
            search_filter=self.connection_from_settings(settings).user_filter,
            attributes=self.DEFAULT_ATTRIBUTES,
            limit=limit,
        )

    def fetch_entries(
        self,
        settings: object,
        *,
        search_base: str = "",
        search_filter: str = "",
        attributes: list[str] | None = None,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        """Lecture LDAP generique pour profils de synchronisation AD."""
        connection = self.connection_from_settings(settings)
        self.validate(connection)
        resolved_base = str(search_base or connection.base_dn).strip()
        resolved_filter = str(search_filter or connection.user_filter).strip() or self.DEFAULT_USER_FILTER
        resolved_attributes = [
            str(attribute or "").strip()
            for attribute in (attributes or self.DEFAULT_ATTRIBUTES)
            if str(attribute or "").strip()
        ] or self.DEFAULT_ATTRIBUTES
        try:
            import ldap3  # type: ignore
        except ImportError as exc:  # pragma: no cover - deployment dependency
            raise RuntimeError("Le composant LDAP n'est pas installe. Installez la dependance 'ldap3'.") from exc
        tls = ldap3.Tls(
            validate=ssl.CERT_REQUIRED if connection.validate_certificates else ssl.CERT_NONE,
            ca_certs_file=connection.ca_certificate_path or None,
        )
        server = ldap3.Server(connection.host, port=connection.port, use_ssl=connection.use_ssl, tls=tls)
        client = ldap3.Connection(server, user=connection.bind_username, password=connection.bind_password, auto_bind=True)
        try:
            client.search(
                search_base=resolved_base,
                search_filter=resolved_filter,
                search_scope=ldap3.SUBTREE,
                attributes=resolved_attributes,
                paged_size=min(max(1, int(limit or 5000)), 5000),
            )
            return [dict(entry.entry_attributes_as_dict) for entry in client.entries]
        finally:
            client.unbind()


class SettingsService:
    """Cache mutable autour des settings avec persistance explicite."""

    def __init__(
        self,
        *,
        loader: Callable[[], NotificationSettings],
        saver: Callable[[NotificationSettings], None],
    ) -> None:
        self._loader = loader
        self._saver = saver
        self._lock = RLock()
        self._settings: NotificationSettings | None = None

    def load(self, *, force: bool = False) -> NotificationSettings:
        with self._lock:
            if self._settings is None or force:
                self._settings = self._loader()
            return replace(self._settings)

    def get(self) -> NotificationSettings:
        return self.load()

    def current(self) -> NotificationSettings:
        with self._lock:
            if self._settings is None:
                self._settings = self._loader()
            return self._settings

    def save(self, settings: NotificationSettings) -> NotificationSettings:
        updated = replace(settings)
        with self._lock:
            self._saver(updated)
            self._settings = self._loader()
            return replace(self._settings)

    def update(self, **changes) -> NotificationSettings:
        with self._lock:
            current = self.current()
            updated = replace(current, **changes)
            self._saver(updated)
            self._settings = updated
            return replace(updated)
