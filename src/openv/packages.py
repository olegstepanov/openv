"""Platform detection and package manager abstraction (brew, apt, opkg)."""

from __future__ import annotations

import shutil
import subprocess
from enum import Enum


class PackageManager(Enum):
    """Supported platform package managers."""

    BREW = "brew"
    APT = "apt"
    OPKG = "opkg"


class InstallationError(Exception):
    """Raised when a package manager fails to install a package."""

    def __init__(self, package: str) -> None:
        super().__init__(f'Error installing package "{package}"')


def detect() -> PackageManager:
    """Detect the platform's package manager from PATH; raise if none found."""
    for pm in (PackageManager.BREW, PackageManager.APT, PackageManager.OPKG):
        if shutil.which(pm.value):
            return pm
    raise RuntimeError("No supported package manager (brew, apt-get or opkg) found. ")


def is_installed(pm: PackageManager, package: str) -> bool:
    """Return True if the package is already installed on the system."""
    match pm:
        case PackageManager.BREW:
            result = subprocess.run(  # noqa: S603
                ["brew", "list", "--formula", package],  # noqa: S607
                capture_output=True,
            )
            return result.returncode == 0
        case PackageManager.APT:
            result = subprocess.run(  # noqa: S603
                ["dpkg-query", "-W", "-f=${Status}", package],  # noqa: S607
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and "install ok installed" in result.stdout
        case PackageManager.OPKG:
            result = subprocess.run(  # noqa: S603
                ["opkg", "status", package],  # noqa: S607
                capture_output=True,
                text=True,
            )
            return (
                result.returncode == 0
                and "Status: install ok installed" in result.stdout
            )


def install_package(pm: PackageManager, package: str) -> None:
    """Install a package via the given package manager; skip if already installed."""
    if is_installed(pm, package):
        return
    try:
        match pm:
            case PackageManager.BREW:
                subprocess.run(["brew", "install", package], check=True)  # noqa: S603, S607
            case PackageManager.APT:
                subprocess.run(["apt-get", "install", "-y", package], check=True)  # noqa: S603, S607
            case PackageManager.OPKG:
                subprocess.run(["opkg", "install", package], check=True)  # noqa: S603, S607
    except subprocess.CalledProcessError as e:
        raise InstallationError(package) from e
