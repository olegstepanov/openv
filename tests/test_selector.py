"""Tests for the tool selector status logic."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from openv.discovery import ToolInfo
from openv.selector import _tool_status, select_tools

if TYPE_CHECKING:
    from pathlib import Path


def _make_file(path: Path, content: str = "") -> Path:
    """Create a file at path with the given content, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestToolStatus:
    """Tests for the _tool_status() function."""

    def test_installed_when_is_installed_true(self, tmp_path: Path) -> None:
        """A tool reported as installed shows status 'installed'."""
        config_file = _make_file(tmp_path / "zsh" / ".zshrc")
        tool = ToolInfo(
            name="zsh",
            directory=tmp_path / "zsh",
            package_dependencies=["zsh"],
            config_files=[config_file],
        )

        status = _tool_status(tool, is_installed=True)

        assert status == "installed"

    def test_not_installed_when_is_installed_false_with_configs(
        self, tmp_path: Path
    ) -> None:
        """A tool with config files but not installed shows as 'partial'."""
        config_file = _make_file(tmp_path / "zsh" / ".zshrc")
        tool = ToolInfo(
            name="zsh",
            directory=tmp_path / "zsh",
            package_dependencies=["zsh"],
            config_files=[config_file],
        )

        status = _tool_status(tool, is_installed=False)

        assert status == "partial"

    def test_no_configs_when_tool_has_no_config_files(self, tmp_path: Path) -> None:
        """A tool with no config files shows as 'no configs'."""
        (tmp_path / "zsh").mkdir()
        tool = ToolInfo(
            name="zsh",
            directory=tmp_path / "zsh",
            package_dependencies=["zsh"],
            config_files=[],
        )

        status = _tool_status(tool, is_installed=False)

        assert status == "no configs"

    def test_scripts_only_tool_shows_non_idempotent(self, tmp_path: Path) -> None:
        """B1: a tool with install.sh and no configs is flagged as non-idempotent."""
        tool_directory = tmp_path / "ssh-agent"
        tool_directory.mkdir()
        install_script = tool_directory / "install.sh"
        install_script.write_text("#!/bin/sh\nexit 0\n")
        tool = ToolInfo(
            name="ssh-agent",
            directory=tool_directory,
            package_dependencies=["ssh-agent"],
            install_script=install_script,
            config_files=[],
        )

        status = _tool_status(tool, is_installed=False)

        assert status == "non-idempotent"


class TestSelectToolsIsInstalledCalledOnce:
    """Tests that installer.is_installed is called once per tool in select_tools."""

    def test_is_installed_called_once_per_tool(self, tmp_path: Path) -> None:
        """select_tools calls installer.is_installed exactly once per tool."""
        config_file = _make_file(tmp_path / "zsh" / ".zshrc")
        tool = ToolInfo(
            name="zsh",
            directory=tmp_path / "zsh",
            package_dependencies=["zsh"],
            config_files=[config_file],
        )
        pm = object()

        with (
            patch(
                "openv.selector.installer.is_installed", return_value=True
            ) as mock_is_installed,
            patch("openv.selector.questionary.checkbox") as mock_checkbox,
        ):
            mock_checkbox.return_value.ask.return_value = None
            select_tools([tool], pm, tmp_path)  # type: ignore[arg-type]

        mock_is_installed.assert_called_once_with(tool, pm, tmp_path)
