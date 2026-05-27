## Context

openv is a greenfield project with no existing codebase. The primary constraint is broad platform support: macOS, mainstream Linux distros, Raspbian, and OpenWRT (busybox ash, opkg, constrained flash). The two-repository model (openv tool + user dotfiles) means the tool must work with any compliant dotfiles repo, not just the author's.

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

Python handles tool discovery, dependency resolution, interactive UI, and stow fallback cleanly. POSIX sh is limited on OpenWRT (busybox ash: no arrays, no `[[`, limited string ops) and would make these components fragile.

The bootstrap preamble must remain POSIX sh because Python isn't yet installed when it runs. It does only three things — detect the package manager, install prerequisites, and hand off to Python — which is well within POSIX sh's capabilities.

**Alternative considered**: Pure POSIX sh throughout. Rejected: dependency resolution with topological sort, shebang parsing, and a good interactive UI are all painful in POSIX sh and error-prone on busybox.

### 2. pip package with CLI entry point

pip is already required for the bootstrap flow (to install openv itself). Packaging openv as a proper pip package with a `[project.scripts]` entry point gives a real `openv` CLI command and handles transitive dependencies cleanly. No separate install step needed.

**Alternative considered**: Single-file penv.py fetched via curl/wget. Rejected: requires separately fetching requirements.txt, handling pip install of deps, and doesn't provide a proper CLI.

### 3. Convention-only tool discovery: directory name = tool name = default package name

No manifest file. Every non-hidden directory at the dotfiles repo root is a tool. The directory name is both the tool identifier and the default package to install. This makes adding a tool trivial: create a directory, drop in configs.

The tradeoff is that package names differing across platforms (e.g. `neovim` vs `nvim`) can't be expressed without a manifest. This is acceptable for v1; manifest support is explicitly deferred.

**Alternative considered**: `tool.yaml` manifest per tool. Deferred to v2.

### 4. GNU stow when available; Python symlink fallback otherwise

stow is the canonical dotfiles symlink manager but is absent from OpenWRT's opkg. Rather than depending on stow everywhere, openv calls `stow` when it's on PATH and falls back to a Python implementation (`os.symlink` + `pathlib`) that replicates the same behavior: walk tool directory, mirror structure under `$HOME`, create symlinks.

Both paths must produce identical results — the stow fallback is not a degraded mode.

### 5. Shebang inference for tool dependencies

Rather than requiring a manifest to declare "this tool needs bash", openv reads the first line of `install.sh` and `post-install.sh`. If the shebang names a tool in the dotfiles repo (e.g. `#!/bin/bash` → `bash`), that tool is added as a dependency automatically. This keeps the convention-only model while handling real dependency needs.

### 6. OPENV_VERSION pinned at generation time in bootstrap script

The generated `bootstrap.sh` stores the openv version that created it as `OPENV_VERSION` at the top of the script. The `pip install openv==$OPENV_VERSION` line in the script uses this variable, ensuring the bootstrap is reproducible and doesn't break when openv releases new versions.

Users who want to upgrade can regenerate the bootstrap script with a newer openv.

## Risks / Trade-offs

- **OpenWRT Python footprint (~30MB)**: Python 3.11 is large for flash-constrained devices. Mitigation: document this upfront; the user confirmed their routers have adequate storage.
- **Convention-only package names**: Package named differently across platforms will fail to install silently or with a confusing error. Mitigation: clear error messages; manifest support planned for v2.
- **pip availability**: pip is sometimes a separate package (python3-pip on apt/opkg). Mitigation: bootstrap.sh installs it explicitly via platform-specific package names.
- **Circular dependency detection**: A dotfiles repo with circular shebang deps (bash depends on zsh which depends on bash) would loop infinitely without detection. Mitigation: topological sort must raise a clear error on cycles.

## Open Questions

- Should `openv install` present the interactive selector every time, or only on first run? (Currently: always interactive, user picks tools each time.)
- Should failed tool installations abort the entire run or continue with remaining tools?
