"""Tests for platform detection and package manager wrappers."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from openv.packages import (
    InstallationError,
    PackageManager,
    detect,
    install_package,
    is_installed,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def _completed(
    returncode: int = 0, stdout: str = ""
) -> subprocess.CompletedProcess[str]:
    """Build a CompletedProcess for mocking subprocess.run."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


class TestDetect:
    """Tests for detect()."""

    def test_returns_brew_when_brew_on_path(self) -> None:
        """detect() returns BREW when only brew is on PATH."""

        def fake_which(name: str) -> str | None:
            return "/usr/local/bin/brew" if name == "brew" else None

        with patch("openv.packages.shutil.which", side_effect=fake_which):
            assert detect() is PackageManager.BREW

    def test_returns_apt_when_apt_on_path(self) -> None:
        """detect() returns APT when only apt is on PATH."""

        def fake_which(name: str) -> str | None:
            return "/usr/bin/apt" if name == "apt" else None

        with patch("openv.packages.shutil.which", side_effect=fake_which):
            assert detect() is PackageManager.APT

    def test_returns_opkg_when_opkg_on_path(self) -> None:
        """detect() returns OPKG when only opkg is on PATH."""

        def fake_which(name: str) -> str | None:
            return "/usr/bin/opkg" if name == "opkg" else None

        with patch("openv.packages.shutil.which", side_effect=fake_which):
            assert detect() is PackageManager.OPKG

    def test_raises_when_no_package_manager_found(self) -> None:
        """detect() raises RuntimeError when no manager is on PATH."""
        with (
            patch("openv.packages.shutil.which", return_value=None),
            pytest.raises(RuntimeError, match="No supported package manager"),
        ):
            detect()


class TestIsInstalled:
    """Tests for is_installed()."""

    def test_brew_returns_true_when_formula_listed(self) -> None:
        """is_installed(BREW) returns True when brew list exits 0."""
        with patch(
            "openv.packages.subprocess.run", return_value=_completed(returncode=0)
        ) as run:
            assert is_installed(PackageManager.BREW, "git") is True
            assert run.call_args.args[0] == ["brew", "list", "--formula", "git"]

    def test_brew_returns_false_when_formula_not_listed(self) -> None:
        """is_installed(BREW) returns False on non-zero exit."""
        with patch(
            "openv.packages.subprocess.run", return_value=_completed(returncode=1)
        ):
            assert is_installed(PackageManager.BREW, "ghost") is False

    def test_apt_requires_install_ok_installed_status(self) -> None:
        """is_installed(APT) requires the dpkg-query install marker in stdout."""
        with patch(
            "openv.packages.subprocess.run",
            return_value=_completed(returncode=0, stdout="install ok installed"),
        ):
            assert is_installed(PackageManager.APT, "git") is True

    def test_apt_returns_false_when_status_missing(self) -> None:
        """is_installed(APT) returns False when status marker is absent."""
        with patch(
            "openv.packages.subprocess.run",
            return_value=_completed(returncode=0, stdout="deinstall ok config-files"),
        ):
            assert is_installed(PackageManager.APT, "git") is False

    def test_opkg_requires_status_line(self) -> None:
        """is_installed(OPKG) requires the exact 'Status: install ok installed' line."""
        with patch(
            "openv.packages.subprocess.run",
            return_value=_completed(
                returncode=0, stdout="Package: git\nStatus: install ok installed\n"
            ),
        ):
            assert is_installed(PackageManager.OPKG, "git") is True


class TestInstallPackage:
    """Tests for install_package()."""

    def test_skips_when_already_installed(self) -> None:
        """install_package() does nothing when is_installed returns True."""
        with (
            patch("openv.packages.is_installed", return_value=True),
            patch("openv.packages.subprocess.run") as run,
        ):
            install_package(PackageManager.BREW, "git")
            assert run.call_count == 0

    def test_runs_brew_install_when_missing(self) -> None:
        """install_package(BREW) runs brew install when the package is absent."""
        with (
            patch("openv.packages.is_installed", return_value=False),
            patch("openv.packages.subprocess.run", return_value=_completed()) as run,
        ):
            install_package(PackageManager.BREW, "git")
            args: Sequence[str] = run.call_args.args[0]
            assert list(args) == ["brew", "install", "git"]

    def test_runs_apt_install_when_missing(self) -> None:
        """install_package(APT) runs apt-get install -y when the package is absent."""
        with (
            patch("openv.packages.is_installed", return_value=False),
            patch("openv.packages.subprocess.run", return_value=_completed()) as run,
        ):
            install_package(PackageManager.APT, "git")
            assert list(run.call_args.args[0]) == ["apt-get", "install", "-y", "git"]

    def test_raises_installation_error_on_failure(self) -> None:
        """install_package() wraps CalledProcessError in InstallationError."""
        with (
            patch("openv.packages.is_installed", return_value=False),
            patch(
                "openv.packages.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, ["brew"]),
            ),
            pytest.raises(InstallationError, match='Error installing package "ghost"'),
        ):
            install_package(PackageManager.BREW, "ghost")
