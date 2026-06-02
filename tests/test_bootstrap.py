"""Tests for the bootstrap script template."""

from __future__ import annotations

import importlib.resources
import subprocess


class TestBootstrapTemplate:
    """Tests for bootstrap.sh.template."""

    def test_template_passes_sh_syntax_check(self) -> None:
        """bootstrap.sh.template contains valid POSIX sh syntax."""
        template_ref = importlib.resources.files("openv").joinpath(
            "bootstrap.sh.template"
        )
        with importlib.resources.as_file(template_ref) as path:
            subprocess.run(["sh", "-n", str(path)], check=True)  # noqa: S603, S607
