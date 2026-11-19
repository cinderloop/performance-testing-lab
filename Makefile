# Every common action. `make help` lists them.
SCENARIO ?= scenarios/foundation-check.ts

.PHONY: help setup fetch up down reset ports run lint typecheck inspect test check format

help: ## list targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## install pinned JS and Python tooling, fetch the pinned demo
	npm ci
	uv sync --locked
	uv run perflab fetch

fetch: ## clone opentelemetry-demo 3.1.0 into demo/.upstream and verify the commit
	uv run perflab fetch

up: ## start the demo (loopback ports only, load generator never started)
	uv run perflab up

down: ## stop the demo and delete its volumes
	uv run perflab down

reset: ## run the reset protocol and verify the start state
	uv run perflab reset

ports: ## check that every published port is bound to 127.0.0.1
	uv run perflab ports

run: ## reset, then run SCENARIO in a k6 container (results/<run-id>/)
	uv run perflab run $(SCENARIO)

lint: ## ESLint, Prettier, ruff
	npm run lint
	uv run ruff check .
	uv run ruff format --check .

typecheck: ## tsc and mypy (strict)
	npm run typecheck
	uv run mypy

inspect: ## k6 inspect every script and prove the guard blocks a public target
	uv run perflab inspect

test: ## unit tests (Node test runner, pytest)
	npm test
	uv run pytest

check: lint typecheck inspect test ports ## everything CI runs

format: ## apply Prettier and ruff formatting
	npm run format
	uv run ruff format .
