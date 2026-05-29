"""Tests for stow symlink creation logic."""

from pathlib import Path

import pytest

from openv.discovery import ToolInfo
from openv.stow import stow


def _make_file(path: Path, content: str = "") -> Path:
    """Create a file at path with the given content, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _make_tool(dotfiles_root: Path, name: str, config_files: list[str]) -> ToolInfo:
    """Create a ToolInfo with the given config files under dotfiles_root/<name>/."""
    tool_directory = dotfiles_root / name
    tool_directory.mkdir(parents=True, exist_ok=True)
    paths = [_make_file(tool_directory / config_file) for config_file in config_files]
    return ToolInfo(
        name=name,
        directory=tool_directory,
        package_dependencies=[name],
        config_files=paths,
    )


class TestStowNormalCreation:
    """Tests for basic symlink creation."""

    def test_creates_symlink_for_config_file(self, tmp_path: Path) -> None:
        """stow() creates a symlink in home pointing to the dotfile."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "zsh", [".zshrc"])
        stow(tool, home)
        link = home / ".zshrc"
        assert link.is_symlink()
        assert link.resolve() == (dotfiles / "zsh" / ".zshrc").resolve()

    def test_creates_intermediate_directories(self, tmp_path: Path) -> None:
        """stow() creates parent directories when the link path is nested."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "nvim", [".config/nvim/init.vim"])
        stow(tool, home)
        link = home / ".config" / "nvim" / "init.vim"
        assert link.is_symlink()

    def test_creates_multiple_symlinks(self, tmp_path: Path) -> None:
        """stow() creates symlinks for every config file in the tool."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "git", [".gitconfig", ".gitignore_global"])
        stow(tool, home)
        assert (home / ".gitconfig").is_symlink()
        assert (home / ".gitignore_global").is_symlink()


class TestStowIdempotency:
    """Tests for idempotent behavior when symlinks already exist."""

    def test_existing_correct_symlink_is_skipped(self, tmp_path: Path) -> None:
        """stow() skips a symlink that already points to the correct target."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "zsh", [".zshrc"])
        target = dotfiles / "zsh" / ".zshrc"
        link = home / ".zshrc"
        link.symlink_to(target)
        # Should not raise
        stow(tool, home)
        assert link.is_symlink()
        assert link.resolve() == target.resolve()

    def test_force_on_correct_symlink_leaves_it_intact(self, tmp_path: Path) -> None:
        """stow(force=True) recreates even a correct symlink (idempotent result)."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "zsh", [".zshrc"])
        target = dotfiles / "zsh" / ".zshrc"
        link = home / ".zshrc"
        link.symlink_to(target)
        stow(tool, home, force=True)
        assert link.is_symlink()
        assert link.resolve() == target.resolve()


class TestStowRegularFileConflict:
    """Tests for the crash fix: regular file exists at link path."""

    def test_raises_when_regular_file_exists(self, tmp_path: Path) -> None:
        """stow() raises FileExistsError when a regular file exists at the link path."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "zsh", [".zshrc"])
        # Simulate pre-existing regular file (e.g., from a previous manual setup)
        _make_file(home / ".zshrc", content="# existing zshrc")
        with pytest.raises(FileExistsError, match="regular file exists"):
            stow(tool, home)

    def test_force_removes_regular_file_and_creates_symlink(
        self, tmp_path: Path
    ) -> None:
        """stow(force=True) removes a regular file and creates the symlink."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "zsh", [".zshrc"])
        existing = _make_file(home / ".zshrc", content="# existing zshrc")
        assert existing.is_file() and not existing.is_symlink()
        stow(tool, home, force=True)
        link = home / ".zshrc"
        assert link.is_symlink()
        assert link.resolve() == (dotfiles / "zsh" / ".zshrc").resolve()


class TestStowDirectoryConflict:
    """Tests for directory existing at link path."""

    def test_raises_when_directory_exists(self, tmp_path: Path) -> None:
        """stow() raises FileExistsError when a directory is at the link path."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "zsh", [".zshrc"])
        (home / ".zshrc").mkdir()
        with pytest.raises(FileExistsError, match="directory exists"):
            stow(tool, home)

    def test_raises_even_with_force_when_directory_exists(self, tmp_path: Path) -> None:
        """stow(force=True) still raises when a directory exists at link path."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "zsh", [".zshrc"])
        (home / ".zshrc").mkdir()
        with pytest.raises(FileExistsError, match="directory exists"):
            stow(tool, home, force=True)


class TestStowWrongTargetSymlink:
    """Tests for symlinks pointing to the wrong target."""

    def test_raises_when_symlink_points_to_wrong_target(self, tmp_path: Path) -> None:
        """stow() raises FileExistsError when link exists but points elsewhere."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "zsh", [".zshrc"])
        wrong_target = _make_file(tmp_path / "other" / ".zshrc", content="# other")
        link = home / ".zshrc"
        link.symlink_to(wrong_target)
        with pytest.raises(FileExistsError, match="wrong target"):
            stow(tool, home)

    def test_force_relinks_wrong_target_symlink(self, tmp_path: Path) -> None:
        """stow(force=True) replaces a wrong-target symlink with the correct one."""
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        home.mkdir()
        tool = _make_tool(dotfiles, "zsh", [".zshrc"])
        wrong_target = _make_file(tmp_path / "other" / ".zshrc", content="# other")
        link = home / ".zshrc"
        link.symlink_to(wrong_target)
        stow(tool, home, force=True)
        expected_target = (dotfiles / "zsh" / ".zshrc").resolve()
        assert link.is_symlink()
        assert link.resolve() == expected_target
