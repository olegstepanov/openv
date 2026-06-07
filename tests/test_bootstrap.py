"""Tests for the bootstrap script template."""

from __future__ import annotations

import importlib.resources
import stat
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

from openv.cli import _cmd_generate_bootstrap

if TYPE_CHECKING:
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

    def test_root_install_does_not_require_sudo(self, tmp_path: Path) -> None:
        """Root environments install prerequisites without sudo."""
        result, log = _run_bootstrap(tmp_path, user_id=0)

        assert result.returncode == 0
        assert "apt-get update -y" in log
        assert "apt-get install -y git python3 python3-pip" in log

    def test_root_openwrt_install_does_not_require_sudo(self, tmp_path: Path) -> None:
        """Root OpenWRT environments install prerequisites without sudo."""
        result, log = _run_bootstrap(tmp_path, user_id=0, package_manager="opkg")

        assert result.returncode == 0
        assert "opkg update" in log
        assert "opkg install git python3 python3-pip" in log

    def test_homebrew_install_does_not_require_sudo(self, tmp_path: Path) -> None:
        """Homebrew environments install prerequisites without sudo."""
        result, log = _run_bootstrap(tmp_path, user_id=1000, package_manager="brew")

        assert result.returncode == 0
        assert "homebrew installer" not in log
        assert "brew install git python3" in log

    def test_macos_without_package_manager_installs_homebrew(
        self, tmp_path: Path
    ) -> None:
        """Darwin environments without brew install Homebrew before prerequisites."""
        result, log = _run_bootstrap(
            tmp_path,
            user_id=1000,
            package_manager=None,
            uname_system="Darwin",
            include_homebrew_installer=True,
        )

        assert result.returncode == 0
        assert "homebrew installer" in log
        assert log.index("homebrew installer") < log.index("brew install git python3")

    def test_non_root_install_uses_sudo_when_available(self, tmp_path: Path) -> None:
        """Non-root environments delegate privileged commands to sudo."""
        result, log = _run_bootstrap(tmp_path, user_id=1000, include_sudo=True)

        assert result.returncode == 0
        assert "sudo apt-get update -y" in log
        assert "sudo apt-get install -y git python3 python3-pip" in log

    def test_non_root_install_fails_clearly_without_sudo(self, tmp_path: Path) -> None:
        """Non-root environments without sudo report how to proceed."""
        result, log = _run_bootstrap(tmp_path, user_id=1000)

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
        self, tmp_path: Path
    ) -> None:
        """Absent package managers fail with the error directed to stderr."""
        result, _ = _run_bootstrap(tmp_path, user_id=1000, package_manager=None)

        assert result.returncode != 0
        assert (
            "ERROR: No supported package manager found (brew, apt-get, opkg)."
        ) in result.stderr

    def test_existing_openv_directory_reports_error_on_stderr(
        self, tmp_path: Path
    ) -> None:
        """An existing $HOME/.openv fails with the error directed to stderr."""
        home_dir = tmp_path / "home"
        (home_dir / ".openv").mkdir(parents=True)

        result, _ = _run_bootstrap(tmp_path, user_id=0)

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


def _run_bootstrap(
    tmp_path: Path,
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

    _write_stub(bin_dir, "id", f'echo "{user_id}"\n')
    if uname_system is not None:
        _write_stub(bin_dir, "uname", f'echo "{uname_system}"\n')
    if package_manager is not None:
        _write_stub(
            bin_dir, package_manager, f'echo "{package_manager} $*" >> "{log_path}"\n'
        )
    if include_homebrew_installer:
        _write_homebrew_installer_stub(bin_dir, log_path)
    _write_stub(bin_dir, "git", f'echo "git $*" >> "{log_path}"\n')
    _write_stub(bin_dir, "pip3", f'echo "pip3 $*" >> "{log_path}"\n')
    _write_stub(bin_dir, "openv", f'echo "openv $*" >> "{log_path}"\n')
    if include_sudo:
        _write_stub(
            bin_dir,
            "sudo",
            f'echo "sudo $*" >> "{log_path}"\nexec "$@"\n',
        )

    template_ref = importlib.resources.files("openv").joinpath("bootstrap.sh.template")
    with importlib.resources.as_file(template_ref) as path:
        result = subprocess.run(  # noqa: S603
            ["/bin/sh", str(path)],
            check=False,
            capture_output=True,
            env={"HOME": str(tmp_path / "home"), "PATH": str(bin_dir)},
            text=True,
        )

    log = log_path.read_text() if log_path.exists() else ""
    return result, log


def _write_stub(bin_dir: Path, name: str, body: str) -> None:
    """Create an executable shell command stub."""
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{body}")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_homebrew_installer_stub(bin_dir: Path, log_path: Path) -> None:
    """Create a curl stub that emits a fake Homebrew installer."""
    brew_path = bin_dir / "brew"
    installer = f"""#!/bin/sh
echo "homebrew installer" >> "{log_path}"
printf '%s\\n' '#!/bin/sh' 'echo "brew $*" >> "{log_path}"' > "{brew_path}"
/bin/chmod +x "{brew_path}"
"""
    escaped_installer = installer.replace("'", "'\"'\"'")
    _write_stub(bin_dir, "curl", f"printf '%s' '{escaped_installer}'\n")
