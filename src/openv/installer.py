from pathlib import Path
from typing import Iterable
import subprocess

from .discovery import ToolInfo
from .import packages
from .packages import PackageManager
from .stow import all_links_valid, stow


def _run_script(script: Path) -> None:
    """Execute a script using its declared shebang interpreter, or /bin/sh."""
    subprocess.run([str(script)], check=True)


def is_installed(
    tool: ToolInfo,
    pm: PackageManager,
    home: Path,
) -> bool:
    for package in tool.package_dependencies:
        if not packages.is_installed(pm, package):
            return False
        
    if not all_links_valid(tool, home):
        return False
    
    return True


def install_tool(
    tool: ToolInfo,
    pm: PackageManager,
    home: Path,
    force: bool = False,
) -> None:
    missing_packages = [
        package
        for package in tool.package_dependencies
        if not packages.is_installed(pm, package)
    ]
    
    """Run the four-step install sequence for a single tool."""
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
    tools: Iterable[ToolInfo],
    pm: PackageManager,
    home: Path,
    force: bool = False,
) -> None:
    """Install tools in topological order."""
    tool_map = {t.name: t for t in tools}
    for tool in tools:
        install_tool(tool, pm, home, force=force)
