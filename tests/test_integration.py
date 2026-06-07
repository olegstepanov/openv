"""End-to-end integration tests for openv install."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from openv.cli import _cmd_install
from openv.packages import PackageManager

if TYPE_CHECKING:
    from collections.abc import Callable
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

    def test_install_resolves_dependency_order_and_symlinks(
        self, tmp_path: Path, assessed_master: Callable[[str], Path]
    ) -> None:
        """A real discovery → dependency-resolution → stow chain runs end to end.

        Builds a temp dotfiles repository with two tools where ``bar`` depends on
        ``bash`` (inferred from ``bar``'s ``#!/usr/bin/env bash`` install script,
        which matches the ``bash`` tool's name). Only the package layer is mocked;
        discovery, topological ordering, and symlinking run for real. The test
        selects only the dependent tool to also exercise transitive expansion.
        """
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()

        bash_dir = dotfiles / "bash"
        bash_dir.mkdir(parents=True)
        bash_config = bash_dir / ".bashrc"
        bash_config.write_text("# bashrc\n")

        bar_dir = dotfiles / "bar"
        bar_dir.mkdir(parents=True)
        bar_config = bar_dir / ".barrc"
        bar_config.write_text("# barrc\n")
        bar_install_script = bar_dir / "install.sh"
        bar_install_script.symlink_to(assessed_master("#!/usr/bin/env bash\nexit 0\n"))

        with (
            patch("openv.cli.Path.home", return_value=home),
            patch(
                "openv.installer.detect_package_manager",
                return_value=PackageManager.BREW,
            ),
            patch("openv.installer.packages.is_installed", return_value=False),
            patch("openv.installer.packages.install_package") as mock_install_package,
        ):
            _cmd_install(dotfiles=dotfiles, force=False, tool_names=["bar"])

        # (a) Real symlinks were created pointing at the real dotfiles configs.
        bash_link = home / ".bashrc"
        bar_link = home / ".barrc"
        assert bash_link.is_symlink()
        assert bar_link.is_symlink()
        assert bash_link.resolve() == bash_config.resolve()
        assert bar_link.resolve() == bar_config.resolve()

        # (b) Packages were installed in topological order: the dependency
        # (`bash`) before the dependent (`bar`). The per-tool package list comes
        # from a set, so its internal order is nondeterministic; assert on first
        # occurrence rather than an exact sequence.
        installed_packages = [
            call.args[1] for call in mock_install_package.call_args_list
        ]
        assert "bash" in installed_packages
        assert "bar" in installed_packages
        assert installed_packages.index("bash") < installed_packages.index("bar")
