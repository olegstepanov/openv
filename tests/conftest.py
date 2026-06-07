"""Shared pytest fixtures."""

from __future__ import annotations

import hashlib
import stat
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@pytest.fixture(scope="session")
def assessed_master(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[str], Path]:
    """Return a factory that yields pre-assessed executable stub files.

    On macOS the first execution of a freshly written executable triggers a
    Gatekeeper/``syspolicyd`` security assessment costing ~0.2s. The assessment is
    inode-keyed, so a symlink (or hardlink) to an already-assessed file inherits it
    for free. This factory writes each unique script body once, pays the assessment
    once per session, and returns the cached master path. Callers reference it from
    per-test directories via symlinks so the penalty is never paid per test.
    """
    master_dir = tmp_path_factory.mktemp("stub_masters")
    cache: dict[str, Path] = {}

    def make(content: str) -> Path:
        """Return a pre-assessed executable master for the given script body."""
        master = cache.get(content)
        if master is None:
            digest = hashlib.sha256(content.encode()).hexdigest()[:12]
            master = master_dir / digest
            master.write_text(content)
            master.chmod(master.stat().st_mode | stat.S_IXUSR)
            # Trigger the one-time macOS first-exec assessment here, not per test.
            subprocess.run(  # noqa: S603
                [str(master)],
                capture_output=True,
                env={"PATH": "/usr/bin:/bin", "STUB_LOG": "/dev/null"},
                check=False,
            )
            cache[content] = master
        return master

    return make
