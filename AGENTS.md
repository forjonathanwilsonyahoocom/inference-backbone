# Development conventions

## Repository structure

- `contracts/` contains shared Python data contracts.
- `observability/` contains shared observability wrapper for python prometheus client.
- `backbone-api/` contains the Backbone API service.
- `worker-agent/` contains the worker agent service.
- `validator-agent/` contains the validator service.
- `docker-broker/` contains the runtime broker service and the runtime images (`<adjust path>`).
- `tests/` contains repository-level tests.
- `jupyter/` contains user material.
- `readme/` contains images for the readme doc.
- `repository.init/` contains startup hints for graphdb.
- `grafana/` contains monitoring material.
- `prometheus/` contains monitoring material.
- `dev/` contains environment setup scripts and a test runner.
- `.venv/` if present indicates the Python environment has been set up inside
  the broker's python runtime (see below). It is not usable outside that runtime.

## Shared packages

`contracts` and `observability` are installable Python packages.

During development they must be installed editable, into the workspace venv,
through the broker:

    ["sh", "-c", "python -m venv .venv && .venv/bin/pip install -e ./contracts -e ./observability"]

Do not copy these packages into application directories.

Do not create duplicate copies of shared packages.

## Execution model

All code execution goes through the docker broker's python runtime. The agent
has no way to run Python or pip directly, and no way to restart the broker or
its own runtime.

Agents must not invoke `docker` or `docker compose` directly.

## Tests

Tests belong under the repository-level `tests/` directory.

Do not create additional test directories unless explicitly requested.

Run tests through the broker:

    ["./dev/test.sh"]

If no relevant tests exist, do not create tests merely to satisfy a workflow.

## Docker broker

The docker broker runs commands in an isolated python container. The agent's
workspace is mounted at `/workspace`, which is also the working directory.

### Request shape

- `workspace`: workspace ID (a single path segment, never a host path)
- `runtime`: always `python` for this project
- `command`: argv list, 1 to 32 items. There is no shell. Use
  `["sh", "-c", "..."]` only when you need pipes, `&&`, or redirects.
- `timeout_seconds`: 1 to 900, default 300

The response contains `exit_code` (null on timeout), `timed_out`, and `logs`
(tail only, truncated).

### Runtime image

The python image is defined by the `python` entry in `RUNTIME_IMAGES` in
`<path to broker main file>`, with its Dockerfile in `<path to python Dockerfile>`.
The image is the complete set of tools available: there is no `apt install` at
runtime and no root.

The broker may define other runtimes. They are unrelated to this project. Do
not use them, and do not modify their images or mappings.

### Python environment

Python dependencies are installed into a venv at `/workspace/.venv`, created
and populated through the broker. The rest of the filesystem is read-only, so
never install into the image's system Python.

- Create or refresh it with broker commands (see "Shared packages").
- Invoke tools via the venv (`.venv/bin/python`, `.venv/bin/pytest`) rather
  than relying on activation.
- The venv records the image's Python path and version. If the python image's
  Python version changes, delete and recreate `.venv`.
- Pip needs a writable cache and home. Set `PIP_CACHE_DIR` and `HOME` to
  locations under `/tmp` or `/workspace` if pip complains.

### Environment constraints

- The container runs as a non-root user with a read-only root filesystem.
  Only `/workspace` and `/tmp` are writable.
- CPU, memory, and process limits are enforced. Jobs are killed at the timeout.
- Network access may be restricted. Do not assume arbitrary hosts are reachable,
  including package indexes.

### Adjusting the broker

If the broker or the python image gets in the way of the task, fix it rather
than working around it. For example:

- a tool or system library is missing from the python image: add it to the
  Dockerfile (including build dependencies for packages that compile native
  extensions)
- the python version is wrong: update the `python` entry in `RUNTIME_IMAGES`
  and the Dockerfile
- a limit (memory, pids, tmpfs) is too low for a legitimate job: raise it
- pip or a tool cannot write its cache: set the right environment variable

**The agent cannot rebuild images or restart the broker.** Changes to the
Dockerfile, `RUNTIME_IMAGES`, or broker code have no effect until the user
rebuilds and restarts. This shapes how to work:

1. Prefer fixes that need no rebuild. Anything achievable inside `/workspace`
   (recreating the venv, pinning different package versions, setting
   environment variables in the command) should be tried first.
2. When a rebuild is genuinely required, batch all needed changes into one
   edit instead of making repeated small ones.
3. Do not attempt to verify a broker or image change yourself. It cannot take
   effect from inside the agent's session. Do not loop on retries.
4. Summarize what you changed and why, state the exact command(s) the user
   needs to run to rebuild and restart, and **ask the user to review**. Then
   stop and wait for the user to confirm it is applied before continuing
   work that depends on it.

Changes that **loosen isolation** must be called out prominently in the review
request, stated as a security-relevant change and not buried in a summary.
This includes enabling or widening network access, adding capabilities or
privileges, adding mounts, relaxing path validation, removing resource limits,
or running as root. Prefer the narrowest change that solves the problem.
Note that giving python network access to reach a package index is a
network change and must be flagged as one.

Never:
- mount the Docker socket or use privileged mode
- add mounts other than the single workspace mount
- let callers specify arbitrary image names or host paths
- install packages into the image's system Python at runtime

## Docker (deployment)

Compose files, deployment configuration, and production runtime setup are
maintained separately from the agent development workflow.

Do not:
- invoke docker or docker compose
- modify deployment configuration merely to make tests run
- add volume mounts to expose repository source to containers
- create duplicate copies of shared packages inside service directories

If application code cannot import a shared package, fix the workspace venv
through the broker (or the python image, with review) rather than introducing
a Docker mount.

## Code changes

Prefer small, explicit changes.

Do not reorganize the repository or introduce new frameworks without a concrete need.
