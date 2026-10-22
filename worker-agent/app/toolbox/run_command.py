from langchain_core.tools import tool
import json
import os
import subprocess

from typing import Any
from toolbox.util import safe_path, clip_mid


COMMAND_OUTPUT_LIMIT = 2000


@tool
def run_command(about: str, command: str, cwd: str = ".") -> str:
    """Run a shell command in a workspace-relative directory.

    Parameters
    ----------
    about : str
        A short description of what the call is about, hint for summarization and retrieval.
    command : str
        The shell command to execute.
    cwd : str, optional
        Working directory relative to the workspace root (default: ".").

    Returns
    -------
    str
        JSON-encoded response with keys:
        * ``command`` – original command string
        * ``cwd`` – working directory
        * ``exit_code`` – process return code or ``None`` on error
        * ``stdout`` – clipped command output
        * ``stderr`` – clipped error output
        * ``error`` – present only when the command was blocked or failed
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

