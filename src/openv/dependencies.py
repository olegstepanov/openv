"""Shebang-based package dependency inference for tool scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

# Interpreter name -> package name mapping
_INTERPRETER_PACKAGES: dict[str, str] = {
    "bash": "bash",
}


class _HasToolDependencyFields(Protocol):
    """Structural protocol for the fields needed to build a dependency graph."""

    name: str
    package_dependencies: list[str]


def _parse_shebang(script: Path) -> str | None:
    """Return the interpreter name from a shebang line, or None."""
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


def build_tool_dependency_graph(
    tools: list[_HasToolDependencyFields],
) -> dict[str, set[str]]:
    """Return a tool-name → set-of-tool-names dependency graph.

    A tool-to-tool edge exists when a package dependency of one tool matches
    the name of another tool in the list. Self-loops (a tool's own-name package
    dependency) are excluded because they would create trivial cycles. Pure
    package dependencies with no matching tool directory produce no graph edge.
    """
    tool_names = {tool.name for tool in tools}
    tool_dependency_graph: dict[str, set[str]] = {}
    for tool in tools:
        tool_dependencies = {
            package_dependency
            for package_dependency in tool.package_dependencies
            if package_dependency in tool_names and package_dependency != tool.name
        }
        tool_dependency_graph[tool.name] = tool_dependencies
    return tool_dependency_graph
