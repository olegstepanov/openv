import argparse
import importlib.metadata
import importlib.resources
import sys
from pathlib import Path
from openv.discovery import discover
from openv.installer import install_tools
from openv.packages import detect
from openv.selector import select_tools


def _cmd_install(args: argparse.Namespace) -> None:
    dotfiles = Path(args.dotfiles).expanduser()
    home = Path.home()
    force = args.force
    pm = detect()

    tools = discover(dotfiles)
    if not tools:
        print("No tools found in", dotfiles)
        return

    if args.tools:
        selected_names = list(args.tools)
    else:
        selected_names = select_tools(tools.values(), pm, home)
        if not selected_names:
            print("No tools selected.")
            return

    selected_tools = [tools[name] for name in selected_names]
    install_tools(selected_tools, pm, home, force=force)


def _cmd_generate_bootstrap(args: argparse.Namespace) -> None:
    template = importlib.resources.files("openv").joinpath("bootstrap.sh.template").read_text()
    version = importlib.metadata.version("openv")
    output = template.replace("{{OPENV_VERSION}}", version)
    output = output.replace("{{DOTFILES_URL}}", args.dotfiles)
    sys.stdout.write(output)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="openv",
        description="Bootstrap your UNIX environment from a dotfiles repository",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    install_p = sub.add_parser("install", help="Install tools from a dotfiles repository")
    install_p.add_argument(
        "--dotfiles",
        default="~/.openv",
        help="Path to dotfiles repository root (default: ~/.openv)",
    )
    install_p.add_argument("--force", action="store_true", help="Re-link configs and re-run scripts")
    install_p.add_argument("tools", nargs="*", help="Tools to install (skips interactive selector)")

    gen_p = sub.add_parser("generate-bootstrap", help="Generate bootstrap script")
    gen_p.add_argument("--dotfiles", required=True, help="URL of the dotfiles repository")

    args = parser.parse_args()

    if args.command == "install":
        _cmd_install(args)
    elif args.command == "generate-bootstrap":
        _cmd_generate_bootstrap(args)
