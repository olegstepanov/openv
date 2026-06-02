"""End-to-end integration tests for openv install."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from openv.cli import _cmd_install
from openv.packages import PackageManager

if TYPE_CHECKING:
    from pathlib import Path


class TestInstallIntegration:
    """End-to-end tests for _cmd_install() with a mocked package manager."""

    def test_install_explicit_tool_by_name(self, tmp_path: Path) -> None:
        """`openv install zsh` discovers, selects, and installs the named tool."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool_dir = dotfiles / "zsh"
        tool_dir.mkdir(parents=True)
        (tool_dir / ".zshrc").write_text("# zshrc\n")

        with (
            patch("openv.cli.Path.home", return_value=home),
            patch(
                "openv.installer.detect_package_manager",
                return_value=PackageManager.BREW,
            ),
            patch("openv.installer.packages.is_installed", return_value=True),
            patch("openv.installer.packages.install_package") as mock_install_package,
        ):
            _cmd_install(dotfiles=dotfiles, force=False, tool_names=["zsh"])

        assert (home / ".zshrc").is_symlink()
        assert mock_install_package.call_count == 0

    def test_install_tool_missing_package(self, tmp_path: Path) -> None:
        """`openv install zsh` installs the package when it is not already present."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool_dir = dotfiles / "zsh"
        tool_dir.mkdir(parents=True)
        (tool_dir / ".zshrc").write_text("# zshrc\n")

        with (
            patch("openv.cli.Path.home", return_value=home),
            patch(
                "openv.installer.detect_package_manager",
                return_value=PackageManager.BREW,
            ),
            patch("openv.installer.packages.is_installed", return_value=False),
            patch("openv.installer.packages.install_package") as mock_install_package,
        ):
            _cmd_install(dotfiles=dotfiles, force=False, tool_names=["zsh"])

        assert (home / ".zshrc").is_symlink()
        mock_install_package.assert_called_once_with(PackageManager.BREW, "zsh")
