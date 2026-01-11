#!/usr/bin/env python3
"""
cleanup_test_data_keycloak.py
Removes test data created for performance testing in Keycloak.

Usage:
    python scripts/cleanup_test_data_keycloak.py

Configuration is read from .env file or environment variables.
"""

import os
import sys

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
CONFIG = {
    "base_url": os.getenv("BASE_URL", "http://localhost:8080"),
    "admin_username": os.getenv("ADMIN_USERNAME", "admin"),
    "admin_password": os.getenv("ADMIN_PASSWORD", "admin"),
    "admin_realm": os.getenv("ADMIN_REALM", "master"),
    "perf_realm": os.getenv("PERF_REALM", "perf"),
}


# Colors for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"  # No Color


def print_success(msg: str) -> None:
    print(f"{Colors.GREEN}{msg}{Colors.NC}")


def print_warning(msg: str) -> None:
    print(f"{Colors.YELLOW}{msg}{Colors.NC}")


def print_error(msg: str) -> None:
    print(f"{Colors.RED}{msg}{Colors.NC}", file=sys.stderr)


def get_admin_token() -> str:
    """Get admin access token from Keycloak using password grant."""
    print_warning("Getting admin access token...")

    # Keycloak uses admin-cli client in master realm for admin operations
    url = f"{CONFIG['base_url']}/realms/{CONFIG['admin_realm']}/protocol/openid-connect/token"

    data = {
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": CONFIG["admin_username"],
        "password": CONFIG["admin_password"],
    }

    try:
        response = requests.post(url, data=data, timeout=30)
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


def delete_realm(token: str, realm_name: str) -> bool:
    """Delete a realm and all its data in Keycloak."""
    print_warning(f"Deleting realm: {realm_name}...")

    # Keycloak Admin API endpoint for realm deletion
    url = f"{CONFIG['base_url']}/admin/realms/{realm_name}"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    try:
        response = requests.delete(url, headers=headers, timeout=30)

        if response.status_code in (200, 204):
            print_success(f"Realm '{realm_name}' deleted successfully")
            return True
        elif response.status_code == 404:
            print_warning(f"Realm '{realm_name}' not found (already deleted?)")
            return True
        else:
            print_error(f"Failed to delete realm. HTTP {response.status_code}: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print_error(f"Failed to delete realm: {e}")
        return False


def confirm_deletion() -> bool:
    """Ask user to confirm deletion."""
    print_warning(f"=== Keycloak Performance Test Data Cleanup ===")
    print(f"Base URL: {CONFIG['base_url']}")
    print(f"Realm to delete: {CONFIG['perf_realm']}")
    print()

    try:
        response = input(f"Are you sure you want to delete the '{CONFIG['perf_realm']}' realm and all its data? (y/N) ")
        return response.strip().lower() in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print()
        return False


def main() -> None:
    # Confirm deletion
    if not confirm_deletion():
        print("Cleanup cancelled.")
        sys.exit(0)

    print()

    # Step 1: Get admin token
    print_warning("Step 1: Authenticating as admin...")
    admin_token = get_admin_token()
    print()

    # Step 2: Delete performance test realm
    print_warning("Step 2: Deleting performance test realm...")
    delete_realm(admin_token, CONFIG["perf_realm"])
    print()

    print_success("=== Cleanup Complete ===")


if __name__ == "__main__":
    main()
