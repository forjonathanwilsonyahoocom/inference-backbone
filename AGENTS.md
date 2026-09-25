# Development conventions

## Repository structure

- `contracts/` contains shared Python data contracts.
- `observability/` contains shared observability utilities.
- `backbone-api/` contains the Backbone API service.
- `worker-agent/` contains the worker agent service.
- `validator-agent/` contains the validator service.
- `tests/` contains repository-level tests.
- `jupyter/` contains user material.

## Shared packages

`contracts` and `observability` are installable Python packages.

During development they must be installed editable:

    pip install -e ./contracts
    pip install -e ./observability

Do not copy these packages into application directories.

Do not create duplicate copies of shared packages.

## Tests

Tests belong under the repository-level `tests/` directory.

Do not create additional test directories unless explicitly requested.

Run tests with:

    ./dev/test.sh

If no relevant tests exist, do not create tests merely to satisfy a workflow.

## Development environment

Agents develop and test directly in the repository's Python virtual environment.

Agents must not use Docker or Docker Compose.

Shared Python packages are installed editable:

    pip install -e ./contracts
    pip install -e ./observability

This means changes to `contracts/` and `observability/` are immediately visible
to Python processes in the development environment.

## Docker

Docker is a deployment/runtime concern and is maintained separately from the
agent development workflow.

Do not:
- invoke docker or docker compose
- modify Docker configuration merely to make tests run
- add volume mounts to expose repository source to containers
- create duplicate copies of shared packages inside service directories

If application code cannot import a shared package during development,
fix the development Python environment rather than introducing a Docker mount.


## Code changes

Prefer small, explicit changes.

Do not reorganize the repository or introduce new frameworks without a concrete need.

