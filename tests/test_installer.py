"""Tests for script execution in the installer module."""

from pathlib import Path
from unittest.mock import patch

from openv.installer import _parse_shebang, _run_script


class TestParseShebang:
    """Tests for _parse_shebang()."""

    def test_shebang_with_interpreter_only(self, tmp_path: Path) -> None:
        """A shebang with just the interpreter returns a single-element list."""
        script = tmp_path / "script.sh"
        script.write_text("#!/bin/sh\necho hello\n")
        assert _parse_shebang(script) == ["/bin/sh"]

    def test_shebang_with_env_and_interpreter(self, tmp_path: Path) -> None:
        """A #!/usr/bin/env <lang> shebang returns both env and interpreter."""
        script = tmp_path / "script.py"
        script.write_text("#!/usr/bin/env python3\nprint('hello')\n")
        assert _parse_shebang(script) == ["/usr/bin/env", "python3"]

    def test_shebang_with_arguments(self, tmp_path: Path) -> None:
        """A shebang with extra arguments includes those arguments in the list."""
        script = tmp_path / "script.py"
        script.write_text("#!/usr/bin/env python3 -u\nprint('hello')\n")
        assert _parse_shebang(script) == ["/usr/bin/env", "python3", "-u"]

    def test_awk_shebang_with_flag(self, tmp_path: Path) -> None:
        """A shebang like #!/usr/bin/awk -f includes the -f flag."""
        script = tmp_path / "script.awk"
        script.write_text("#!/usr/bin/awk -f\n{ print $0 }\n")
        assert _parse_shebang(script) == ["/usr/bin/awk", "-f"]

    def test_no_shebang_falls_back_to_sh(self, tmp_path: Path) -> None:
        """A script without a shebang line falls back to /bin/sh."""
        script = tmp_path / "script.sh"
        script.write_text("echo hello\n")
        assert _parse_shebang(script) == ["/bin/sh"]

    def test_empty_file_falls_back_to_sh(self, tmp_path: Path) -> None:
        """An empty script falls back to /bin/sh."""
        script = tmp_path / "script.sh"
        script.write_text("")
        assert _parse_shebang(script) == ["/bin/sh"]

    def test_comment_that_is_not_shebang_falls_back_to_sh(self, tmp_path: Path) -> None:
        """A file starting with # but not #! falls back to /bin/sh."""
        script = tmp_path / "script.sh"
        script.write_text("# This is just a comment\necho hello\n")
        assert _parse_shebang(script) == ["/bin/sh"]


class TestRunScript:
    """Tests for _run_script()."""

    def test_runs_with_shebang_interpreter(self, tmp_path: Path) -> None:
        """_run_script passes the correct interpreter and script path to subprocess."""
        script = tmp_path / "script.sh"
        script.write_text("#!/bin/sh\necho hello\n")

        with patch("openv.installer.subprocess.run") as mock_run:
            _run_script(script)
            mock_run.assert_called_once_with(["/bin/sh", str(script)], check=True)

    def test_runs_with_shebang_interpreter_and_args(self, tmp_path: Path) -> None:
        """_run_script includes shebang arguments before the script path."""
        script = tmp_path / "script.py"
        script.write_text("#!/usr/bin/env python3 -u\nprint('hello')\n")

        with patch("openv.installer.subprocess.run") as mock_run:
            _run_script(script)
            mock_run.assert_called_once_with(
                ["/usr/bin/env", "python3", "-u", str(script)], check=True
            )

    def test_runs_non_executable_script(self, tmp_path: Path) -> None:
        """_run_script can execute a script that is not marked executable."""
        script = tmp_path / "script.sh"
        script.write_text("#!/bin/sh\necho hello\n")
        # Explicitly remove execute bit
        script.chmod(0o644)

        with patch("openv.installer.subprocess.run") as mock_run:
            _run_script(script)
            mock_run.assert_called_once_with(["/bin/sh", str(script)], check=True)

    def test_falls_back_to_sh_without_shebang(self, tmp_path: Path) -> None:
        """_run_script uses /bin/sh when the script has no shebang."""
        script = tmp_path / "script.sh"
        script.write_text("echo hello\n")

        with patch("openv.installer.subprocess.run") as mock_run:
            _run_script(script)
            mock_run.assert_called_once_with(["/bin/sh", str(script)], check=True)
