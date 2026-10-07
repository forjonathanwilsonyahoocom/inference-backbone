from langchain_core.tools import tool
import json
import os
import subprocess

from typing import Any
from toolbox.util import safe_path, clip_mid


COMMAND_OUTPUT_LIMIT = 2000


@tool
def run_command(command: str, cwd: str = ".") -> str:
    """
    Run a non-interactive shell command in a workspace-relative directory.

    Use this for tests, formatting, compilation, inspection, and other
    non-interactive development commands.

    cwd must be relative to the workspace root. Use "." to run from the
    workspace root. The resolved working directory is included in the
    result.
    """
    blocked_fragments = [
        "rm -rf",
        "shutdown",
        "reboot",
        "mkfs",
        "dd if=",
        ":(){",
        "curl | sh",
        "wget | sh",
    ]

    normalized = command.lower().replace(" ", "")

    for fragment in blocked_fragments:
        if fragment.replace(" ", "") in normalized:
            return json.dumps({
                "command": command,
                "cwd": cwd,
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "error": f"Blocked potentially destructive command: {command}",
            }, indent=2)

    try:
        run_path = safe_path(cwd)

        result = subprocess.run(
            command,
            shell=True,
            cwd=run_path,
            capture_output=True,
            text=True,
            timeout=60,
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
            },
        )

        return json.dumps({
            "command": command,
            "cwd": cwd,
            "exit_code": result.returncode,
            "stdout": clip_mid(result.stdout, 1500),
            "stderr": clip_mid(result.stderr, 4000),
        }, indent=2)

    except subprocess.TimeoutExpired:
        return json.dumps({
            "command": command,
            "cwd": cwd,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": "Command timed out after 60 seconds.",
        }, indent=2)

    except Exception as exc:
        return json.dumps({
            "command": command,
            "cwd": cwd,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": f"{type(exc).__name__}: {exc}",
        }, indent=2)



def compress_run_command(result: Any, limit: int) -> str:
    """Return a truncated stdout/stderr and exit code.

    Parameters
    ----------
    result: dict
        Expected to contain ``stdout``, ``stderr`` and ``exit_code``.
    """
    try:
        result = json.loads(str(result))
    except Exception as e:
        print(f"compress_run_command fails  with {e} \n on \n {result}")
        return result
    
    if not isinstance(result, dict):
        return str(result)
        
    return json.dumps({
        "command": result['command'],
        "cwd":  result['cwd'],
        "exit_code": result['exit_code'],
        "stdout": clip_mid(result['stdout'], limit),
        "stderr": clip_mid(result['stderr'], limit),
    }, indent=2)

