"""Shebang-based package dependency inference for tool scripts."""

from __future__ import annotations

from pathlib import Path

# Interpreter name -> package name mapping
_INTERPRETER_PACKAGES: dict[str, str] = {
    "bash": "bash",
}


def _parse_shebang(script: Path) -> str | None:
    try:
        with script.open("r", encoding="utf-8", errors="replace") as f:
            first_line = f.readline().rstrip("\n")
    except OSError:
        return None

    if not first_line.startswith("#!"):
        return None

    parts = first_line[2:].strip().split()
    if not parts:
        return None

    executable = parts[0]
    if executable.endswith("/env") and len(parts) >= 2:
        return parts[1]
    else:
        return Path(executable).name


def get_script_dependencies(script: Path) -> list[str]:
    """Return the package name inferred from a script's shebang, or None."""
    interpreter = _parse_shebang(script)
    if interpreter is None:
        return []
    interpreter_package = _INTERPRETER_PACKAGES.get(interpreter)
    if interpreter_package is None:
        return []
    else:
        return [interpreter_package]
