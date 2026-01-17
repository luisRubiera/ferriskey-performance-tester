"""FerrisKey IAM provider implementation."""

import secrets
import string
import sys

import requests

from .base_provider import IAMProvider
from .config import Config
from .console import print_error, print_success, print_warning


def generate_random_secret(length: int = 16) -> str:
    """Generate a random client secret."""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


class FerrisKeyProvider(IAMProvider):
    """IAM provider implementation for FerrisKey."""

    def __init__(self, config: Config):
        """Initialize the FerrisKey provider."""
        super().__init__(config)

    @property
    def name(self) -> str:
        """Return the display name of this provider."""
        return "FerrisKey"

    def get_admin_token(self) -> str:
        """Get admin access token from FerrisKey using password grant."""
        print_warning("Getting admin access token...")

        # Use admin client credentials if provided, otherwise fail
        if not self.config.admin_client_id:
            print_error("ADMIN_CLIENT_ID is required for FerrisKey authentication")
            sys.exit(1)

        url = f"{self.config.base_url}/realms/{self.config.admin_realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "password",
            "client_id": self.config.admin_client_id,
            "username": self.config.admin_username,
            "password": self.config.admin_password,
        }

        # Only include client_secret for confidential clients
        if self.config.admin_client_secret:
            data["client_secret"] = self.config.admin_client_secret

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
        """Create a new realm in FerrisKey."""
        print_warning(f"Creating realm: {realm_name}...")

        url = f"{self.config.base_url}/realms"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        data = {"name": realm_name}

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=self.config.request_timeout
            )

            if response.status_code in (200, 201):
                print_success(f"Realm '{realm_name}' created successfully")
                return True
            elif response.status_code in (400, 409):
                print_warning(f"Realm '{realm_name}' may already exist (HTTP {response.status_code})")
                return True
            else:
                print_error(f"Failed to create realm. HTTP {response.status_code}: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print_error(f"Failed to create realm: {e}")
            return False

    def create_client(self, token: str, realm: str, client_data: dict) -> str | None:
        """Create a new client in FerrisKey."""
        client_id = client_data.get("client_id", "unknown")
        print_warning(f"Creating client: {client_id}...")

        url = f"{self.config.base_url}/realms/{realm}/clients"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Remove _comment field if present
        clean_data = {k: v for k, v in client_data.items() if not k.startswith("_")}

        try:
            response = requests.post(
                url, headers=headers, json=clean_data, timeout=self.config.request_timeout
            )

            if response.status_code in (200, 201):
                print_success(f"Client '{client_id}' created successfully")
                try:
                    result = response.json()
                    return result.get("data", {}).get("id") or result.get("id")
                except Exception:
                    return None
            elif response.status_code in (400, 409):
                print_warning(f"Client '{client_id}' may already exist (HTTP {response.status_code})")
                return None
            else:
                print_error(f"Failed to create client. HTTP {response.status_code}: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print_error(f"Failed to create client: {e}")
            return None

    def create_user(
        self,
        token: str,
        realm: str,
        username: str,
        firstname: str,
        lastname: str,
        email: str,
    ) -> str | None:
        """Create a new user in FerrisKey."""
        url = f"{self.config.base_url}/realms/{realm}/users"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        data = {
            "username": username,
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "email_verified": True,
        }

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=self.config.request_timeout
            )

            if response.status_code in (200, 201):
                try:
                    result = response.json()
                    return result.get("data", {}).get("id") or result.get("id")
                except Exception:
                    return None
            else:
                return None

        except requests.exceptions.RequestException:
            return None

    def set_user_password(
        self, token: str, realm: str, user_id: str, password: str
    ) -> bool:
        """Set password for a user in FerrisKey."""
        if not user_id:
            return False

        url = f"{self.config.base_url}/realms/{realm}/users/{user_id}/reset-password"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        data = {
            "temporary": False,
            "credential_type": "password",
            "value": password,
        }

        try:
            response = requests.put(
                url, headers=headers, json=data, timeout=self.config.request_timeout
            )
            return response.status_code in (200, 204)
        except requests.exceptions.RequestException:
            return False

    def get_client_secret(self, token: str, realm: str, client_uuid: str) -> str | None:
        """Get the client secret from FerrisKey."""
        url = f"{self.config.base_url}/realms/{realm}/clients/{client_uuid}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(url, headers=headers, timeout=self.config.request_timeout)
            if response.status_code == 200:
                data = response.json()
                # Secret is in data.secret or directly in secret
                return data.get("data", {}).get("secret") or data.get("secret")
        except requests.exceptions.RequestException:
            pass
        return None

    def create_default_client(self, token: str, realm: str) -> tuple[str | None, str | None]:
        """Create the default performance test client and retrieve server-generated secret."""
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

        client_uuid = self.create_client(token, realm, client_data)
        if not client_uuid:
            return None, None

        # FerrisKey generates its own secret - retrieve it from the server
        client_secret = self.get_client_secret(token, realm, client_uuid)
        return client_uuid, client_secret
