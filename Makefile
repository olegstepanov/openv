.PHONY: setup lint lint-fix lint-fix-unsafe test

setup:
	uv sync
	pre-commit install

lint:
	uv run dev/lint.py

lint-fix:
	uv run dev/lint.py --fix

lint-fix-unsafe:
	uv run dev/lint.py --force

test:
	uv run pytest
