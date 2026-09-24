from langchain_core.tools import tool
import subprocess

@tool
def run_command(command: str) -> str:
    """
    Run a non-interactive shell command inside the project workspace.
    Use this for formatting, tests, compilation, and inspection.
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
            return f"Blocked potentially destructive command: {command}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=60,
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
            },
        )

        output = (
            f"exit_code: {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

        if len(output) > 20_000:
            output = output[:20_000] + "\n...[output truncated]"

        return output

    except subprocess.TimeoutExpired:
        return "Command timed out after 60 seconds."
    except Exception as exc:
        return f"Command failed to run: {type(exc).__name__}: {exc}"

