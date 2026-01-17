"""Abstract base class for IAM providers."""

from abc import ABC, abstractmethod

from .config import Config


class IAMProvider(ABC):
    """Abstract base class for IAM provider implementations."""

    def __init__(self, config: Config):
        """Initialize the provider with configuration."""
        self.config = config
        self._token: str | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the display name of this provider."""
        pass

    @abstractmethod
    def get_admin_token(self) -> str:
        """
        Authenticate and return an admin access token.

        Returns:
            The access token string.

        Raises:
            SystemExit: If authentication fails.
        """
        pass

    @abstractmethod
    def create_realm(self, token: str, realm_name: str) -> bool:
        """
        Create a new realm.

        Args:
            token: Admin access token.
            realm_name: Name of the realm to create.

        Returns:
            True if successful or realm already exists, False otherwise.
        """
        pass

    @abstractmethod
    def create_client(self, token: str, realm: str, client_data: dict) -> str | None:
        """
        Create a new OAuth2 client.

        Args:
            token: Admin access token.
            realm: Realm name.
            client_data: Client configuration from fixture file.

        Returns:
            Client UUID if successful, None otherwise.
        """
        pass

    def create_default_client(self, token: str, realm: str) -> tuple[str | None, str | None]:
        """
        Create the default performance test client from env configuration.

        Uses CLIENT_ID from config to create a confidential client suitable
        for performance testing (supports client_credentials and password grants).

        Args:
            token: Admin access token.
            realm: Realm name.

        Returns:
            Tuple of (client_uuid, client_secret). Secret may be None if
            the provider doesn't support secret retrieval, or the configured
            secret if set by the provider.
        """
        client_data = {
            "name": "Performance Test Client",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "client_type": "confidential",
            "service_account_enabled": True,
            "public_client": False,
            "protocol": "openid-connect",
            "enabled": True,
            "direct_access_grants_enabled": True,
        }
        client_uuid = self.create_client(token, realm, client_data)
        # Default implementation returns configured secret
        # Subclasses may override to retrieve server-generated secret
        return client_uuid, self.config.client_secret if client_uuid else None

    @abstractmethod
    def create_user(
        self,
        token: str,
        realm: str,
        username: str,
        firstname: str,
        lastname: str,
        email: str,
    ) -> str | None:
        """
        Create a new user.

        Args:
            token: Admin access token.
            realm: Realm name.
            username: Username for the new user.
            firstname: First name.
            lastname: Last name.
            email: Email address.

        Returns:
            User UUID if successful, None otherwise.
        """
        pass

    @abstractmethod
    def set_user_password(
        self, token: str, realm: str, user_id: str, password: str
    ) -> bool:
        """
        Set password for a user.

        Args:
            token: Admin access token.
            realm: Realm name.
            user_id: User UUID.
            password: Password to set.

        Returns:
            True if successful, False otherwise.
        """
        pass
