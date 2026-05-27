## Why

Setting up a new machine requires manually installing tools, copying config files, and remembering what goes where — a slow, error-prone process repeated from scratch every time. openv (Oleg's Portable Environment) solves this by encoding the full environment as a dotfiles repository that can be installed on any UNIX-like machine with a single command.

## What Changes

- New pip-installable CLI tool `openv` with two subcommands: `install` and `generate-bootstrap`
- Convention-based dotfiles repository format: each top-level directory is a tool, containing its config files plus optional `install.sh` / `post-install.sh` scripts
- Automatic package installation via the platform's native package manager (brew, apt, pacman, opkg)
- Config deployment via a Python symlink manager: mirrors tool directory structure under `$HOME`, consistent across all platforms
- `generate-bootstrap` produces a self-contained POSIX sh script that can be hosted anywhere and piped into `sh` on a fresh machine
- Dependency resolution: tools declare implicit deps (same-name package) and inferred deps (shebang of install scripts)
- Idempotent installs: already-installed packages and already-stowed configs are skipped unless `--force` is passed

## Capabilities

### New Capabilities

- `tool-discovery`: How openv locates and enumerates tools from a dotfiles repository root
- `tool-installation`: Per-tool install flow — package install, script execution, config stowing, post-install — including idempotency rules
- `dependency-resolution`: Implicit package deps, shebang-inferred tool deps, and topological ordering
- `bootstrap-generation`: Generating a self-contained POSIX sh bootstrap script with pinned openv version and embedded dotfiles URL

### Modified Capabilities

## Impact

- New Python package `openv` (PyPI), Python 3.11+ required
- New POSIX sh `bootstrap.sh` template embedded in the package
- Depends on: `questionary` or `rich` for interactive UI; standard library only for core logic
- Platform targets: macOS, Debian/Ubuntu, Arch, Raspbian, OpenWRT (busybox ash + opkg)
- No existing code affected — this is a greenfield project
