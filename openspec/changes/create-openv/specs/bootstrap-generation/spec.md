## ADDED Requirements

### Requirement: generate-bootstrap produces a self-contained POSIX sh script
`openv generate-bootstrap --dotfiles URL` SHALL output a POSIX sh script to stdout. The script SHALL be valid under busybox ash (no bash-isms: no arrays, no `[[`, no process substitution) and SHALL require no tools beyond what a minimal UNIX system provides.

#### Scenario: Script is written to stdout
- **WHEN** user runs `openv generate-bootstrap --dotfiles https://github.com/user/dotfiles`
- **THEN** a complete, executable sh script is written to stdout

#### Scenario: Script can be redirected to a file
- **WHEN** user runs `openv generate-bootstrap --dotfiles URL > bootstrap.sh`
- **THEN** bootstrap.sh is a valid, standalone script that can be hosted on any server

### Requirement: Generated script pins the openv version that created it
The generated script SHALL include `OPENV_VERSION="<version>"` as a variable at the top of the file, where `<version>` is the version of openv that ran `generate-bootstrap`. The script SHALL use this variable when installing openv via pip.

#### Scenario: Version variable is present
- **WHEN** openv 1.2.3 generates a bootstrap script
- **THEN** the script contains `OPENV_VERSION="1.2.3"` near the top

#### Scenario: pip install uses pinned version
- **WHEN** the generated script runs on a new machine
- **THEN** it executes `pip3 install "openv==$OPENV_VERSION"`, installing exactly the pinned version

### Requirement: Generated script embeds the dotfiles URL
The generated script SHALL include `DOTFILES_URL="<url>"` as a variable at the top of the file, where `<url>` is the value passed to `--dotfiles`.

#### Scenario: URL is embedded
- **WHEN** user passes `--dotfiles https://github.com/user/dotfiles`
- **THEN** the script contains `DOTFILES_URL="https://github.com/user/dotfiles"`

### Requirement: Generated script installs prerequisites via the detected package manager
When run on a new machine, the generated script SHALL detect the platform's package manager and install git, python3, and pip (as a separate package where required) before proceeding.

#### Scenario: Installs prerequisites on apt system
- **WHEN** the script runs on a Debian/Ubuntu system
- **THEN** it runs `apt-get install -y git python3 python3-pip`

#### Scenario: Installs prerequisites on macOS with brew
- **WHEN** the script runs on macOS with Homebrew present
- **THEN** it runs `brew install git python3` (pip is bundled with brew's Python)

#### Scenario: Installs prerequisites on OpenWRT
- **WHEN** the script runs on OpenWRT with opkg
- **THEN** it runs `opkg install git python3 python3-pip`

#### Scenario: Installs prerequisites on Arch
- **WHEN** the script runs on Arch Linux with pacman
- **THEN** it runs `pacman -S --noconfirm git python` (pip is bundled with Arch's Python)

#### Scenario: Unknown package manager
- **WHEN** the script cannot detect a known package manager
- **THEN** it prints a human-readable error listing the required prerequisites and exits

### Requirement: Generated script clones the dotfiles repo and runs openv install
After installing prerequisites and openv, the generated script SHALL clone the dotfiles repository to `$HOME/.openv` and execute `openv install`.

#### Scenario: Full bootstrap sequence on a fresh machine
- **WHEN** the generated script is run on a machine with none of the prerequisites
- **THEN** it sequentially: detects package manager, installs git + python3 + pip, installs openv via pip, clones dotfiles to `$HOME/.openv`, and runs `openv install`

#### Scenario: Dotfiles directory already exists
- **WHEN** `$HOME/.openv` already exists when the script runs
- **THEN** the script skips cloning and proceeds directly to `openv install`

### Requirement: openv install uses ~/.openv as default dotfiles location
`openv install` (with no `--dotfiles` argument) SHALL default to `$HOME/.openv` as the dotfiles root.

#### Scenario: Default dotfiles location
- **WHEN** user runs `openv install` without `--dotfiles`
- **THEN** openv looks for tools in `$HOME/.openv`

#### Scenario: Explicit dotfiles location overrides default
- **WHEN** user runs `openv install --dotfiles /path/to/dotfiles`
- **THEN** openv looks for tools in `/path/to/dotfiles`
