"""Tests for the openv CLI entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from openv.cli import _cmd_install
from openv.packages import PackageManager

if TYPE_CHECKING:
    from pathlib import Path


class TestCliUnknownToolError:
    """Tests for unknown tool name validation in _cmd_install."""

    def test_install_aborts_on_unknown_tool_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Unknown tool name exits non-zero with a clear message."""
        dotfiles = tmp_path / "dotfiles"
        (dotfiles / "zsh").mkdir(parents=True)

        with (
            patch("openv.cli.detect_package_manager", return_value=PackageManager.BREW),
            pytest.raises(SystemExit) as exit_info,
        ):
            _cmd_install(dotfiles=dotfiles, force=False, tool_names=["bogustool"])

        assert exit_info.value.code == 2
        err = capsys.readouterr().err
        assert "Unknown tool(s): bogustool" in err
