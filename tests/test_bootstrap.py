"""Tests for the bootstrap script template."""

from __future__ import annotations

import importlib.resources
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

from openv.cli import _cmd_generate_bootstrap

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest


class TestBootstrapTemplate:
    """Tests for bootstrap.sh.template."""

    def test_template_passes_sh_syntax_check(self) -> None:
        """bootstrap.sh.template contains valid POSIX sh syntax."""
        template_ref = importlib.resources.files("openv").joinpath(
            "bootstrap.sh.template"
        )
        with importlib.resources.as_file(template_ref) as path:
            subprocess.run(["sh", "-n", str(path)], check=True)  # noqa: S603, S607

    def test_root_install_does_not_require_sudo(
        self, tmp_path: Path, script_factory: Callable[[str], Path]
    ) -> None:
        """Root environments install prerequisites without sudo."""
        result, log = _run_bootstrap(tmp_path, script_factory, user_id=0)

        assert result.returncode == 0
        assert "apt-get update -y" in log
        assert "apt-get install -y git python3 python3-pip" in log

    def test_root_openwrt_install_does_not_require_sudo(
        self, tmp_path: Path, script_factory: Callable[[str], Path]
    ) -> None:
        """Root OpenWRT environments install prerequisites without sudo."""
        result, log = _run_bootstrap(
            tmp_path, script_factory, user_id=0, package_manager="opkg"
        )

        assert result.returncode == 0
        assert "opkg update" in log
        assert "opkg install git python3 python3-pip" in log

    def test_homebrew_install_does_not_require_sudo(
        self, tmp_path: Path, script_factory: Callable[[str], Path]
    ) -> None:
        """Homebrew environments install prerequisites without sudo."""
        result, log = _run_bootstrap(
            tmp_path, script_factory, user_id=1000, package_manager="brew"
        )

        assert result.returncode == 0
        assert "homebrew installer" not in log
        assert "brew install git python3" in log

    def test_macos_without_package_manager_installs_homebrew(
        self, tmp_path: Path, script_factory: Callable[[str], Path]
    ) -> None:
        """Darwin environments without brew install Homebrew before prerequisites."""
        result, log = _run_bootstrap(
            tmp_path,
            script_factory,
            user_id=1000,
            package_manager=None,
            uname_system="Darwin",
            include_homebrew_installer=True,
        )

        assert result.returncode == 0
        assert "homebrew installer" in log
        assert log.index("homebrew installer") < log.index("brew install git python3")

    def test_non_root_install_uses_sudo_when_available(
        self, tmp_path: Path, script_factory: Callable[[str], Path]
    ) -> None:
        """Non-root environments delegate privileged commands to sudo."""
        result, log = _run_bootstrap(
            tmp_path, script_factory, user_id=1000, include_sudo=True
        )

        assert result.returncode == 0
        assert "sudo apt-get update -y" in log
        assert "sudo apt-get install -y git python3 python3-pip" in log

    def test_non_root_install_fails_clearly_without_sudo(
        self, tmp_path: Path, script_factory: Callable[[str], Path]
    ) -> None:
        """Non-root environments without sudo report how to proceed."""
        result, log = _run_bootstrap(tmp_path, script_factory, user_id=1000)

        assert result.returncode == 1
        assert log == ""
        assert (
            "ERROR: Root privileges are required to install prerequisites. "
            "Run as root or install sudo."
        ) in result.stderr

    def test_generated_dotfiles_url_is_shell_quoted(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The generated assignment treats shell syntax in the URL as data."""
        marker = tmp_path / "command-substitution-ran"
        dotfiles_url = f"https://example.invalid/it's/$(touch {marker})"

        _cmd_generate_bootstrap(dotfiles_url)

        output = capsys.readouterr().out
        assignment = next(
            line for line in output.splitlines() if line.startswith("DOTFILES_URL=")
        )
        result = subprocess.run(  # noqa: S603
            ["sh", "-c", f"{assignment}\nprintf '%s' \"$DOTFILES_URL\""],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout == dotfiles_url
        assert not marker.exists()

    def test_generated_output_substitutes_openv_version(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The installed openv version replaces the template placeholder."""
        with patch("openv.cli.importlib.metadata.version", return_value="1.2.3"):
            _cmd_generate_bootstrap("https://example.invalid/dotfiles.git")

        output = capsys.readouterr().out
        assert 'OPENV_VERSION="1.2.3"' in output
        assert "{{OPENV_VERSION}}" not in output

    def test_missing_package_manager_reports_error_on_stderr(
        self, tmp_path: Path, script_factory: Callable[[str], Path]
    ) -> None:
        """Absent package managers fail with the error directed to stderr."""
        result, _ = _run_bootstrap(
            tmp_path, script_factory, user_id=1000, package_manager=None
        )

        assert result.returncode != 0
        assert (
            "ERROR: No supported package manager found (brew, apt-get, opkg)."
        ) in result.stderr

    def test_existing_openv_directory_reports_error_on_stderr(
        self, tmp_path: Path, script_factory: Callable[[str], Path]
    ) -> None:
        """An existing $HOME/.openv fails with the error directed to stderr."""
        home_dir = tmp_path / "home"
        (home_dir / ".openv").mkdir(parents=True)

        result, _ = _run_bootstrap(tmp_path, script_factory, user_id=0)

        assert result.returncode != 0
        assert (
            f"ERROR: {home_dir}/.openv already exists. "
            "Remove it before running bootstrap."
        ) in result.stderr

    def test_installs_openv_before_cloning_dotfiles(self) -> None:
        """Bootstrap installs pinned openv before cloning the dotfiles repository."""
        template = (
            importlib.resources.files("openv")
            .joinpath("bootstrap.sh.template")
            .read_text()
        )

        assert template.index('pip3 install "openv==$OPENV_VERSION"') < template.index(
            'git clone "$DOTFILES_URL" "$HOME/.openv"'
        )


# Stub command bodies, kept identical across tests so each is assessed once per
# session (see the ``assessed_master`` fixture in conftest.py). Per-test data is
# passed through the STUB_* environment variables rather than baked into the body.
# The generic logger derives the invoked command name from ``$0`` via POSIX
# parameter expansion (``${0##*/}``), so a single master can stand in for git,
# pip3, the package managers, etc. without needing basename on the restricted PATH.
_LOGGER_STUB = '#!/bin/sh\necho "${0##*/} $*" >> "$STUB_LOG"\n'
_ID_STUB = '#!/bin/sh\necho "${STUB_UID:-0}"\n'
_UNAME_STUB = '#!/bin/sh\necho "${STUB_UNAME:-Linux}"\n'
_SUDO_STUB = '#!/bin/sh\necho "sudo $*" >> "$STUB_LOG"\nexec "$@"\n'
# curl emits a Homebrew installer that logs and creates ``brew`` as a symlink to a
# pre-assessed master (rather than write+chmod, which would re-incur the macOS
# first-exec penalty). It uses absolute /bin/ln since only the stub bin dir is on
# PATH, and relies on the STUB_* variables inherited by the installer's shell.
_CURL_STUB = (
    "#!/bin/sh\n"
    "printf '%s\\n' "
    '\'echo "homebrew installer" >> "$STUB_LOG"\' '
    '\'/bin/ln -s "$STUB_BREW_MASTER" "$STUB_BIN/brew"\'\n'
)


def _run_bootstrap(
    tmp_path: Path,
    assessed_master: Callable[[str], Path],
    *,
    user_id: int,
    include_sudo: bool = False,
    package_manager: str | None = "apt-get",
    uname_system: str | None = None,
    include_homebrew_installer: bool = False,
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Execute the template against package-manager and install command stubs."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "commands.log"

    logger = assessed_master(_LOGGER_STUB)
    (bin_dir / "id").symlink_to(assessed_master(_ID_STUB))
    (bin_dir / "git").symlink_to(logger)
    (bin_dir / "pip3").symlink_to(logger)
    (bin_dir / "openv").symlink_to(logger)
    if uname_system is not None:
        (bin_dir / "uname").symlink_to(assessed_master(_UNAME_STUB))
    if package_manager is not None:
        (bin_dir / package_manager).symlink_to(logger)
    if include_sudo:
        (bin_dir / "sudo").symlink_to(assessed_master(_SUDO_STUB))

    env = {
        "HOME": str(tmp_path / "home"),
        "PATH": str(bin_dir),
        "STUB_LOG": str(log_path),
        "STUB_UID": str(user_id),
    }
    if uname_system is not None:
        env["STUB_UNAME"] = uname_system
    if include_homebrew_installer:
        (bin_dir / "curl").symlink_to(assessed_master(_CURL_STUB))
        env["STUB_BIN"] = str(bin_dir)
        env["STUB_BREW_MASTER"] = str(logger)

    template_ref = importlib.resources.files("openv").joinpath("bootstrap.sh.template")
    with importlib.resources.as_file(template_ref) as path:
        result = subprocess.run(  # noqa: S603
            ["/bin/sh", str(path)],
            check=False,
            capture_output=True,
            env=env,
            text=True,
        )

    log = log_path.read_text() if log_path.exists() else ""
    return result, log
