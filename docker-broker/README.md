# Docker Broker

The **Docker Broker** is a lightweight FastAPI service that exposes two endpoints for running arbitrary Docker commands inside the workspace. It is used by the worker agent to execute tool‑specific Docker jobs (e.g., running a Python script or a Node container).

## Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/on_demand` | POST | Run a single Docker command synchronously. The request contains the image, command, and environment variables. |
| `/jobs` | POST | Submit a job that runs a Docker image with a specified runtime (Python, Node, Go, Rust, PHP, AST, or text). |
| `/health` | GET | Health‑check.

## Request/Response contracts

The broker uses the `RunRequest` and `RunResponse` models from `contracts/general_contracts/docker_broker.py`.

```json
{
  "nocache": false,
  "workspace": "/workspace",
  "runtime": "python",
  "command": ["python", "script.py"],
  "timeout_seconds": 120
}
```

The response contains the exit code, a timeout flag, and the combined stdout/stderr.

## Implementation notes

* The broker uses the Docker SDK (`docker-py`) to spin up containers.
* `ON_DEMAND_BUILD_DIRS` and `RUNTIME_IMAGES` map runtime names to Docker images.
* The broker runs in a separate container and is orchestrated by `docker-compose.yml`.

## Example usage

```bash
curl -X POST http://localhost:8000/on_demand \
  -H 'Content-Type: application/json' \
  -d '{"nocache":false,"workspace":"/workspace","runtime":"python","command":["python","script.py"],"timeout_seconds":60}'
```

---

For more details, see the `docker-broker/app/on_demand_tools.py` source.
