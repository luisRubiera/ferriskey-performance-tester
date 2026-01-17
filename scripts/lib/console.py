"""Console output utilities with colored output support."""

import sys


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"  # No Color


def print_success(msg: str) -> None:
    """Print a success message in green."""
    print(f"{Colors.GREEN}{msg}{Colors.NC}")


def print_warning(msg: str) -> None:
    """Print a warning message in yellow."""
    print(f"{Colors.YELLOW}{msg}{Colors.NC}")


def print_error(msg: str) -> None:
    """Print an error message in red to stderr."""
    print(f"{Colors.RED}{msg}{Colors.NC}", file=sys.stderr)
