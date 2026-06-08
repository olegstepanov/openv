# openv

**Oleg's Portable Environment** — bootstrap a personal UNIX environment on a new
machine from a dotfiles repository.

> ⚠️ **Status: raw, pre-alpha.** This is a personal project under active,
> early development. The CLI, the dotfiles format, and the bootstrap flow may
> change without notice, and openv is **not yet published to PyPI**. Use at your
> own risk.

## What it does

Point openv at a dotfiles repository and it discovers the tools you keep there,
installs their system packages, links their config files into your home
directory, and runs their custom pre- and post-install scripts.

## Usage

### Bootstrap a new machine

The intended end-to-end flow. Generate a self-contained bootstrap script from
your dotfiles repository URL:

```sh
openv generate-bootstrap --dotfiles https://github.com/you/dotfiles.git > bootstrap.sh
```

Host that script somewhere, then run it on the new machine:

```sh
curl -fsSL https://example.com/bootstrap.sh | sh
```

The script detects the package manager (Homebrew, apt, or opkg), installs
prerequisites and openv, clones your dotfiles to `~/.openv`, and runs
`openv install`.

### Install directly

If openv and your dotfiles are already present, install tools directly:

```sh
openv install                 # interactive tool selector
openv install zsh tmux        # install named tools, skipping the selector
openv install --dotfiles PATH # use a dotfiles root other than ~/.openv
openv install --force         # re-link configs and re-run scripts
```

### Dotfiles layout

Each top-level directory in the dotfiles root is a **tool**. Within a tool
directory:

- an optional `install.sh` and `post-install.sh` are run during installation;
- all other files are treated as config files and linked into your home
  directory.

The default dotfiles root is `~/.openv`.

## Development

- See [`AGENTS.md`](AGENTS.md) for the tech stack, project conventions, and git
  workflow.
- Common [`Makefile`](Makefile) targets: `make setup` (set up the environment),
  `make lint` (style and type checks), `make test` (run the test suite).
- Design artifacts live in [`openspec/`](openspec/).

## Security

See [`SECURITY.md`](SECURITY.md) for how to report a vulnerability.

## License

MIT — see [`pyproject.toml`](pyproject.toml).
