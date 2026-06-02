"""CLI entry point for openv."""

import argparse
import importlib.metadata
import importlib.resources
import sys
from pathlib import Path

from openv.discovery import discover
from openv.installer import install_tools
from openv.packages import detect
from openv.selector import select_tools


class _Args(argparse.Namespace):
    command: str = ""
    dotfiles: str = ""
    force: bool = False
    tools: list[str] = []  # noqa: RUF012


def _cmd_install(dotfiles: Path, force: bool, tool_names: list[str]) -> None:
    """Discover, select, and install tools from a dotfiles repository."""
    home = Path.home()
    pm = detect()

    tools = discover(dotfiles)
    if not tools:
        print("No tools found in", dotfiles)
        return

    if tool_names:
        unknown = [name for name in tool_names if name not in tools]
        if unknown:
            unknown_list = ", ".join(unknown)
            print(
                f"Unknown tool(s): {unknown_list}",
                file=sys.stderr,
            )
            sys.exit(2)
        selected_names = tool_names
    else:
        selected_names = select_tools(tools.values(), pm, home)
        if not selected_names:
            print("No tools selected.")
            return

    selected_tools = [tools[name] for name in selected_names]
    install_tools(selected_tools, tools, pm, home, force=force)


def _cmd_generate_bootstrap(dotfiles_url: str) -> None:
    """Render the bootstrap script template and write it to stdout."""
    template = (
        importlib.resources.files("openv").joinpath("bootstrap.sh.template").read_text()
    )
    version = importlib.metadata.version("openv")
    output = template.replace("{{OPENV_VERSION}}", version)
    output = output.replace("{{DOTFILES_URL}}", dotfiles_url)
    sys.stdout.write(output)


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        prog="openv",
        description="Bootstrap your UNIX environment from a dotfiles repository",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    install_p = sub.add_parser(
        "install", help="Install tools from a dotfiles repository"
    )
    install_p.add_argument(
        "--dotfiles",
        default="~/.openv",
        help="Path to dotfiles repository root (default: ~/.openv)",
    )
    install_p.add_argument(
        "--force", action="store_true", help="Re-link configs and re-run scripts"
    )
    install_p.add_argument(
        "tools", nargs="*", help="Tools to install (skips interactive selector)"
    )

    gen_p = sub.add_parser("generate-bootstrap", help="Generate bootstrap script")
    gen_p.add_argument(
        "--dotfiles", required=True, help="URL of the dotfiles repository"
    )

    args = parser.parse_args(namespace=_Args())

    if args.command == "install":
        _cmd_install(
            dotfiles=Path(args.dotfiles).expanduser(),
            force=args.force,
            tool_names=args.tools,
        )
    elif args.command == "generate-bootstrap":
        _cmd_generate_bootstrap(dotfiles_url=args.dotfiles)
