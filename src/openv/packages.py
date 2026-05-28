from __future__ import annotations

import shutil
import subprocess
from enum import Enum


class PackageManager(Enum):
    BREW = "brew"
    APT = "apt"
    OPKG = "opkg"


class InstallationError(Exception):
    def __init__(self, package: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.package = package


    def __str__(self):
        return f'Error installing package "{self.package}"'


def detect() -> PackageManager:
    for pm in (PackageManager.BREW, PackageManager.APT, PackageManager.OPKG):
        if shutil.which(pm.value):
            return pm
    raise RuntimeError(
        "No supported package manager (brew, apt-get or opkg) found. "
    )


def is_installed(pm: PackageManager, package: str) -> bool:
    match pm:
        case PackageManager.BREW:
            result = subprocess.run(
                ["brew", "list", "--formula", package],
                capture_output=True,
            )
            return result.returncode == 0
        case PackageManager.APT:
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", package],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and "install ok installed" in result.stdout
        case PackageManager.OPKG:
            result = subprocess.run(
                ["opkg", "status", package],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and "Status: install ok installed" in result.stdout


def install_package(pm: PackageManager, package: str) -> None:
    if is_installed(pm, package):
        return
    try:
        match pm:
            case PackageManager.BREW:
                subprocess.run(["brew", "install", package], check=True)
            case PackageManager.APT:
                subprocess.run(["apt-get", "install", "-y", package], check=True)
            case PackageManager.OPKG:
                subprocess.run(["opkg", "install", package], check=True)
    except subprocess.CalledProcessError as e:
        raise InstallationError(package, e)