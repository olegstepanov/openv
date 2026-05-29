"""Interactive tool selector using questionary checkboxes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import questionary

from . import installer
from .stow import all_links_valid

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from .discovery import ToolInfo
    from .packages import PackageManager


def _tool_status(tool: ToolInfo, home: Path) -> str:
    if all_links_valid(tool, home):
        return "installed"
    if not tool.config_files:
        return "no configs"
    return "partial"


def select_tools(
    tools: Iterable[ToolInfo], pm: PackageManager, home: Path
) -> list[str]:
    """Show an interactive checkbox selector; return selected tool names."""
    choices: list[questionary.Choice] = []
    for tool in tools:
        status = _tool_status(tool, home)
        label = f"{tool.name}  [{status}]"
        tool_is_installed = installer.is_installed(tool, pm, home)
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
