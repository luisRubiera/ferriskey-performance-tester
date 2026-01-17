"""
IAM Provider library for performance test data seeding.

Supports multiple IAM backends (FerrisKey, Keycloak) through a common interface.
"""

from .config import Config, load_config
from .console import Colors, print_error, print_success, print_warning
from .base_provider import IAMProvider
from .ferriskey_provider import FerrisKeyProvider
from .keycloak_provider import KeycloakProvider

__all__ = [
    "Config",
    "load_config",
    "Colors",
    "print_success",
    "print_warning",
    "print_error",
    "IAMProvider",
    "FerrisKeyProvider",
    "KeycloakProvider",
]
