"""Tests for script execution and install orchestration in the installer."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from openv.discovery import ToolInfo
from openv.installer import (
    _run_script,
    install_tool,
    is_installed,
    is_scripts_only,
)
from openv.packages import PackageManager

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _write_script(directory: Path, name: str, content: str) -> Path:
    """Write an executable script file and return its path."""
    script = directory / name
    script.write_text(content)
    script.chmod(0o755)
    return script


def _make_tool(
    dotfiles_root: Path,
    name: str,
    config_files: list[str] | None = None,
    install_script_content: str | None = None,
    post_install_script_content: str | None = None,
) -> ToolInfo:
    """Build a ToolInfo on disk for installer tests."""
    tool_directory = dotfiles_root / name
    tool_directory.mkdir(parents=True, exist_ok=True)
    config_paths: list[Path] = []
    for config_file in config_files or []:
        path = tool_directory / config_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {config_file}\n")
        config_paths.append(path)

    install_script = (
        _write_script(tool_directory, "install.sh", install_script_content)
        if install_script_content is not None
        else None
    )

    post_install_script = (
        _write_script(tool_directory, "post-install.sh", post_install_script_content)
        if post_install_script_content is not None
        else None
    )

    return ToolInfo(
        name=name,
        directory=tool_directory,
        package_dependencies=[name],
        install_script=install_script,
        post_install_script=post_install_script,
        config_files=config_paths,
    )


class TestRunScript:
    """Tests for _run_script()."""

    def test_executable_script_runs_successfully(
        self, assessed_master: Callable[[str], Path]
    ) -> None:
        """An executable script is invoked via OS execution without error."""
        _run_script(assessed_master("#!/bin/sh\nexit 0\n"))

    def test_non_executable_script_raises_permission_error(
        self, tmp_path: Path
    ) -> None:
        """A script without the executable bit raises PermissionError before running."""
        script = tmp_path / "install.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o644)
        with pytest.raises(PermissionError, match="not executable"):
            _run_script(script)

    def test_script_with_nonzero_exit_raises_called_process_error(
        self, assessed_master: Callable[[str], Path]
    ) -> None:
        """A script that exits with a non-zero status raises CalledProcessError."""
        with pytest.raises(subprocess.CalledProcessError):
            _run_script(assessed_master("#!/bin/sh\nexit 1\n"))


class TestIsScriptsOnly:
    """Tests for the is_scripts_only() predicate."""

    def test_true_when_install_script_and_no_configs(self, tmp_path: Path) -> None:
        """True for a tool with install.sh and no config files."""
        tool = _make_tool(tmp_path, "ssh-agent", install_script_content="#!/bin/sh\n")
        assert is_scripts_only(tool) is True

    def test_true_when_post_install_script_and_no_configs(self, tmp_path: Path) -> None:
        """True for a tool with only post-install.sh and no config files."""
        tool = _make_tool(
            tmp_path, "service", post_install_script_content="#!/bin/sh\n"
        )
        assert is_scripts_only(tool) is True

    def test_false_when_scripts_with_configs(self, tmp_path: Path) -> None:
        """False when the tool also has config files (symlinks are the signal)."""
        tool = _make_tool(
            tmp_path,
            "zsh",
            config_files=[".zshrc"],
            install_script_content="#!/bin/sh\n",
        )
        assert is_scripts_only(tool) is False

    def test_false_when_no_scripts(self, tmp_path: Path) -> None:
        """False for a config- or package-only tool (no scripts)."""
        config_only = _make_tool(tmp_path, "zsh", config_files=[".zshrc"])
        package_only = _make_tool(tmp_path, "htop")
        assert is_scripts_only(config_only) is False
        assert is_scripts_only(package_only) is False


class TestIsInstalled:
    """Tests for installer.is_installed()."""

    def test_scripts_only_tool_is_never_installed(self, tmp_path: Path) -> None:
        """A scripts-only tool is not 'installed' before or after install_tool runs."""
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(
            tmp_path / "dotfiles",
            "ssh-agent",
            install_script_content="#!/bin/sh\nexit 0\n",
        )
        pm = MagicMock(spec=PackageManager)
        with (
            patch("openv.installer.packages.is_installed", return_value=True),
            patch("openv.installer.packages.install_package"),
            patch("openv.installer._run_script"),
        ):
            assert is_installed(tool, pm, home) is False
            install_tool(tool, pm, home, force=False)
            assert is_installed(tool, pm, home) is False

    def test_config_tool_installed_when_symlinks_and_package_present(
        self, tmp_path: Path
    ) -> None:
        """is_installed() returns True when package and symlinks are all in place."""
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(tmp_path / "dotfiles", "zsh", config_files=[".zshrc"])
        (home / ".zshrc").symlink_to(tool.config_files[0])
        pm = MagicMock(spec=PackageManager)
        with patch("openv.installer.packages.is_installed", return_value=True):
            assert is_installed(tool, pm, home) is True

    def test_package_only_tool_installed_when_package_present(
        self, tmp_path: Path
    ) -> None:
        """A tool with no configs or scripts is installed iff its package is present."""
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(tmp_path / "dotfiles", "htop")
        pm = MagicMock(spec=PackageManager)
        with patch("openv.installer.packages.is_installed", return_value=True):
            assert is_installed(tool, pm, home) is True


class TestInstallToolIdempotency:
    """Tests for install_tool()'s skip-the-whole-tool idempotency."""

    def test_skips_when_package_present_and_symlinks_valid(
        self, tmp_path: Path
    ) -> None:
        """install_tool() returns early; scripts are not re-run."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        ran: list[str] = []
        tool = _make_tool(
            dotfiles,
            "zsh",
            config_files=[".zshrc"],
            install_script_content="#!/bin/sh\nexit 0\n",
        )
        (home / ".zshrc").symlink_to(tool.config_files[0])
        pm = MagicMock(spec=PackageManager)

        with (
            patch("openv.installer.packages.is_installed", return_value=True),
            patch(
                "openv.installer._run_script",
                side_effect=lambda s: ran.append(str(s)),
            ),
        ):
            install_tool(tool, pm, home, force=False)

        assert ran == []

    def test_scripts_only_tool_runs_install_sh_when_package_present(
        self, tmp_path: Path
    ) -> None:
        """scripts-only tool runs install.sh even when its package is present."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        ran: list[str] = []
        tool = _make_tool(
            dotfiles,
            "ssh-agent",
            install_script_content="#!/bin/sh\nexit 0\n",
        )
        pm = MagicMock(spec=PackageManager)

        with (
            patch("openv.installer.packages.is_installed", return_value=True),
            patch(
                "openv.installer._run_script",
                side_effect=lambda s: ran.append(str(s)),
            ),
        ):
            install_tool(tool, pm, home, force=False)

        assert ran == [str(tool.install_script)]
