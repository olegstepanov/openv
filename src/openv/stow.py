from pathlib import Path

from openv.discovery import ToolInfo


def expected_links(tool: ToolInfo, home: Path) -> list[tuple[Path, Path]]:
    """Return list of (link_path, target_path) for a tool's config files."""
    links: list[tuple[Path, Path]] = []
    for config_file in tool.config_files:
        rel = config_file.relative_to(tool.directory)
        link_path = home / rel
        links.append((link_path, config_file))
    return links


def all_links_valid(tool: ToolInfo, home: Path) -> bool:
    """Return True if every expected symlink exists and points to the correct target."""
    for link_path, target in expected_links(tool, home):
        if not link_path.is_symlink():
            return False
        if link_path.resolve() != target.resolve():
            return False
    return True


def stow(tool: ToolInfo, home: Path, force: bool = False) -> None:
    """Create symlinks for a tool's config files under home."""
    for link_path, target in expected_links(tool, home):
        if link_path.is_symlink():
            if not force:
                continue
            link_path.unlink()
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(target)
