## ADDED Requirements

### Requirement: Tool installation follows a fixed four-step sequence
For each selected tool, openv SHALL execute steps in order: (1) install package, (2) run install.sh, (3) stow configs, (4) run post-install.sh. Steps with no corresponding content are skipped silently.

#### Scenario: Full install with all steps
- **WHEN** a tool has install.sh, config files, and post-install.sh
- **THEN** openv installs the package, runs install.sh, stows configs, then runs post-install.sh in that order

#### Scenario: Step is skipped when not present
- **WHEN** a tool has no post-install.sh
- **THEN** openv completes install without running post-install.sh and does not error

### Requirement: Config stowing uses GNU stow when available, Python fallback otherwise
openv SHALL use `stow` (GNU stow) if it is present on PATH to create symlinks from the tool directory to `$HOME`. When stow is not available, openv SHALL use a Python implementation that produces identical results: for each file in the tool directory (excluding install.sh and post-install.sh), create a symlink at the corresponding path under `$HOME`, creating intermediate directories as needed.

#### Scenario: stow is available
- **WHEN** `stow` is on PATH
- **THEN** openv invokes stow to link the tool directory into `$HOME`

#### Scenario: stow is not available (e.g. OpenWRT)
- **WHEN** `stow` is not on PATH
- **THEN** openv uses Python symlink fallback and produces the same symlink structure

#### Scenario: Intermediate directories are created
- **WHEN** a config file lives at `.config/nvim/init.vim` within the tool directory
- **THEN** openv creates `$HOME/.config/nvim/` if it does not exist, then creates the symlink

### Requirement: install.sh and post-install.sh are excluded from stowing
openv SHALL NOT create symlinks for `install.sh` or `post-install.sh` when stowing a tool's configs.

#### Scenario: Scripts not symlinked
- **WHEN** a tool directory contains `install.sh`, `post-install.sh`, and `.zshrc`
- **THEN** only `.zshrc` is symlinked into `$HOME`; the scripts are not

### Requirement: Package installation is idempotent
openv SHALL skip package installation for a tool if the package is already installed on the system.

#### Scenario: Package already installed
- **WHEN** `zsh` is already installed
- **THEN** openv skips the package install step for the `zsh` tool and proceeds to scripts and stowing

### Requirement: Config stowing is idempotent by default
openv SHALL skip stowing for a tool if all expected symlinks already exist and point to the correct targets. When `--force` is passed, openv SHALL re-stow regardless.

#### Scenario: All symlinks already valid
- **WHEN** all config symlinks for a tool exist and point to the correct files
- **THEN** openv skips stowing that tool's configs

#### Scenario: Partial stow — some symlinks missing
- **WHEN** some but not all symlinks for a tool are present
- **THEN** openv proceeds with stowing (creates missing symlinks)

#### Scenario: Force re-stow
- **WHEN** all symlinks are valid but `--force` flag is passed
- **THEN** openv re-stows the tool's configs, replacing existing symlinks

### Requirement: Package installed but configs not stowed proceeds normally
openv SHALL run install.sh, stow configs, and run post-install.sh even if the package is already installed, as long as configs have not yet been stowed.

#### Scenario: Package present, configs absent
- **WHEN** the tool's package is installed but no config symlinks exist
- **THEN** openv skips package installation and proceeds with scripts and stowing

### Requirement: scripts are executed with their declared interpreter
openv SHALL execute `install.sh` and `post-install.sh` using the interpreter declared in their shebang line. If no shebang is present, the script SHALL be executed with `/bin/sh`.

#### Scenario: Script with bash shebang
- **WHEN** install.sh begins with `#!/bin/bash`
- **THEN** openv executes it as `bash install.sh`

#### Scenario: Script with no shebang
- **WHEN** install.sh has no shebang line
- **THEN** openv executes it as `sh install.sh`
