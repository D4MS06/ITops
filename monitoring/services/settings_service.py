from __future__ import annotations

from dataclasses import dataclass, replace
import ipaddress
import re
import ssl
from threading import RLock
from typing import Any, Callable

from monitoring.config.settings import NotificationSettings


@dataclass(frozen=True)
class ActiveDirectoryConnection:
    host: str
    dns_servers: tuple[str, ...]
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
        raw_dns = getattr(settings, "active_directory_dns_servers", "") or ""
        dns_servers = tuple(
            item.strip() for item in (raw_dns if isinstance(raw_dns, (list, tuple)) else str(raw_dns).replace(";", ",").split(","))
            if str(item).strip()
        )
        return ActiveDirectoryConnection(
            host=str(getattr(settings, "active_directory_host", "") or "").strip(),
            dns_servers=dns_servers,
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
    def _resolved_host(connection: ActiveDirectoryConnection) -> str:
        """Resolve LDAP names with the source's DNS servers, never system DNS."""
        try:
            ipaddress.ip_address(connection.host)
            return connection.host
        except ValueError:
            pass
        if not connection.dns_servers:
            return connection.host
        try:
            import dns.resolver  # type: ignore
        except ImportError as exc:  # pragma: no cover - deployment dependency
            raise RuntimeError("La dependance dnspython est requise pour utiliser les DNS propres a une synchronisation AD.") from exc
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = list(connection.dns_servers)
        resolver.timeout = 3.0
        resolver.lifetime = 8.0
        try:
            return str(resolver.resolve(connection.host, "A")[0])
        except Exception:
            try:
                return str(resolver.resolve(connection.host, "AAAA")[0])
            except Exception as exc:
                raise RuntimeError(f"Resolution DNS AD impossible pour {connection.host} via {', '.join(connection.dns_servers)}: {exc}") from exc

    @classmethod
    def _server(cls, ldap3, connection: ActiveDirectoryConnection):
        resolved_host = cls._resolved_host(connection)
        tls = ldap3.Tls(
            validate=ssl.CERT_REQUIRED if connection.validate_certificates else ssl.CERT_NONE,
            ca_certs_file=connection.ca_certificate_path or None,
            valid_names=[connection.host] if connection.validate_certificates and resolved_host != connection.host else None,
            sni=connection.host if resolved_host != connection.host else None,
        )
        return ldap3.Server(resolved_host, port=connection.port, use_ssl=connection.use_ssl, tls=tls)

    @staticmethod
    def _bind_identity(connection: ActiveDirectoryConnection) -> str:
        """Convertit un simple nom de compte en UPN, sans modifier les formats avances."""
        username = connection.bind_username.strip()
        # UPN, DN LDAP et identifiant NetBIOS restent sous le controle de l'administrateur.
        if "@" in username or "=" in username or "\\" in username:
            return username
        domain_parts = [
            match.group(1).strip()
            for match in re.finditer(r"(?:^|,)\s*DC\s*=\s*([^,]+)", connection.base_dn, flags=re.IGNORECASE)
            if match.group(1).strip()
        ]
        return f"{username}@{'.'.join(domain_parts)}" if domain_parts else username

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
        server = self._server(ldap3, connection)
        client = ldap3.Connection(server, user=self._bind_identity(connection), password=connection.bind_password, auto_bind=True)
        try:
            # A successful bind only validates the account.  Verify that the
            # configured search base actually exists and is readable as well.
            if not client.search(
                search_base=connection.base_dn,
                search_filter="(objectClass=*)",
                search_scope=ldap3.BASE,
                attributes=["distinguishedName"],
            ):
                result = dict(getattr(client, "result", {}) or {})
                detail = str(result.get("message") or result.get("description") or "base introuvable ou non accessible")
                raise RuntimeError(f"Base DN Active Directory invalide ou inaccessible ({connection.base_dn}) : {detail}")
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
        server = self._server(ldap3, connection)
        client = ldap3.Connection(server, user=self._bind_identity(connection), password=connection.bind_password, auto_bind=True)
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
