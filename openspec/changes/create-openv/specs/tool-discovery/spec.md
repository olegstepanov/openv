## ADDED Requirements

### Requirement: Tools are discovered from dotfiles root
openv SHALL enumerate tools by listing non-hidden directories at the root of the dotfiles repository. Each directory represents exactly one tool; the directory name is the tool's identifier.

#### Scenario: Standard tool directory is discovered
- **WHEN** a directory named `zsh` exists at the dotfiles root
- **THEN** openv discovers a tool with identifier `zsh`

#### Scenario: Hidden directories are ignored
- **WHEN** a directory named `.git` or `.ssh` exists at the dotfiles root
- **THEN** openv does NOT treat it as a tool

#### Scenario: Files at root are ignored
- **WHEN** a file (not a directory) such as `README.md` exists at the dotfiles root
- **THEN** openv does NOT treat it as a tool

### Requirement: Tool directory structure is well-defined
Each tool directory SHALL contain any combination of the following, all optional:
- `install.sh` — run before config stowing; may have any valid shebang
- `post-install.sh` — run after config stowing; may have any valid shebang
- Any other files or subdirectories — treated as config files to be stowed

#### Scenario: Tool with only config files
- **WHEN** a tool directory contains only dotfiles (e.g. `.zshrc`, `.zshenv`) and no scripts
- **THEN** openv installs the package and stows the configs without running any scripts

#### Scenario: Tool with only scripts
- **WHEN** a tool directory contains `install.sh` but no config files
- **THEN** openv installs the package and runs the script without attempting to stow anything

#### Scenario: Tool with both scripts and configs
- **WHEN** a tool directory contains `install.sh`, `post-install.sh`, and config files
- **THEN** openv runs install.sh, stows configs, then runs post-install.sh

### Requirement: Tool name is used as the default package name
The tool's directory name SHALL be used as the name of the package to install via the platform package manager, unless overridden by future manifest support.

#### Scenario: Tool named after its package
- **WHEN** a tool directory is named `zsh`
- **THEN** openv attempts to install the package named `zsh` via the detected package manager

#### Scenario: Unknown package name fails gracefully
- **WHEN** the package manager reports that no package matches the tool name
- **THEN** openv logs a warning and continues with the remaining install steps (scripts and stowing) rather than aborting
