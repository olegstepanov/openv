"""Interactive tool selector using questionary checkboxes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import questionary

from . import installer
from .packages import detect_package_manager

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from .discovery import ToolInfo


def _tool_status(tool: ToolInfo, is_installed: bool) -> str:
    """Return the short status label shown next to the tool name in the selector."""
    if is_installed:
        return "installed"
    if installer.is_scripts_only(tool):
        return "scripts only"
    if not tool.config_files:
        return "no configs"
    return "partial"


def select_tools(tools: Iterable[ToolInfo], home: Path) -> list[str]:
    """Show an interactive checkbox selector; return selected tool names."""
    pm = detect_package_manager()
    choices: list[questionary.Choice] = []
    for tool in tools:
        tool_is_installed = installer.is_installed(tool, pm, home)
        status = _tool_status(tool, tool_is_installed)
        label = f"{tool.name}  [{status}]"
        choice = questionary.Choice(
            title=label,
            value=tool.name,
            checked=tool_is_installed,
            disabled="Installed" if tool_is_installed else None,
        )
        choices.append(choice)

    selected: list[str] | None = questionary.checkbox(  # pyright: ignore[reportAny]
        "Select tools to install:",
        choices=choices,
    ).ask()

    if selected is None:
        return []
    return selected
