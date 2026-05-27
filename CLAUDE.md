# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

This repository contains the OpenSpec design artifacts for **openv** (Oleg's Portable Environment) — a pip-installable CLI tool for bootstrapping a personal UNIX environment on a new machine.

The implementation has not started yet. See `openspec/changes/create-openv/` for the full design:
- `proposal.md` — what and why
- `design.md` — key technical decisions
- `specs/` — per-capability requirements
- `tasks.md` — implementation checklist

Run `/opsx:apply` to begin implementing.

## Tech stack (planned)

- Python 3.11+
- `pyproject.toml` packaging with `openv` CLI entry point
- Dependencies: `questionary`, `rich`
- POSIX sh for the generated bootstrap script template
