.PHONY: install test lint fmt check clean

install:  ## Install project with dev dependencies
	uv pip install -e ".[dev]"
	uv run pre-commit install

test:  ## Run tests with coverage
	uv run pytest --cov --cov-report=term-missing

lint:  ## Run linter
	uv run ruff check src tests

fmt:  ## Format code
	uv run ruff format src tests
	uv run ruff check --fix src tests

check:  ## Run all checks (lint + test)
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run pytest --cov --cov-report=term-missing

clean:  ## Remove build artifacts
	rm -rf dist build *.egg-info .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
