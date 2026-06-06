# Instructions for Claude

## Project

This repository contains **openv** (Oleg's Portable Environment) — a pip-installable CLI tool for bootstrapping a personal UNIX environment on a new machine.

The implementation lives in `src/openv/`, with tests in `tests/`. Design artifacts are kept in `openspec`.

## Tech stack

- Python 3.11+
- `pyproject.toml` packaging with `openv` CLI entry point
- Dependencies: `questionary`, `rich`
- POSIX sh for the generated bootstrap script template

## Project commands

Use the following Makefile targets:

- `make setup` to setup project environment on new machine or new worktree
- `make lint` to check code for syntax, style and type errors. Run for verification.
- `make test` to run tests. Run for verification.

## Git Workflow

- Always create a feature branch before starting new work
- Branch naming: `feature/<short-description>`, `fix/<issue-id>`, `chore/<task>`
- Never commit directly to `main`
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Make sure branch is up-to-date before pushing
- Open a PR with auto merge (`--auto`) when the feature is complete
