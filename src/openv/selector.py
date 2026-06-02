"""Interactive tool selector using questionary checkboxes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import questionary

from . import installer, packages
from .packages import detect_package_manager
from .stow import all_links_valid

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from .discovery import ToolInfo


def _tool_status(
    tool: ToolInfo, is_installed: bool, is_partially_installed: bool = False
) -> str:
    """Return the short status label shown next to the tool name in the selector."""
    if is_installed:
        return "installed"
    if installer.is_scripts_only(tool):
        return "scripts only"
    if not tool.config_files:
        return "no configs"
    if is_partially_installed:
        return "partial"
    return "not installed"


def _is_partially_installed(
    tool: ToolInfo, pm: packages.PackageManager, home: Path
) -> bool:
    """Return True if packages are present but config symlinks are incomplete."""
    return (
        bool(tool.config_files)
        and all(
            packages.is_installed(pm, package) for package in tool.package_dependencies
        )
        and not all_links_valid(tool, home)
    )


def select_tools(tools: Iterable[ToolInfo], home: Path) -> list[str]:
    """Show an interactive checkbox selector; return selected tool names."""
    pm = detect_package_manager()
    choices: list[questionary.Choice] = []
    for tool in tools:
        tool_is_installed = installer.is_installed(tool, pm, home)
        tool_is_partial = not tool_is_installed and _is_partially_installed(
            tool, pm, home
        )
        status = _tool_status(tool, tool_is_installed, tool_is_partial)
        label = f"{tool.name}  [{status}]"
        choice = questionary.Choice(
            title=label,
            value=tool.name,
            checked=tool_is_installed or tool_is_partial,
        )
        choices.append(choice)

    selected: list[str] | None = questionary.checkbox(  # pyright: ignore[reportAny]
        "Select tools to install:",
        choices=choices,
    ).ask()

    if selected is None:
        return []
    return selected
