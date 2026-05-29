#!/usr/bin/env python3
"""Run all linters for the openv project."""

import argparse
import subprocess
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all linters")
    parser.add_argument("files", nargs="*", default=["src/", "dev/"])
    parser.add_argument("--fix", action="store_true", help="Apply safe auto-fixes")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Apply unsafe fixes (implies --fix)",
    )
    args = parser.parse_args()
    fix = args.fix or args.force

    ruff_format_cmd = ["ruff", "format"] + ([] if fix else ["--check"]) + args.files
    ruff_check_cmd = (
        ["ruff", "check"]
        + (["--fix"] if fix else [])
        + (["--unsafe-fixes"] if args.force else [])
        + args.files
    )
    commands = [
        ruff_format_cmd,
        ruff_check_cmd,
        ["basedpyright"],
        ["pydoclint", *args.files],
        [sys.executable, "dev/check_docstrings.py", "--threshold", "5", *args.files],
    ]

    for command in commands:
        result = subprocess.run(command)
        if result.returncode != 0:
            sys.exit(result.returncode)
