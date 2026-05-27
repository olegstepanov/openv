## Context

openv is a greenfield project with no existing codebase. The primary constraint is broad platform support: macOS (brew), Debian-based Linux including Raspbian (apt), and OpenWRT (busybox ash, opkg, constrained flash). The two-repository model (openv tool + user dotfiles) means the tool must work with any compliant dotfiles repo, not just the author's.

## Goals / Non-Goals

**Goals:**
- Single-command machine bootstrap from a hosted URL
- Interactive tool selection on first install
- Idempotent re-runs (safe to run on already-configured machines)
- Extensible tool format (add a directory, get a working tool)
- Support all target platforms including OpenWRT

**Non-Goals:**
- Windows support
- Manifest-based tool metadata (deferred — convention-only for now)
- Remote secrets management (SSH keys are out of scope for v1)
- Rollback / uninstall

## Decisions

### 1. Python 3.11+ for core logic; POSIX sh only for bootstrap preamble

Python handles tool discovery, dependency resolution, interactive UI, and config symlinking cleanly. POSIX sh is limited on OpenWRT (busybox ash: no arrays, no `[[`, limited string ops) and would make these components fragile.

The bootstrap preamble must remain POSIX sh because Python isn't yet installed when it runs. It does only three things — detect the package manager, install prerequisites, and hand off to Python — which is well within POSIX sh's capabilities.

**Alternative considered**: Pure POSIX sh throughout. Rejected: dependency resolution with topological sort, shebang parsing, and a good interactive UI are all painful in POSIX sh and error-prone on busybox.

### 2. pip package with CLI entry point

pip is already required for the bootstrap flow (to install openv itself). Packaging openv as a proper pip package with a `[project.scripts]` entry point gives a real `openv` CLI command and handles transitive dependencies cleanly. No separate install step needed.

**Alternative considered**: Single-file penv.py fetched via curl/wget. Rejected: requires separately fetching requirements.txt, handling pip install of deps, and doesn't provide a proper CLI.

### 3. Convention-only tool discovery: directory name = tool name = default package name

No manifest file. Every non-hidden directory at the dotfiles repo root is a tool. The directory name is both the tool identifier and the default package to install. This makes adding a tool trivial: create a directory, drop in configs.

The tradeoff is that package names differing across platforms (e.g. `neovim` vs `nvim`) can't be expressed without a manifest. This is acceptable for v1; manifest support is explicitly deferred.

**Alternative considered**: `tool.yaml` manifest per tool. Deferred to v2.

### 4. Python-only symlink manager; no GNU stow dependency

openv manages config symlinks entirely in Python (`os.symlink` + `pathlib`): walk the tool directory, mirror its structure under `$HOME`, create symlinks, create intermediate directories as needed. stow is not used.

The "stow if available, fallback otherwise" approach was considered and rejected: it produces two code paths that must remain identical, makes debugging ambiguous ("did stow or Python run this?"), and adds an external dependency that is absent on OpenWRT anyway. The Python implementation is simple (~20 lines), covers all required behavior, and is consistent across every platform.

**Alternative considered**: Call GNU stow when on PATH, Python fallback otherwise. Rejected: two code paths, same-result requirement, no real benefit over pure Python.

### 5. Shebang inference via an extensible interpreter→package mapping

openv reads the shebang of `install.sh` and `post-install.sh` and looks up the interpreter name in an internal mapping of recognised interpreters to package names. If the interpreter is in the mapping, openv ensures that package is installed before executing the script. No tool directory is required in the dotfiles repo — these are direct package dependencies. Both `#!/bin/bash` and `#!/bin/env bash` are recognised.

Only bash is supported in v1, but adding more tools (zsh, fish, python) should be easy.

This keeps the model simple for v1 while making the common case (bash scripts on systems where bash may not be the default shell) work correctly out of the box.

### 6. OPENV_VERSION pinned at generation time in bootstrap script

The generated `bootstrap.sh` stores the openv version that created it as `OPENV_VERSION` at the top of the script. The `pip install openv==$OPENV_VERSION` line in the script uses this variable, ensuring the bootstrap is reproducible and doesn't break when openv releases new versions.

Users who want to upgrade can regenerate the bootstrap script with a newer openv.

## Risks / Trade-offs

- **OpenWRT Python footprint (~30MB)**: Python 3.11 is large for flash-constrained devices. Mitigation: document this upfront; the user confirmed their routers have adequate storage.
- **Convention-only package names**: Package named differently across platforms will fail to install silently or with a confusing error. Mitigation: clear error messages; manifest support planned for v2.
- **pip availability**: pip is sometimes a separate package (python3-pip on apt/opkg). Mitigation: bootstrap.sh installs it explicitly via platform-specific package names.
- **Circular dependency detection**: A dotfiles repo with circular shebang deps (bash depends on zsh which depends on bash) would loop infinitely without detection. Mitigation: topological sort must raise a clear error on cycles.

## Decisions (continued)

### 7. Interactive selector runs every time

`openv install` always presents the tool selector, even on machines that have been partially configured. This lets the user choose a different subset of tools on each run without needing a separate flag or saved state.

### 8. Failed tool installation aborts the run

If any step in a tool's install sequence fails (package install, script, or symlinking), openv halts immediately and reports the error. Partial installs are left as-is for the user to inspect. This avoids silently applying an incomplete environment and makes failures obvious.

### 9. E2E tests deferred to v2; unit and integration tests only in v1

v1 ships with unit tests (pure logic: discovery, shebang parsing, dependency resolution, symlink manager, idempotency) and one integration test (`openv install` on a temp dotfiles dir with a mocked package manager). Multi-platform E2E tests are deferred.

Planned v2 approach:
- **Debian/Ubuntu**: Docker container from scratch (`debian:bookworm`) — trivial, cheap, high fidelity
- **macOS**: self-hosted GitHub Actions runner on a Mac — no virtualization needed, no extra cost
- **OpenWRT**: start with `openwrtorg/rootfs` Docker image (opkg + busybox userspace, no real kernel); upgrade to full QEMU boot with official x86_64 images if gaps are found
