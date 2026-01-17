"""Keycloak IAM provider implementation."""

import sys

import requests

from .base_provider import IAMProvider
from .config import Config
from .console import print_error, print_success, print_warning


class KeycloakProvider(IAMProvider):
    """IAM provider implementation for Keycloak."""

    def __init__(self, config: Config):
        """Initialize the Keycloak provider."""
        super().__init__(config)

    @property
    def name(self) -> str:
        """Return the display name of this provider."""
        return "Keycloak"

    def get_admin_token(self) -> str:
        """Get admin access token from Keycloak using password grant."""
        print_warning("Getting admin access token...")

        url = f"{self.config.base_url}/realms/{self.config.admin_realm}/protocol/openid-connect/token"

        # Keycloak uses admin-cli client for admin operations
        data = {
            "grant_type": "password",
            "client_id": self.config.keycloak_auth_client,
            "username": self.config.admin_username,
            "password": self.config.admin_password,
        }

        try:
            response = requests.post(url, data=data, timeout=self.config.request_timeout)
            response.raise_for_status()
            token = response.json().get("access_token")

            if not token:
                print_error(f"No access_token in response: {response.text}")
                sys.exit(1)

            print_success("Authentication successful")
            return token

        except requests.exceptions.RequestException as e:
            print_error(f"Failed to get admin token: {e}")
            sys.exit(1)

    def create_realm(self, token: str, realm_name: str) -> bool:
        """Create a new realm in Keycloak."""
        print_warning(f"Creating realm: {realm_name}...")

        # Keycloak Admin API endpoint
        url = f"{self.config.base_url}/admin/realms"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        data = {
            "realm": realm_name,
            "enabled": True,
            "displayName": f"{realm_name} Performance Testing",
        }

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=self.config.request_timeout
            )

            if response.status_code in (200, 201, 204):
                print_success(f"Realm '{realm_name}' created successfully")
                return True
            elif response.status_code == 409:
                print_warning(f"Realm '{realm_name}' already exists")
                return True
            else:
                print_error(f"Failed to create realm. HTTP {response.status_code}: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print_error(f"Failed to create realm: {e}")
            return False

    def create_client(self, token: str, realm: str, client_data: dict) -> str | None:
        """Create a new client in Keycloak. Returns client UUID if successful."""
        client_id = client_data.get("client_id", "unknown")
        print_warning(f"Creating client: {client_id}...")

        # Keycloak Admin API endpoint
        url = f"{self.config.base_url}/admin/realms/{realm}/clients"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Transform to Keycloak format (camelCase)
        # Note: Don't set secret - Keycloak generates it
        keycloak_client = {
            "clientId": client_data.get("client_id"),
            "name": client_data.get("name"),
            "enabled": client_data.get("enabled", True),
            "protocol": client_data.get("protocol", "openid-connect"),
            "publicClient": client_data.get("public_client", False),
            "serviceAccountsEnabled": client_data.get("service_account_enabled", False),
            "directAccessGrantsEnabled": client_data.get("direct_access_grants_enabled", True),
            "standardFlowEnabled": True,
        }

        try:
            response = requests.post(
                url, headers=headers, json=keycloak_client, timeout=self.config.request_timeout
            )

            if response.status_code in (200, 201, 204):
                print_success(f"Client '{client_id}' created successfully")
                # Get client UUID from Location header
                location = response.headers.get("Location", "")
                if location:
                    return location.split("/")[-1]
                return None
            elif response.status_code == 409:
                print_warning(f"Client '{client_id}' already exists")
                # Try to get existing client UUID
                return self._get_client_uuid(token, realm, client_id)
            else:
                print_error(f"Failed to create client. HTTP {response.status_code}: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print_error(f"Failed to create client: {e}")
            return None

    def _get_client_uuid(self, token: str, realm: str, client_id: str) -> str | None:
        """Get the UUID of an existing client by its clientId."""
        url = f"{self.config.base_url}/admin/realms/{realm}/clients"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"clientId": client_id}

        try:
            response = requests.get(
                url, headers=headers, params=params, timeout=self.config.request_timeout
            )
            if response.status_code == 200:
                clients = response.json()
                if clients:
                    return clients[0].get("id")
            return None
        except requests.exceptions.RequestException:
            return None

    def get_client_secret(self, token: str, realm: str, client_uuid: str) -> str | None:
        """Get the client secret for a confidential client."""
        url = f"{self.config.base_url}/admin/realms/{realm}/clients/{client_uuid}/client-secret"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(
                url, headers=headers, timeout=self.config.request_timeout
            )
            if response.status_code == 200:
                return response.json().get("value")
            return None
        except requests.exceptions.RequestException:
            return None

    def generate_client_secret(self, token: str, realm: str, client_uuid: str) -> str | None:
        """Generate (or regenerate) a client secret for a confidential client."""
        url = f"{self.config.base_url}/admin/realms/{realm}/clients/{client_uuid}/client-secret"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.post(
                url, headers=headers, timeout=self.config.request_timeout
            )
            if response.status_code == 200:
                return response.json().get("value")
            return None
        except requests.exceptions.RequestException:
            return None

    def create_default_client(self, token: str, realm: str) -> tuple[str | None, str | None]:
        """
        Create the default performance test client and retrieve its secret.

        Returns:
            Tuple of (client_uuid, client_secret) if successful, (None, None) otherwise.
        """
        client_data = {
            "name": "Performance Test Client",
            "client_id": self.config.client_id,
            "client_type": "confidential",
            "service_account_enabled": True,
            "public_client": False,
            "protocol": "openid-connect",
            "enabled": True,
            "direct_access_grants_enabled": True,
        }

        # Create the client
        client_uuid = self.create_client(token, realm, client_data)

        if not client_uuid:
            return None, None

        # Get or generate the client secret
        secret = self.get_client_secret(token, realm, client_uuid)

        if not secret:
            print_warning("No secret found, generating new secret...")
            secret = self.generate_client_secret(token, realm, client_uuid)

        if secret:
            print_success(f"Client secret retrieved successfully")
        else:
            print_error("Failed to retrieve client secret")

        return client_uuid, secret

    def create_user(
        self,
        token: str,
        realm: str,
        username: str,
        firstname: str,
        lastname: str,
        email: str,
    ) -> str | None:
        """Create a new user in Keycloak."""
        # Keycloak Admin API endpoint
        url = f"{self.config.base_url}/admin/realms/{realm}/users"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        # Keycloak uses camelCase
        data = {
            "username": username,
            "firstName": firstname,
            "lastName": lastname,
            "email": email,
            "emailVerified": True,
            "enabled": True,
        }

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=self.config.request_timeout
            )

            if response.status_code in (200, 201, 204):
                # Get user ID from Location header
                location = response.headers.get("Location", "")
                if location:
                    return location.split("/")[-1]
                return None
            else:
                return None

        except requests.exceptions.RequestException:
            return None

    def set_user_password(
        self, token: str, realm: str, user_id: str, password: str
    ) -> bool:
        """Set password for a user in Keycloak."""
        if not user_id:
            return False

        # Keycloak Admin API endpoint
        url = f"{self.config.base_url}/admin/realms/{realm}/users/{user_id}/reset-password"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        # Keycloak password format
        data = {
            "type": "password",
            "value": password,
            "temporary": False,
        }

        try:
            response = requests.put(
                url, headers=headers, json=data, timeout=self.config.request_timeout
            )
            return response.status_code in (200, 204)
        except requests.exceptions.RequestException:
            return False
