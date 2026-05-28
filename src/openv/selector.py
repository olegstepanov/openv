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
    config_count = len(tool.config_files)
    if config_count == 0:
        return "no configs"
    return "partial"


def _is_partial(tool: ToolInfo, home: Path) -> bool:
    if not tool.config_files:
        return False
    valid = all_links_valid(tool, home)
    return not valid


def select_tools(
    tools: Iterable[ToolInfo], pm: PackageManager, home: Path
) -> list[str]:
    """Show an interactive checkbox selector; return selected tool names."""
    choices = []
    for tool in tools:
        status = _tool_status(tool, home)
        label = f"{tool.name}  [{status}]"
        is_installed = installer.is_installed(tool, pm, home)
        choice = questionary.Choice(
            title=label,
            value=tool.name,
            checked=is_installed,
            disabled="Installed" if is_installed else None,
        )
        choices.append(choice)

    selected = questionary.checkbox(
        "Select tools to install:",
        choices=choices,
    ).ask()

    if selected is None:
        return []
    return selected
