"""Tests for tool discovery from a dotfiles repository root."""

from pathlib import Path

from openv.discovery import ToolInfo, discover


def _make_file(path: Path, content: str = "") -> Path:
    """Create a file at path with the given content, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestDiscover:
    """Tests for the discover() function."""

    def test_hidden_directory_is_ignored(self, tmp_path: Path) -> None:
        """Hidden directories at the dotfiles root are not treated as tools."""
        _make_file(tmp_path / ".git" / "config")
        result = discover(tmp_path)
        assert ".git" not in result

    def test_file_at_root_is_ignored(self, tmp_path: Path) -> None:
        """Files (not directories) at the dotfiles root are not treated as tools."""
        _make_file(tmp_path / "README.md")
        result = discover(tmp_path)
        assert "README.md" not in result

    def test_tool_directory_is_discovered(self, tmp_path: Path) -> None:
        """A non-hidden directory at the dotfiles root produces a tool entry."""
        (tmp_path / "zsh").mkdir()
        result = discover(tmp_path)
        assert "zsh" in result


class TestCreateToolFromDirectory:
    """Tests for per-tool directory introspection via discover()."""

    def _discover_single(self, dotfiles_root: Path, name: str) -> ToolInfo:
        tools = discover(dotfiles_root)
        return tools[name]

    def test_install_script_detected(self, tmp_path: Path) -> None:
        """install.sh at the top level is identified as install_script."""
        _make_file(tmp_path / "zsh" / "install.sh", "#!/bin/sh\necho hi")
        tool = self._discover_single(tmp_path, "zsh")
        assert tool.install_script is not None
        assert tool.install_script.name == "install.sh"

    def test_post_install_script_detected(self, tmp_path: Path) -> None:
        """post-install.sh at the top level is identified as post_install_script."""
        _make_file(tmp_path / "zsh" / "post-install.sh", "#!/bin/sh\necho done")
        tool = self._discover_single(tmp_path, "zsh")
        assert tool.post_install_script is not None
        assert tool.post_install_script.name == "post-install.sh"

    def test_top_level_script_not_in_config_files(self, tmp_path: Path) -> None:
        """install.sh and post-install.sh are excluded from config_files."""
        _make_file(tmp_path / "zsh" / "install.sh", "#!/bin/sh")
        _make_file(tmp_path / "zsh" / "post-install.sh", "#!/bin/sh")
        tool = self._discover_single(tmp_path, "zsh")
        names = {f.name for f in tool.config_files}
        assert "install.sh" not in names
        assert "post-install.sh" not in names

    def test_top_level_config_file_discovered(self, tmp_path: Path) -> None:
        """A plain config file at the top level appears in config_files."""
        _make_file(tmp_path / "zsh" / ".zshrc")
        tool = self._discover_single(tmp_path, "zsh")
        assert any(f.name == ".zshrc" for f in tool.config_files)

    def test_nested_config_file_discovered(self, tmp_path: Path) -> None:
        """Config files in subdirectories are recursively discovered."""
        _make_file(tmp_path / "nvim" / ".config" / "nvim" / "init.vim")
        tool = self._discover_single(tmp_path, "nvim")
        relative_paths = [f.relative_to(tmp_path / "nvim") for f in tool.config_files]
        assert Path(".config/nvim/init.vim") in relative_paths

    def test_install_sh_in_subdirectory_is_config_file(self, tmp_path: Path) -> None:
        """A file named install.sh inside a subdirectory is treated as a config file."""
        _make_file(tmp_path / "nvim" / ".config" / "nvim" / "install.sh")
        tool = self._discover_single(tmp_path, "nvim")
        relative_paths = [f.relative_to(tmp_path / "nvim") for f in tool.config_files]
        assert Path(".config/nvim/install.sh") in relative_paths

    def test_implicit_package_dependency(self, tmp_path: Path) -> None:
        """The tool directory name is always included as a package dependency."""
        (tmp_path / "zsh").mkdir()
        tool = self._discover_single(tmp_path, "zsh")
        assert "zsh" in tool.package_dependencies
