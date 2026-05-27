## ADDED Requirements

### Requirement: Every tool implicitly depends on its same-named package
openv SHALL treat the package with the same name as the tool directory as an implicit dependency for every tool. This dependency ensures the package is installed before install.sh runs.

#### Scenario: Implicit package dependency
- **WHEN** a tool named `zsh` is selected
- **THEN** openv ensures the `zsh` package is installed before running any of the tool's scripts

### Requirement: Recognised shebang interpreters infer package dependencies
openv SHALL maintain an internal mapping of interpreter names to package names. When reading the shebang of `install.sh` or `post-install.sh`, openv SHALL extract the interpreter name and look it up in this mapping. If found, openv SHALL ensure the corresponding package is installed before executing the script. No tool directory for the interpreter is required in the dotfiles repo. Interpreters not present in the mapping are ignored.

The mapping in v1 contains one entry: `bash → bash`. New interpreters can be added to the mapping without structural changes.

#### Scenario: Recognised interpreter triggers package install
- **WHEN** `install.sh` begins with `#!/bin/bash`
- **THEN** openv installs the `bash` package (if not already installed) before running the script

#### Scenario: env-style shebang is also parsed
- **WHEN** `install.sh` begins with `#!/usr/bin/env bash`
- **THEN** openv extracts `bash`, finds it in the mapping, and installs the `bash` package

#### Scenario: Unrecognised interpreter infers no dependency
- **WHEN** `install.sh` begins with `#!/bin/sh` or `#!/usr/bin/env python3`
- **THEN** openv infers no package dependency and runs the script as-is

#### Scenario: No shebang infers no dependency
- **WHEN** `install.sh` has no shebang line
- **THEN** openv infers no package dependency

### Requirement: Dependencies are resolved into a topological install order
openv SHALL compute a valid topological ordering of selected tools such that each tool is installed only after all its dependencies. When a dependency is not explicitly selected by the user, openv SHALL install it automatically: running scripts and linking configs if the dependency has a tool directory in the dotfiles repo, or installing only the package if it does not. If the dependency package cannot be installed, the entire run is aborted.

#### Scenario: Dependency with tool directory is fully installed
- **WHEN** `delta` depends on `git` and `git` has a tool directory in the dotfiles repo
- **THEN** openv runs git's full install sequence (package + scripts + configs) before installing `delta`

#### Scenario: Dependency without tool directory installs package only
- **WHEN** a script shebang requires `bash` and there is no `bash` tool directory in the dotfiles repo
- **THEN** openv installs only the `bash` package before running the script

#### Scenario: Unresolvable dependency aborts the run
- **WHEN** a required dependency package cannot be installed by the package manager
- **THEN** openv aborts with an error before installing any further tools

#### Scenario: Independent tools have no required order
- **WHEN** `git` and `vim` have no dependencies on each other
- **THEN** openv may install them in any order

### Requirement: Circular dependencies are detected and reported as errors
openv SHALL detect cycles in the dependency graph before beginning installation and SHALL halt with a clear error message listing the tools involved in the cycle.

#### Scenario: Direct circular dependency
- **WHEN** tool A depends on tool B and tool B depends on tool A
- **THEN** openv halts before installing anything and reports the cycle

#### Scenario: Indirect circular dependency
- **WHEN** tool A → B → C → A
- **THEN** openv halts before installing anything and reports all tools in the cycle
