#!/usr/bin/env python3
"""Check that functions with significant bodies have docstrings."""

import argparse
import ast
import sys
from pathlib import Path


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if the function's first statement is a docstring."""
    if not node.body:
        return False
    first = node.body[0]
    return (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    )


def _count_meaningful_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
) -> int:
    """Count non-blank, non-comment body lines, excluding the docstring.

    The function header line is not counted.
    """
    body = node.body
    if not body:
        return 0
    first_body_index = 1 if _has_docstring(node) else 0
    if first_body_index >= len(body):
        return 0
    first_line = body[first_body_index].lineno
    last_line = node.end_lineno
    count = 0
    for line_num in range(first_line, last_line + 1):
        line = source_lines[line_num - 1].strip()
        if line and not line.startswith("#"):
            count += 1
    return count


def check_file(path: Path, threshold: int) -> list[str]:
    """Return violation messages for undocumented functions in path.

    A function is flagged when it has no docstring and its body contains
    more than threshold meaningful lines.
    """
    source = path.read_text()
    source_lines = source.splitlines()
    tree = ast.parse(source, filename=str(path))
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _has_docstring(node):
            continue
        meaningful = _count_meaningful_lines(node, source_lines)
        if meaningful > threshold:
            violations.append(
                f"{path}:{node.lineno}: '{node.name}' has {meaningful}"
                f" meaningful lines but no docstring"
            )
    return violations


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check docstrings on significant functions"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=5,
        help="Minimum meaningful body lines that require a docstring (default: 5)",
    )
    parser.add_argument("files", nargs="*", default=["src/", "dev/"])
    args = parser.parse_args()

    all_files: list[Path] = []
    for arg in args.files:
        p = Path(arg)
        if p.is_dir():
            all_files.extend(sorted(p.rglob("*.py")))
        elif p.suffix == ".py":
            all_files.append(p)

    all_violations: list[str] = []
    for file in all_files:
        all_violations.extend(check_file(file, args.threshold))

    for violation in all_violations:
        print(violation)

    sys.exit(1 if all_violations else 0)
