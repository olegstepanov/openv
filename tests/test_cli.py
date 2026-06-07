"""Tests for the openv CLI entry point."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from openv.cli import _cmd_install, main


class TestCliUnknownToolError:
    """Tests for unknown tool name validation in _cmd_install."""

    def test_install_aborts_on_unknown_tool_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Unknown tool name exits non-zero with a clear message."""
        dotfiles = tmp_path / "dotfiles"
        (dotfiles / "zsh").mkdir(parents=True)

        with pytest.raises(SystemExit) as exit_info:
            _cmd_install(dotfiles=dotfiles, force=False, tool_names=["bogustool"])

        assert exit_info.value.code == 2
        err = capsys.readouterr().err
        assert "Unknown tool(s): bogustool" in err


class TestMainArgumentParsing:
    """Tests for argument parsing and subcommand dispatch in main()."""

    def test_no_subcommand_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Invoking without a subcommand exits (subparsers are required)."""
        monkeypatch.setattr(sys, "argv", ["openv"])

        with pytest.raises(SystemExit):
            main()

    def test_install_dispatch_passes_expanded_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Install dispatches to _cmd_install with expanded path and tools."""
        dotfiles_arg = str(tmp_path / "dotfiles")
        monkeypatch.setattr(
            sys, "argv", ["openv", "install", "--dotfiles", dotfiles_arg, "zsh"]
        )

        with patch("openv.cli._cmd_install") as cmd_install:
            main()

        cmd_install.assert_called_once_with(
            dotfiles=Path(dotfiles_arg).expanduser(),
            force=False,
            tool_names=["zsh"],
        )

    def test_install_expands_user_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A ~-relative --dotfiles path is expanded before dispatch."""
        monkeypatch.setattr(sys, "argv", ["openv", "install", "--dotfiles", "~/dots"])

        with patch("openv.cli._cmd_install") as cmd_install:
            main()

        passed_dotfiles = cmd_install.call_args.kwargs["dotfiles"]
        assert passed_dotfiles == Path("~/dots").expanduser()
        assert "~" not in str(passed_dotfiles)

    def test_install_force_flag_is_forwarded(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """The --force flag is forwarded to _cmd_install."""
        monkeypatch.setattr(
            sys,
            "argv",
            ["openv", "install", "--dotfiles", str(tmp_path), "--force"],
        )

        with patch("openv.cli._cmd_install") as cmd_install:
            main()

        assert cmd_install.call_args.kwargs["force"] is True
        assert cmd_install.call_args.kwargs["tool_names"] == []

    def test_install_default_dotfiles(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Omitting --dotfiles falls back to the expanded ~/.openv default."""
        monkeypatch.setattr(sys, "argv", ["openv", "install"])

        with patch("openv.cli._cmd_install") as cmd_install:
            main()

        assert cmd_install.call_args.kwargs["dotfiles"] == Path("~/.openv").expanduser()

    def test_generate_bootstrap_dispatch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dispatch generate-bootstrap with the provided dotfiles URL."""
        url = "https://example.com/dotfiles"
        monkeypatch.setattr(
            sys, "argv", ["openv", "generate-bootstrap", "--dotfiles", url]
        )

        with patch("openv.cli._cmd_generate_bootstrap") as cmd_generate:
            main()

        cmd_generate.assert_called_once_with(dotfiles_url=url)

    def test_generate_bootstrap_requires_dotfiles(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without --dotfiles, generate-bootstrap exits (it is required)."""
        monkeypatch.setattr(sys, "argv", ["openv", "generate-bootstrap"])

        with pytest.raises(SystemExit):
            main()
