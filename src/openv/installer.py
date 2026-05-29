"""Tool installation orchestration: runs the four-step install sequence per tool."""

import subprocess
from collections.abc import Iterable
from pathlib import Path

from . import packages
from .discovery import ToolInfo
from .packages import PackageManager
from .stow import all_links_valid, stow


def _parse_shebang(script: Path) -> list[str]:
    """Return the interpreter and arguments from the script's shebang line.

    Reads the first line of the script and, if it starts with ``#!``, splits
    the remainder on whitespace to produce a list of ``[interpreter, *args]``.
    Returns ``["/bin/sh"]`` when no shebang line is present.
    """
    first_line = (
        script.read_text(encoding="utf-8").splitlines()[0]
        if script.stat().st_size > 0
        else ""
    )
    if first_line.startswith("#!"):
        parts = first_line[2:].split()
        if parts:
            return parts
    return ["/bin/sh"]


def _run_script(script: Path) -> None:
    """Execute a script using its declared shebang interpreter, or /bin/sh.

    Parses the shebang line to determine the interpreter and any arguments,
    then invokes ``subprocess.run([interpreter, *shebang_args, script])``.
    This means the script does not need to be marked executable.
    """
    interpreter_and_args = _parse_shebang(script)
    subprocess.run([*interpreter_and_args, str(script)], check=True)  # noqa: S603


def is_installed(
    tool: ToolInfo,
    pm: PackageManager,
    home: Path,
) -> bool:
    """Return True if all packages are installed and all config symlinks are valid."""
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
    for tool in tools:
        install_tool(tool, pm, home, force=force)
