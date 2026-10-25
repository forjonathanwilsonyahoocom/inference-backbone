import logging
import time
import docker
from docker.errors import DockerException, ImageNotFound
from fastapi import APIRouter, HTTPException
from contracts.general_contracts.docker_broker import RunRequest, RunResponse

from resolver import resolve_workspace


log = logging.getLogger(__name__)

on_demand_tools_router = APIRouter()

# Connects using the Docker environment available to the broker.
docker_client = docker.from_env()

# The caller chooses a logical runtime, never an arbitrary image.
ON_DEMAND_BUILD_DIRS = {
    "ast": "./plugin_builds/ast_outline",
    "text": "./plugin_builds/text_analysis",
}

DEFAULT_ENV_PER_IMAGE = {}

@on_demand_tools_router.post("/on_demand", response_model=RunResponse)
def run_ondemand_tool(request: RunRequest) -> RunResponse:
    """Use a regular `def`: Docker SDK calls are synchronous/blocking."""
    workspace = resolve_workspace(request.workspace)
    path_to_project = ON_DEMAND_BUILD_DIRS[request.runtime]

    log.info(f"workspace mapping from {workspace}, loading path_to_project {path_to_project}")
    container = None
    timed_out = False

    tag_name = path_to_project.split("/")[-1]

    image, logs = docker_client.images.build(
        nocache=request.nocache,
        path=path_to_project,
        tag=f"{tag_name}:latest",
        dockerfile="Dockerfile",  # optional if it's named Dockerfile at the context root
    )
    
    for line in logs:
        print(line)

    try:
        container = docker_client.containers.run(
            image=image,
            command=request.command,
            environment=DEFAULT_ENV_PER_IMAGE.get(request.runtime, {}),
            working_dir="/workspace",
            volumes={
                str(workspace): {
                    "bind": "/workspace",
                    "mode": "ro",
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
            network_disabled=True,
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

