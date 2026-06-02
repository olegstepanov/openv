"""Tests for the bootstrap script template."""

from __future__ import annotations

import importlib.resources
import stat
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


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


def _run_bootstrap(
    tmp_path: Path,
    *,
    user_id: int,
    include_sudo: bool = False,
    package_manager: str = "apt-get",
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Execute the template against package-manager and install command stubs."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "commands.log"

    _write_stub(bin_dir, "id", f'echo "{user_id}"\n')
    _write_stub(
        bin_dir, package_manager, f'echo "{package_manager} $*" >> "{log_path}"\n'
    )
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
