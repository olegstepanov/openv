"""Tests for script execution in the installer."""

import subprocess
from pathlib import Path

import pytest

from openv.installer import _run_script


class TestRunScript:
    """Tests for _run_script()."""

    def test_executable_script_runs_successfully(self, tmp_path: Path) -> None:
        """An executable script is invoked via OS execution without error."""
        script = tmp_path / "install.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o755)
        _run_script(script)

    def test_non_executable_script_raises_permission_error(self, tmp_path: Path) -> None:
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
