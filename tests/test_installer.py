"""Tests for script execution and install orchestration in the installer."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from openv.cli import _cmd_install
from openv.discovery import ToolInfo
from openv.installer import (
    _run_script,
    install_tool,
    is_installed,
    scripts_cannot_be_verified,
)
from openv.packages import PackageManager

if TYPE_CHECKING:
    from pathlib import Path


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

    install_script: Path | None = None
    if install_script_content is not None:
        install_script = tool_directory / "install.sh"
        install_script.write_text(install_script_content)
        install_script.chmod(0o755)

    post_install_script: Path | None = None
    if post_install_script_content is not None:
        post_install_script = tool_directory / "post-install.sh"
        post_install_script.write_text(post_install_script_content)
        post_install_script.chmod(0o755)

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

    def test_executable_script_runs_successfully(self, tmp_path: Path) -> None:
        """An executable script is invoked via OS execution without error."""
        script = tmp_path / "install.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o755)
        _run_script(script)

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
        self, tmp_path: Path
    ) -> None:
        """A script that exits with a non-zero status raises CalledProcessError."""
        script = tmp_path / "install.sh"
        script.write_text("#!/bin/sh\nexit 1\n")
        script.chmod(0o755)
        with pytest.raises(subprocess.CalledProcessError):
            _run_script(script)


class TestScriptsCannotBeVerified:
    """Tests for the scripts_cannot_be_verified() predicate."""

    def test_true_when_install_script_and_no_configs(self, tmp_path: Path) -> None:
        """True for a tool with install.sh and no config files."""
        tool = _make_tool(tmp_path, "ssh-agent", install_script_content="#!/bin/sh\n")
        assert scripts_cannot_be_verified(tool) is True

    def test_true_when_post_install_script_and_no_configs(self, tmp_path: Path) -> None:
        """True for a tool with only post-install.sh and no config files."""
        tool = _make_tool(
            tmp_path, "service", post_install_script_content="#!/bin/sh\n"
        )
        assert scripts_cannot_be_verified(tool) is True

    def test_false_when_scripts_with_configs(self, tmp_path: Path) -> None:
        """False when the tool also has config files (symlinks are the signal)."""
        tool = _make_tool(
            tmp_path,
            "zsh",
            config_files=[".zshrc"],
            install_script_content="#!/bin/sh\n",
        )
        assert scripts_cannot_be_verified(tool) is False

    def test_false_when_no_scripts(self, tmp_path: Path) -> None:
        """False for a config- or package-only tool (no scripts)."""
        config_only = _make_tool(tmp_path, "zsh", config_files=[".zshrc"])
        package_only = _make_tool(tmp_path, "htop")
        assert scripts_cannot_be_verified(config_only) is False
        assert scripts_cannot_be_verified(package_only) is False


class TestIsInstalled:
    """Tests for installer.is_installed()."""

    def test_scripts_only_tool_is_never_installed(self, tmp_path: Path) -> None:
        """B1: scripts-only tool is not 'installed' even if its package is present."""
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(
            tmp_path / "dotfiles",
            "ssh-agent",
            install_script_content="#!/bin/sh\nexit 0\n",
        )
        pm = MagicMock(spec=PackageManager)
        with patch("openv.installer.packages.is_installed", return_value=True):
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
        """B1: scripts-only tool runs install.sh even when its package is present."""
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


class TestCmdInstallIntegration:
    """End-to-end tests for _cmd_install() with a mocked package manager."""

    def test_install_explicit_tool_by_name(self, tmp_path: Path) -> None:
        """`openv install zsh` discovers, selects, and installs the named tool."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        _make_tool(dotfiles, "zsh", config_files=[".zshrc"])

        with (
            patch("openv.cli.Path.home", return_value=home),
            patch("openv.cli.detect", return_value=PackageManager.BREW),
            patch("openv.installer.packages.is_installed", return_value=True),
            patch("openv.installer.packages.install_package") as mock_install_package,
        ):
            _cmd_install(dotfiles=dotfiles, force=False, tool_names=["zsh"])

        assert (home / ".zshrc").is_symlink()
        assert mock_install_package.call_count == 0

    def test_install_aborts_on_unknown_tool_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """B2: unknown tool name exits non-zero with a clear message."""
        dotfiles = tmp_path / "dotfiles"
        _make_tool(dotfiles, "zsh", config_files=[".zshrc"])

        with (
            patch("openv.cli.detect", return_value=PackageManager.BREW),
            pytest.raises(SystemExit) as exit_info,
        ):
            _cmd_install(dotfiles=dotfiles, force=False, tool_names=["bogustool"])

        assert exit_info.value.code == 2
        err = capsys.readouterr().err
        assert "Unknown tool(s): bogustool" in err

    def test_install_runs_install_sh_for_scripts_only_tool(
        self, tmp_path: Path
    ) -> None:
        """B1 end-to-end: scripts-only tool with pre-installed pkg runs install.sh."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        ran: list[str] = []
        tool = _make_tool(
            dotfiles,
            "ssh-agent",
            install_script_content="#!/bin/sh\nexit 0\n",
        )

        with (
            patch("openv.cli.Path.home", return_value=home),
            patch("openv.cli.detect", return_value=PackageManager.BREW),
            patch("openv.installer.packages.is_installed", return_value=True),
            patch(
                "openv.installer._run_script",
                side_effect=lambda s: ran.append(str(s)),
            ),
        ):
            _cmd_install(dotfiles=dotfiles, force=False, tool_names=["ssh-agent"])

        assert ran == [str(tool.install_script)]
