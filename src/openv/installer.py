"""Tool installation orchestration: runs the four-step install sequence per tool."""

import graphlib
import os
import subprocess
from pathlib import Path
from typing import cast

from . import packages
from .dependencies import build_tool_dependency_graph
from .discovery import ToolInfo
from .packages import PackageManager
from .stow import all_links_valid, stow


def _run_script(script: Path) -> None:
    """Execute a script via OS execution; raises PermissionError if not executable."""
    if not os.access(script, os.X_OK):
        raise PermissionError(f"Script is not executable: {script}")
    subprocess.run([str(script)], check=True)  # noqa: S603


def is_scripts_only(tool: ToolInfo) -> bool:
    """Return True if the tool has scripts but no symlinks to verify completion.

    A tool with install.sh/post-install.sh but no config files leaves no
    persistent trace of whether its scripts ran. Such tools cannot be treated as
    idempotently complete; they must be re-run whenever selected.
    """
    has_scripts = (
        tool.install_script is not None or tool.post_install_script is not None
    )
    return has_scripts and not tool.config_files


def is_installed(
    tool: ToolInfo,
    pm: PackageManager,
    home: Path,
) -> bool:
    """Return True if all packages are installed and all config symlinks are valid."""
    if is_scripts_only(tool):
        return False
    all_packages_installed = all(
        packages.is_installed(pm, p) for p in tool.package_dependencies
    )
    return all_packages_installed and all_links_valid(tool, home)


def install_tool(
    tool: ToolInfo,
    pm: PackageManager,
    home: Path,
    force: bool = False,
) -> None:
    """Run the four-step install sequence for a single tool."""
    missing_packages = [
        package
        for package in tool.package_dependencies
        if not packages.is_installed(pm, package)
    ]
    if not is_scripts_only(tool):
        if not force and not missing_packages and all_links_valid(tool, home):
            return

    # Step 1: install package dependencies
    for missing_package in missing_packages:
        packages.install_package(pm, missing_package)

    # Step 2: run install.sh
    install_script = tool.install_script
    if install_script:
        _run_script(install_script)

    # Step 3: link configs
    stow(tool, home, force=force)

    # Step 4: run post-install.sh
    post_install_script = tool.post_install_script
    if post_install_script:
        _run_script(post_install_script)


def install_tools(
    selected_tools: list[ToolInfo],
    all_tools: dict[str, ToolInfo],
    pm: PackageManager,
    home: Path,
    force: bool = False,
) -> None:
    """Install tools in topological order, including transitive dependencies.

    Expands the selected tool list to include any transitive tool dependencies
    not explicitly selected by the user, then installs all required tools in
    dependency order.

    Args:
        selected_tools: Tools explicitly chosen by the user.
        all_tools: All tools discovered in the dotfiles repository, keyed by name.
        pm: The package manager to use for installing packages.
        home: The user's home directory for symlinking configs.
        force: If True, re-link configs and re-run scripts even if already done.

    Raises:
        ValueError: If a circular dependency is detected among the tools.
    """
    # Expand selected tools to include transitive tool dependencies
    tools_to_install: dict[str, ToolInfo] = {}
    pending = list(selected_tools)
    while pending:
        tool = pending.pop()
        if tool.name in tools_to_install:
            continue
        tools_to_install[tool.name] = tool
        for package_dependency in tool.package_dependencies:
            if (
                package_dependency in all_tools
                and package_dependency not in tools_to_install
            ):
                pending.append(all_tools[package_dependency])

    # Build tool dependency graph and sort in topological order
    tool_dependency_graph = build_tool_dependency_graph(list(tools_to_install.values()))
    sorter = graphlib.TopologicalSorter(tool_dependency_graph)
    try:
        ordered_tool_names = list(sorter.static_order())
    except graphlib.CycleError as cycle_error:
        cycle_nodes = cast("list[str]", cycle_error.args[1])
        cycle_description = " -> ".join(cycle_nodes)
        raise ValueError(
            f"Circular tool dependency detected: {cycle_description}"
        ) from cycle_error

    for tool_name in ordered_tool_names:
        tool = tools_to_install[tool_name]
        install_tool(tool, pm, home, force=force)
