# Development conventions

## Repository structure

- `contracts/` contains shared Python data contracts.
- `observability/` contains shared observability utilities.
- `backbone-api/` contains the Backbone API service.
- `worker-agent/` contains the worker agent service.
- `validator-agent/` contains the validator service.
- `tests/` contains repository-level tests.
- `jupyter/` contains exploratory notebooks.

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

## Docker

Agents must not use Docker.

Docker is used separately to build and run deployment images.

## Code changes

Prefer small, explicit changes.

Do not reorganize the repository or introduce new frameworks without a concrete need.

