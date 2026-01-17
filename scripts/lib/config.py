"""Configuration management for IAM performance testing."""

import os
import secrets
import string
from dataclasses import dataclass

from dotenv import load_dotenv


def generate_random_id(prefix: str = "perf-client-", length: int = 8) -> str:
    """Generate a random ID with the given prefix."""
    chars = string.ascii_lowercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(length))
    return f"{prefix}{suffix}"


@dataclass
class Config:
    """Configuration for IAM seeding operations."""

    # IAM provider selection
    iam_provider: str

    # Server connection
    base_url: str
    request_timeout: int

    # Admin authentication
    admin_username: str
    admin_password: str
    admin_realm: str

    # Admin client credentials (for FerrisKey - requires existing client in admin realm)
    admin_client_id: str | None
    admin_client_secret: str | None

    # Keycloak-specific
    keycloak_auth_client: str

    # Performance test realm
    perf_realm: str

    # Client configuration (can be auto-generated)
    client_id: str
    client_secret: str | None  # None means server will generate

    # User configuration
    user_count: int
    user_password: str
    user_prefix: str
    user_firstname: str
    user_lastname_prefix: str
    user_email_prefix: str
    user_email_domain: str


def load_config() -> Config:
    """Load configuration from environment variables."""
    load_dotenv()

    iam_provider = os.getenv("IAM_PROVIDER", "ferriskey").lower()

    # Set defaults based on provider
    if iam_provider == "keycloak":
        default_base_url = "http://localhost:8080"
        default_admin_realm = "master"
        default_perf_realm = "perf"
    else:  # ferriskey
        default_base_url = "http://localhost:3333"
        default_admin_realm = "master"
        default_perf_realm = "perf-realm"

    # Auto-generate client_id if not provided
    client_id_env = os.getenv("CLIENT_ID", "").strip()
    client_id = client_id_env if client_id_env else generate_random_id()

    # Client secret is optional - None means server will generate
    client_secret_env = os.getenv("CLIENT_SECRET", "").strip()
    client_secret = client_secret_env if client_secret_env else None

    # Admin client credentials (for FerrisKey authentication)
    admin_client_id_env = os.getenv("ADMIN_CLIENT_ID", "").strip()
    admin_client_id = admin_client_id_env if admin_client_id_env else None

    admin_client_secret_env = os.getenv("ADMIN_CLIENT_SECRET", "").strip()
    admin_client_secret = admin_client_secret_env if admin_client_secret_env else None

    return Config(
        # IAM provider
        iam_provider=iam_provider,
        # Server connection
        base_url=os.getenv("BASE_URL", default_base_url),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        # Admin authentication
        admin_username=os.getenv("ADMIN_USERNAME", "admin"),
        admin_password=os.getenv("ADMIN_PASSWORD", "admin"),
        admin_realm=os.getenv("ADMIN_REALM", default_admin_realm),
        # Admin client credentials (for FerrisKey)
        admin_client_id=admin_client_id,
        admin_client_secret=admin_client_secret,
        # Keycloak-specific
        keycloak_auth_client=os.getenv("KEYCLOAK_AUTH_CLIENT", "admin-cli"),
        # Performance test realm
        perf_realm=os.getenv("PERF_REALM", default_perf_realm),
        # Client configuration
        client_id=client_id,
        client_secret=client_secret,
        # User configuration
        user_count=int(os.getenv("USER_COUNT", "50")),
        user_password=os.getenv("USER_PASSWORD", "perf-password"),
        user_prefix=os.getenv("USER_PREFIX", "perf-user-"),
        user_firstname=os.getenv("USER_FIRSTNAME", "Perf"),
        user_lastname_prefix=os.getenv("USER_LASTNAME_PREFIX", "User"),
        user_email_prefix=os.getenv("USER_EMAIL_PREFIX", "perf"),
        user_email_domain=os.getenv("USER_EMAIL_DOMAIN", "test.local"),
    )
