## 1. Project Scaffold

- [ ] 1.1 Initialize pyproject.toml with package metadata, Python 3.11+ requirement, and `openv` CLI entry point
- [ ] 1.2 Create `src/openv/` package structure with empty module files (cli.py, installer.py, stow.py, discovery.py, platforms.py, deps.py)
- [ ] 1.3 Add dependencies to pyproject.toml: questionary (interactive UI), rich (output formatting)
- [ ] 1.4 Add `bootstrap.sh` template file to the package (embedded as a resource)

## 2. Platform Detection

- [ ] 2.1 Implement `platforms.py`: detect package manager from PATH (brew, apt-get, pacman, opkg)
- [ ] 2.2 Implement `install_package(name)` per platform, skipping if already installed
- [ ] 2.3 Implement `install_packages(names)` for installing the prerequisite list (git, python3, pip) with platform-specific package names

## 3. Tool Discovery

- [ ] 3.1 Implement `discovery.py`: scan dotfiles root, return list of tool names (non-hidden directories only)
- [ ] 3.2 Implement tool directory introspection: detect presence of install.sh, post-install.sh, and config files

## 4. Dependency Resolution

- [ ] 4.1 Implement shebang parser in `deps.py`: read first line of a script file, extract interpreter name
- [ ] 4.2 Implement dependency graph builder: implicit same-name package dep + shebang-inferred tool deps
- [ ] 4.3 Implement topological sort with cycle detection (raise clear error listing involved tools)
- [ ] 4.4 Implement auto-inclusion of dependency tools not explicitly selected by user

## 5. Stow / Symlink

- [ ] 5.1 Implement `stow.py`: walk tool dir, skip install.sh/post-install.sh, create symlinks under `$HOME` with intermediate directory creation
- [ ] 5.2 Implement idempotency check: verify all expected symlinks exist and point to correct targets
- [ ] 5.3 Implement `--force` re-link: remove and recreate existing symlinks

## 6. Tool Installer Orchestration

- [ ] 6.1 Implement `installer.py`: run the four-step sequence (package, install.sh, stow, post-install.sh) for a single tool
- [ ] 6.2 Wire up idempotency: skip package install if already present; skip stow if all symlinks valid (unless --force)
- [ ] 6.3 Implement script execution: run scripts with their declared shebang interpreter, fall back to `/bin/sh`
- [ ] 6.4 Implement full install loop: iterate tools in topological order, run installer per tool

## 7. Interactive Selector

- [ ] 7.1 Implement tool selection UI using questionary: checkbox list showing all discovered tools
- [ ] 7.2 Show tool name and whether it's already installed/stowed (status hint)
- [ ] 7.3 Pre-select tools that are already partially installed (package present, configs missing)

## 8. CLI

- [ ] 8.1 Implement `openv install` subcommand: `--dotfiles PATH` (default `~/.openv`), `--force`, optional positional tool list to skip interactive selector
- [ ] 8.2 Implement `openv generate-bootstrap --dotfiles URL` subcommand: read current package version, render bootstrap template, write to stdout

## 9. Bootstrap Script Template

- [ ] 9.1 Write `bootstrap.sh.template`: POSIX sh, variables at top (`OPENV_VERSION`, `DOTFILES_URL`), package manager detection function
- [ ] 9.2 Implement prerequisites installation in template: platform-aware install of git + python3 + pip (python3-pip on apt/opkg, bundled on brew/pacman)
- [ ] 9.3 Implement dotfiles clone step in template: skip if `$HOME/.openv` already exists
- [ ] 9.4 Implement pip install + openv invocation in template
- [ ] 9.5 Test generated script on macOS (brew), Ubuntu (apt), and OpenWRT (opkg) — fix any busybox ash incompatibilities

## 10. Tests

- [ ] 10.1 Unit test: tool discovery (hidden dirs ignored, files ignored, tool list correct)
- [ ] 10.2 Unit test: shebang parser (various shebangs, missing shebang, non-tool interpreter)
- [ ] 10.3 Unit test: topological sort (correct order, cycle detection error)
- [ ] 10.4 Unit test: symlink fallback (correct paths, intermediate dirs, skips scripts)
- [ ] 10.5 Unit test: idempotency checks (all symlinks valid → skip, partial → proceed)
- [ ] 10.6 Integration test: `openv install` on a temp dotfiles dir with a minimal tool
