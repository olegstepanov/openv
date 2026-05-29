"""Tool discovery: enumerate tools from a dotfiles repository root."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import dependencies

if TYPE_CHECKING:
    from pathlib import Path

_SCRIPT_NAMES = {"install.sh", "post-install.sh"}


@dataclass
class ToolInfo:
    """Metadata about a single tool in the dotfiles repository."""

    name: str
    directory: Path
    package_dependencies: list[str] = field(default_factory=list)
    install_script: Path | None = None
    post_install_script: Path | None = None
    config_files: list[Path] = field(default_factory=list)


def discover(dotfiles_root: Path) -> dict[str, ToolInfo]:
    """Return all tools found at the dotfiles root, keyed by name."""
    tools: dict[str, ToolInfo] = {}
    for entry in dotfiles_root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        tool = _create_tool_from_directory(entry)
        if tool.name in tools:
            raise ValueError(f"Duplicate tool name: {tool.name!r}")
        tools[tool.name] = tool
    return tools


def _create_tool_from_directory(directory: Path) -> ToolInfo:
    """Build a ToolInfo by inspecting a tool directory."""

    def check_script(file_name: str) -> Path | None:
        """Return path to file_name if it exists as a regular file, else None."""
        path = directory / file_name
        if not path.exists():
            return None
        if not path.is_file():
            raise ValueError(f"Script {path} must either be a file or be absent.")
        return path

    install_script = check_script("install.sh")
    post_install_script = check_script("post-install.sh")
    config_files = [
        entry
        for entry in directory.iterdir()
        if entry.is_file() and entry.name not in _SCRIPT_NAMES
    ]

    # Implicit dependency on package with the same name
    package_dependencies = {directory.name}
    package_dependencies.update(
        dependency
        for script in [install_script, post_install_script]
        if script is not None
        for dependency in dependencies.get_script_dependencies(script)
    )
    return ToolInfo(
        name=directory.name,
        directory=directory,
        package_dependencies=list(package_dependencies),
        install_script=install_script,
        post_install_script=post_install_script,
        config_files=config_files,
    )
