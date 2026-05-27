## ADDED Requirements

### Requirement: Tool installation follows a fixed four-step sequence
For each selected tool, after installing dependencies, openv SHALL execute steps in order: (1) install package, (2) run install.sh, (3) link configs, (4) run post-install.sh. Steps with no corresponding content are skipped silently.

#### Scenario: Full install with all steps
- **WHEN** a tool has install.sh, config files, and post-install.sh
- **THEN** openv installs the package, runs install.sh, links configs, then runs post-install.sh in that order

#### Scenario: Tool with only config files
- **WHEN** a tool directory contains config files but no `install.sh` or `post-install.sh`
- **THEN** openv installs the package and links the configs without running any scripts

#### Scenario: Tool with only scripts
- **WHEN** a tool directory contains `install.sh` but no config files
- **THEN** openv installs the package and runs the script without attempting to link any configs

#### Scenario: `post-install.sh` is skipped when not present
- **WHEN** a tool has no `post-install.sh`
- **THEN** openv completes install without running post-install.sh and does not error

### Requirement: Config linking uses Python symlink manager on all platforms
openv SHALL deploy tool configs using a Python symlink manager: for each file in the tool directory (excluding `install.sh` and `post-install.sh`), create a symlink at the corresponding path under `$HOME`, creating intermediate directories as needed. This implementation is used on all platforms; GNU stow is not used.

#### Scenario: Config file is symlinked into $HOME
- **WHEN** a tool directory contains `.zshrc`
- **THEN** openv creates a symlink at `$HOME/.zshrc` pointing to the file in the tool directory

#### Scenario: Intermediate directories are created
- **WHEN** a config file lives at `.config/nvim/init.vim` within the tool directory
- **THEN** openv creates `$HOME/.config/nvim/` if it does not exist, then creates the symlink

#### Scenario: Behavior is identical on all platforms
- **WHEN** openv runs on macOS, Linux, or OpenWRT
- **THEN** the symlink structure produced is identical

### Requirement: install.sh and post-install.sh are excluded from linking
openv SHALL NOT create symlinks for `install.sh` or `post-install.sh` when linking a tool's configs.

#### Scenario: Scripts not symlinked
- **WHEN** a tool directory contains `install.sh`, `post-install.sh`, and `.zshrc`
- **THEN** only `.zshrc` is symlinked into `$HOME`; the scripts are not

### Requirement: Package installation is idempotent
openv SHALL skip package installation for a tool if the package is already installed on the system.

#### Scenario: Package already installed
- **WHEN** `zsh` is already installed
- **THEN** openv skips the package install step for the `zsh` tool and proceeds to scripts and linking

#### Scenario: Package not found aborts the run
- **WHEN** the package manager reports no package matching the tool name
- **THEN** openv aborts immediately with an error and does not proceed to scripts or linking

### Requirement: Config linking is idempotent by default
openv SHALL skip the entire tool installation — package install, scripts, and config linking — if all expected config symlinks already exist and point to the correct targets. When `--force` is passed, openv SHALL re-link configs and re-run scripts regardless.

#### Scenario: All symlinks already valid
- **WHEN** all config symlinks for a tool exist and point to the correct files
- **THEN** openv skips the tool entirely: scripts are not run, configs are not re-linked

#### Scenario: Partial link — some symlinks missing
- **WHEN** some but not all symlinks for a tool are present
- **THEN** openv runs `install.sh`, links configs (creates missing symlinks), then runs `post-install.sh`

#### Scenario: Force re-link
- **WHEN** all symlinks are valid but `--force` flag is passed
- **THEN** openv re-links the tool's configs, replacing existing symlinks, and re-runs both scripts

### Requirement: Pre-existing package installation is handled gracefully
openv SHALL proceed with scripts and config linking even if the tool's package was already present on the system before openv ran — whether installed by the OS, the user, or another tool.

#### Scenario: Package pre-installed, configs absent
- **WHEN** the tool's package is already installed but no config symlinks exist
- **THEN** openv skips package installation and proceeds with scripts and linking

### Requirement: Scripts are executed with their declared interpreter
openv SHALL execute `install.sh` and `post-install.sh` using the interpreter declared in their shebang line. If no shebang is present, the script SHALL be executed with `/bin/sh`.

#### Scenario: Script with bash shebang
- **WHEN** install.sh begins with `#!/bin/bash`
- **THEN** openv executes it as `bash install.sh`

#### Scenario: Script with no shebang
- **WHEN** install.sh has no shebang line
- **THEN** openv executes it as `sh install.sh`
