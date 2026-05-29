"""Tests for tool dependency graph construction and topological sort."""

from pathlib import Path

import pytest

from openv.dependencies import build_tool_dependency_graph
from openv.discovery import ToolInfo
from openv.installer import install_tools
from openv.packages import PackageManager


def _make_tool(name: str, package_dependencies: list[str] | None = None) -> ToolInfo:
    """Create a minimal ToolInfo for testing dependency logic."""
    return ToolInfo(
        name=name,
        directory=Path(f"/fake/{name}"),
        package_dependencies=package_dependencies
        if package_dependencies is not None
        else [name],
    )


class TestBuildToolDependencyGraph:
    """Tests for build_tool_dependency_graph()."""

    def test_tools_with_no_cross_dependencies_have_empty_edges(self) -> None:
        """Tools whose package deps don't overlap with tool names produce no edges."""
        git = _make_tool("git")
        vim = _make_tool("vim")
        tool_dependency_graph = build_tool_dependency_graph([git, vim])
        assert tool_dependency_graph == {"git": set(), "vim": set()}

    def test_self_loop_is_excluded(self) -> None:
        """A tool's own implicit same-name package dep must not create a self-loop."""
        zsh = _make_tool("zsh", package_dependencies=["zsh"])
        tool_dependency_graph = build_tool_dependency_graph([zsh])
        assert tool_dependency_graph["zsh"] == set()

    def test_direct_tool_dependency_is_captured(self) -> None:
        """When tool A lists tool B's name as a package dep, A depends on B."""
        git = _make_tool("git")
        delta = _make_tool("delta", package_dependencies=["delta", "git"])
        tool_dependency_graph = build_tool_dependency_graph([git, delta])
        assert tool_dependency_graph["delta"] == {"git"}
        assert tool_dependency_graph["git"] == set()

    def test_package_only_dependency_is_not_a_tool_edge(self) -> None:
        """Package deps that have no matching tool directory are not graph nodes."""
        zsh = _make_tool("zsh", package_dependencies=["zsh", "bash"])
        # "bash" has no ToolInfo, so it should not appear as a tool edge
        tool_dependency_graph = build_tool_dependency_graph([zsh])
        assert tool_dependency_graph["zsh"] == set()
        assert "bash" not in tool_dependency_graph


class TestTopologicalSortViaInstallTools:
    """Tests for topological sort behaviour exercised through install_tools()."""

    def test_independent_tools_install_without_error(self, tmp_path: Path) -> None:
        """Tools with no mutual dependencies can be installed in any order."""
        git = _make_tool("git")
        vim = _make_tool("vim")
        all_tools = {"git": git, "vim": vim}
        # Should not raise; we use a fake PackageManager and verify the call
        # completes. Actual installation is covered by integration tests.
        installed_order: list[str] = []

        import unittest.mock as mock

        with mock.patch("openv.installer.install_tool") as mock_install:
            mock_install.side_effect = lambda tool, pm, home, force=False: (
                installed_order.append(tool.name)
            )
            install_tools(
                selected_tools=[git, vim],
                all_tools=all_tools,
                pm=mock.MagicMock(spec=PackageManager),
                home=tmp_path,
                force=False,
            )

        assert set(installed_order) == {"git", "vim"}

    def test_dependency_is_installed_before_dependent(self, tmp_path: Path) -> None:
        """A tool that depends on another tool is installed after its dependency."""
        git = _make_tool("git")
        delta = _make_tool("delta", package_dependencies=["delta", "git"])
        all_tools = {"git": git, "delta": delta}

        installed_order: list[str] = []

        import unittest.mock as mock

        with mock.patch("openv.installer.install_tool") as mock_install:
            mock_install.side_effect = lambda tool, pm, home, force=False: (
                installed_order.append(tool.name)
            )
            install_tools(
                selected_tools=[delta],
                all_tools=all_tools,
                pm=mock.MagicMock(spec=PackageManager),
                home=tmp_path,
                force=False,
            )

        assert "git" in installed_order
        assert "delta" in installed_order
        assert installed_order.index("git") < installed_order.index("delta")

    def test_transitive_dependency_is_auto_included(self, tmp_path: Path) -> None:
        """Selecting only the leaf tool pulls in all transitive dependencies."""
        base = _make_tool("base")
        middle = _make_tool("middle", package_dependencies=["middle", "base"])
        leaf = _make_tool("leaf", package_dependencies=["leaf", "middle"])
        all_tools = {"base": base, "middle": middle, "leaf": leaf}

        installed_order: list[str] = []

        import unittest.mock as mock

        with mock.patch("openv.installer.install_tool") as mock_install:
            mock_install.side_effect = lambda tool, pm, home, force=False: (
                installed_order.append(tool.name)
            )
            install_tools(
                selected_tools=[leaf],
                all_tools=all_tools,
                pm=mock.MagicMock(spec=PackageManager),
                home=tmp_path,
                force=False,
            )

        assert set(installed_order) == {"base", "middle", "leaf"}
        assert installed_order.index("base") < installed_order.index("middle")
        assert installed_order.index("middle") < installed_order.index("leaf")

    def test_cycle_detection_raises_value_error(self, tmp_path: Path) -> None:
        """A circular dependency raises ValueError with a descriptive message."""
        tool_a = _make_tool("tool_a", package_dependencies=["tool_a", "tool_b"])
        tool_b = _make_tool("tool_b", package_dependencies=["tool_b", "tool_a"])
        all_tools = {"tool_a": tool_a, "tool_b": tool_b}

        import unittest.mock as mock

        with pytest.raises(ValueError, match="Circular tool dependency detected"):
            install_tools(
                selected_tools=[tool_a, tool_b],
                all_tools=all_tools,
                pm=mock.MagicMock(spec=PackageManager),
                home=tmp_path,
                force=False,
            )

    def test_indirect_cycle_detection_raises_value_error(self, tmp_path: Path) -> None:
        """An indirect cycle (A -> B -> C -> A) raises ValueError."""
        tool_a = _make_tool("tool_a", package_dependencies=["tool_a", "tool_b"])
        tool_b = _make_tool("tool_b", package_dependencies=["tool_b", "tool_c"])
        tool_c = _make_tool("tool_c", package_dependencies=["tool_c", "tool_a"])
        all_tools = {"tool_a": tool_a, "tool_b": tool_b, "tool_c": tool_c}

        import unittest.mock as mock

        with pytest.raises(ValueError, match="Circular tool dependency detected"):
            install_tools(
                selected_tools=[tool_a, tool_b, tool_c],
                all_tools=all_tools,
                pm=mock.MagicMock(spec=PackageManager),
                home=tmp_path,
                force=False,
            )
