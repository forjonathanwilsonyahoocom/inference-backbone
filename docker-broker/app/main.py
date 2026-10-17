import logging
import time
from pathlib import Path
import docker
from docker.errors import DockerException, ImageNotFound
from fastapi import FastAPI, HTTPException
from contracts.general_contracts.docker_broker import RunRequest, RunResponse
import os

app = FastAPI()
log = logging.getLogger(__name__)

# Connects using the Docker environment available to the broker.
docker_client = docker.from_env()

# The caller chooses a logical runtime, never an arbitrary image.
RUNTIME_IMAGES = {
    "node": "node:22-trixie-slim",
    "go": "golang:1.24-trixie",
    "rust": "rust:1.88-slim-trixie",
    "php": "php:8.4-cli-trixie",
}

WORKSPACE_ROOT = Path(os.environ["WORKSPACE_ROOT"]).resolve()

def resolve_workspace(workspace: str) -> Path:
    # In a real service, look up authorization and workspace ownership here.
    # the caller supplies a path relative to the workspace never a host path.
    path = (WORKSPACE_ROOT / workspace).resolve()

    if not path.is_relative_to(WORKSPACE_ROOT) or not path.is_dir():
        raise HTTPException(status_code=404, detail="Workspace not found")

    return path


DEFAULT_ENV_PER_IMAGE = {"node" : {"HOME": "/tmp", "npm_config_cache": "/tmp/.npm"}}

@app.post("/jobs", response_model=RunResponse)
def run_job(request: RunRequest) -> RunResponse:
    """Use a regular `def`: Docker SDK calls are synchronous/blocking."""
    workspace = resolve_workspace(request.workspace)
    image = RUNTIME_IMAGES[request.runtime]

    log.info(f"workspace mapping from {workspace}")
    container = None
    timed_out = False

    try:
        container = docker_client.containers.run(
            image=image,
            command=request.command,
            environment=DEFAULT_ENV_PER_IMAGE.get(request.runtime, {}),
            working_dir="/workspace",
            volumes={
                str(workspace): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
            detach=True,

            # Example limits; tune these for your workloads.
            mem_limit="1g",
            nano_cpus=1_000_000_000,  # 1 CPU
            pids_limit=128,

            # Example hardening. Test these against your toolchains.
            user="10001:10001",
            read_only=True,
            tmpfs={"/tmp": "rw,nosuid,nodev,size=256m"},
            network_disabled=False, #danger ranger, we need to lock this down
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            init=True,
            labels={
                "managed-by": "agent-runtime-broker",
                "workspace": str(request.workspace),
            },
        )

        deadline = time.monotonic() + request.timeout_seconds

        # Poll container state so the broker enforces a wall-clock deadline.
        while time.monotonic() < deadline:
            container.reload()
            if container.status in {"exited", "dead"}:
                break
            time.sleep(0.25)
        else:
            timed_out = True
            try:
                container.stop(timeout=2)
            except DockerException:
                container.kill()

        result = container.wait(timeout=10)
        exit_code = result.get("StatusCode")

        # For production, stream/cap logs while the job runs rather than
        # buffering potentially unbounded output in memory.
        logs = container.logs(stdout=True, stderr=True).decode(
            "utf-8", errors="replace"
        )

        return RunResponse(
            exit_code=exit_code,
            timed_out=timed_out,
            logs=logs[-100_000:],  # response cap; not a memory-use cap
        )

    except ImageNotFound:
        log.exception("Configured runtime image is missing")
        raise HTTPException(status_code=500, detail="Runtime image unavailable")
    except DockerException:
        log.exception("Container execution failed")
        raise HTTPException(status_code=502, detail="Container execution failed")
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except DockerException:
                log.exception("Failed to remove execution container")

