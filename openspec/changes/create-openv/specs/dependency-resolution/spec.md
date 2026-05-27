## ADDED Requirements

### Requirement: Every tool implicitly depends on its same-named package
openv SHALL treat the package with the same name as the tool directory as an implicit dependency for every tool. This dependency ensures the package is installed before install.sh runs.

#### Scenario: Implicit package dependency
- **WHEN** a tool named `zsh` is selected
- **THEN** openv ensures the `zsh` package is installed before running any of the tool's scripts

### Requirement: Shebang lines in scripts infer tool dependencies
openv SHALL read the shebang line of `install.sh` and `post-install.sh` for each tool. If the shebang names an interpreter that matches a tool name in the dotfiles repo, that tool is added as a dependency.

#### Scenario: bash shebang infers bash dependency
- **WHEN** `install.sh` begins with `#!/bin/bash` and a `bash` tool exists in the dotfiles repo
- **THEN** the `bash` tool is added as a dependency and installed before the tool with the shebang

#### Scenario: sh shebang infers no tool dependency
- **WHEN** `install.sh` begins with `#!/bin/sh`
- **THEN** no tool dependency is inferred, since `sh` is a POSIX primitive not a managed tool

#### Scenario: No shebang infers no dependency
- **WHEN** `install.sh` has no shebang line
- **THEN** no tool dependency is inferred

#### Scenario: Shebang tool not in dotfiles repo
- **WHEN** `install.sh` begins with `#!/usr/bin/env python3` but no `python3` tool exists in the dotfiles repo
- **THEN** no tool dependency is inferred (interpreter is assumed to be a system tool)

### Requirement: Dependencies are resolved into a topological install order
openv SHALL compute a valid topological ordering of selected tools such that each tool is installed only after all its dependencies. Dependencies not explicitly selected by the user but required by selected tools SHALL be installed automatically.

#### Scenario: Dependency installed before dependent
- **WHEN** `zsh` depends on `bash` and the user selects `zsh`
- **THEN** openv installs `bash` before `zsh`, even if the user did not select `bash`

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
