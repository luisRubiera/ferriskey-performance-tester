#!/usr/bin/env python3
"""
seed_test_data_keycloak.py
Seeds Keycloak with test data for performance testing.

Usage:
    python scripts/seed_test_data_keycloak.py

Configuration is read from .env file or environment variables.
"""

import json
import os
import sys
from pathlib import Path

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
    "client_id": os.getenv("CLIENT_ID", "perf-client"),
    "client_secret": os.getenv("CLIENT_SECRET", "perf-client-secret"),
    "user_count": int(os.getenv("USER_COUNT", "50")),
    "user_password": os.getenv("USER_PASSWORD", "perf-password"),
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


def create_realm(token: str, realm_name: str) -> bool:
    """Create a new realm in Keycloak."""
    print_warning(f"Creating realm: {realm_name}...")

    # Keycloak Admin API endpoint for realms
    url = f"{CONFIG['base_url']}/admin/realms"
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
        response = requests.post(url, headers=headers, json=data, timeout=30)

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


def create_client(token: str, realm: str, client_data: dict) -> str | None:
    """Create a new client in Keycloak. Returns client UUID if successful."""
    client_id = client_data.get("client_id", "unknown")
    print_warning(f"Creating client: {client_id}...")

    # Keycloak Admin API endpoint for clients
    url = f"{CONFIG['base_url']}/admin/realms/{realm}/clients"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Transform to Keycloak format
    keycloak_client = {
        "clientId": client_data.get("client_id"),
        "name": client_data.get("name"),
        "enabled": client_data.get("enabled", True),
        "protocol": client_data.get("protocol", "openid-connect"),
        "publicClient": client_data.get("public_client", False),
        "serviceAccountsEnabled": client_data.get("service_account_enabled", False),
        "directAccessGrantsEnabled": client_data.get("direct_access_grants_enabled", True),
        "standardFlowEnabled": True,
        "secret": CONFIG["client_secret"],
    }

    try:
        response = requests.post(url, headers=headers, json=keycloak_client, timeout=30)

        if response.status_code in (200, 201, 204):
            print_success(f"Client '{client_id}' created successfully")
            # Get client UUID from Location header or fetch it
            location = response.headers.get("Location", "")
            if location:
                return location.split("/")[-1]
            return None
        elif response.status_code == 409:
            print_warning(f"Client '{client_id}' already exists")
            return None
        else:
            print_error(f"Failed to create client. HTTP {response.status_code}: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print_error(f"Failed to create client: {e}")
        return None


def create_user(token: str, realm: str, username: str, firstname: str, lastname: str, email: str) -> str | None:
    """Create a new user in Keycloak. Returns user UUID if successful."""
    # Keycloak Admin API endpoint for users
    url = f"{CONFIG['base_url']}/admin/realms/{realm}/users"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = {
        "username": username,
        "firstName": firstname,
        "lastName": lastname,
        "email": email,
        "emailVerified": True,
        "enabled": True,
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code in (200, 201, 204):
            # Get user ID from Location header
            location = response.headers.get("Location", "")
            if location:
                return location.split("/")[-1]
            return None
        elif response.status_code == 409:
            # User already exists
            return None
        else:
            return None

    except requests.exceptions.RequestException:
        return None


def set_user_password(token: str, realm: str, user_id: str, password: str) -> bool:
    """Set password for a user in Keycloak."""
    if not user_id:
        return False

    # Keycloak Admin API endpoint for resetting password
    url = f"{CONFIG['base_url']}/admin/realms/{realm}/users/{user_id}/reset-password"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = {
        "type": "password",
        "value": password,
        "temporary": False,
    }

    try:
        response = requests.put(url, headers=headers, json=data, timeout=30)
        return response.status_code in (200, 204)
    except requests.exceptions.RequestException:
        return False


def load_clients_fixture() -> list[dict]:
    """Load clients from fixture file."""
    script_dir = Path(__file__).parent
    clients_file = script_dir.parent / "data" / "clients.json"

    if clients_file.exists():
        with open(clients_file, "r") as f:
            return json.load(f)
    else:
        print_warning(f"clients.json not found at {clients_file}")
        return []


def main() -> None:
    print_success("=== Keycloak Performance Test Data Seeding ===")
    print(f"Base URL: {CONFIG['base_url']}")
    print(f"Admin Realm: {CONFIG['admin_realm']}")
    print(f"Perf Realm: {CONFIG['perf_realm']}")
    print(f"User Count: {CONFIG['user_count']}")
    print()

    # Step 1: Get admin token
    print_warning("Step 1: Authenticating as admin...")
    admin_token = get_admin_token()
    print()

    # Step 2: Create performance test realm
    print_warning("Step 2: Creating performance test realm...")
    create_realm(admin_token, CONFIG["perf_realm"])
    print()

    # Step 3: Create test clients
    print_warning("Step 3: Creating test clients...")
    clients = load_clients_fixture()
    for client_data in clients:
        create_client(admin_token, CONFIG["perf_realm"], client_data)
    print()

    # Step 4: Create test users
    print_warning(f"Step 4: Creating test users ({CONFIG['user_count']} users)...")
    created = 0
    failed = 0

    for i in range(1, CONFIG["user_count"] + 1):
        padded = f"{i:03d}"
        username = f"perf-user-{padded}"
        firstname = "Perf"
        lastname = f"User{padded}"
        email = f"perf{padded}@test.local"

        # Show progress every 10 users
        if i % 10 == 0 or i == CONFIG["user_count"]:
            print(f"  Creating users... {i}/{CONFIG['user_count']}")

        user_id = create_user(admin_token, CONFIG["perf_realm"], username, firstname, lastname, email)

        if user_id:
            # Set password for the user
            if set_user_password(admin_token, CONFIG["perf_realm"], user_id, CONFIG["user_password"]):
                created += 1
            else:
                failed += 1
        else:
            failed += 1

    print_success(f"Users created: {created}, Skipped/Failed: {failed}")
    print()

    # Summary
    print_success("=== Seeding Complete ===")
    print()
    print("Test configuration:")
    print(f"  Realm: {CONFIG['perf_realm']}")
    print(f"  Client ID: {CONFIG['client_id']}")
    print(f"  Client Secret: {CONFIG['client_secret']}")
    print(f"  Test users: perf-user-001 through perf-user-{CONFIG['user_count']:03d}")
    print(f"  User password: {CONFIG['user_password']}")
    print()
    print("To run tests:")
    print(f"  set -a && source .env && set +a && k6 run k6/scenarios/token_client_credentials.js")


if __name__ == "__main__":
    main()
