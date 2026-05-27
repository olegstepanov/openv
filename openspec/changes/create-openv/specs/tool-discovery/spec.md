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
- **WHEN** a file (not a directory) such as `zsh` exists at the dotfiles root
- **THEN** openv does NOT treat it as a tool

### Requirement: Tool directory structure is well-defined
Each tool directory SHALL contain any combination of the following, all optional:
- `install.sh` — run before config stowing; may have any valid shebang
- `post-install.sh` — run after config stowing; may have any valid shebang
- Any other files or subdirectories — treated as config files to be stowed

#### Scenario: install.sh is identified as the pre-install script
- **WHEN** a tool directory contains a file named `install.sh`
- **THEN** openv identifies it as the pre-install script for that tool

#### Scenario: post-install.sh is identified as the post-install script
- **WHEN** a tool directory contains a file named `post-install.sh`
- **THEN** openv identifies it as the post-install script for that tool

#### Scenario: Other files are identified as config files
- **WHEN** a tool directory contains files other than `install.sh` and `post-install.sh`
- **THEN** openv identifies them as config files to be linked into `$HOME`

### Requirement: Tool name is used as the default package name
The tool's directory name SHALL be used as the name of the package to install via the platform package manager, unless overridden by future manifest support.

#### Scenario: Tool named after its package
- **WHEN** a tool directory is named `zsh`
- **THEN** openv attempts to install the package named `zsh` via the detected package manager

