from langchain_core.tools import tool
from typing import List, Dict, Optional
from agent.models import Iteration, AgentRequest


class AssessResultWrapper:
    """
    Holds the list of Iterations and the AgentRequest config.
    Provides @tool annotations that call functions requiring access to local run state.
    """
    def __init__(self, config: AgentRequest, iterations: Optional[List[Iteration]] = None):
        self.iterations: List[Iteration] = iterations or []
        self.config: AgentRequest = config

    def get_assess_result(self):
        @tool
        def assess_result(
            instance_number: int,
            utility: float,
            better_focus: Optional[str] = None,
        ) -> str:
            """Refine the utility score and retrieval focus for a previously executed tool result.

Parameters
----------
instance_number : int
    The stamped instance number of the iteration to update.
utility : float
    Score (0.0–1.0) indicating how helpful the result was.
better_focus : str | None, optional
    New focus query to replace the original about.

Returns
-------
str
    Confirmation message describing the update.
"""

            return assess_result_function(self.iterations, instance_number, utility, better_focus)

        return assess_result


def assess_result_function(
    iterations: List[Iteration],
    instance_number: int,
    utility: float,
    better_focus: Optional[str],
) -> str:
    """Internal helper for :func:`AssessResultWrapper.get_assess_result`.

    Parameters
    ----------
    iterations : List[Iteration]
        The current execution history.
    instance_number : int
        The stamped instance number of the Iteration to update.
    utility : float
        A score (0.0–1.0) measuring how much the result actually helps achieve the objective.
    better_focus : str, optional
        The new focus query for chunked compression. When provided, it replaces the
        original `about` argument sent to the tool that produced the result.

    Returns
    -------
    str
        Confirmation message describing the update applied.
    """

    target: Iteration | None = None
    for it in iterations:
        if getattr(it, "tool_call_result_instance_number", None) == instance_number:
            target = it
            break

    if target is None:
        return f"No iteration with instance_number {instance_number} found."

    if better_focus:
        if target.model_response and target.model_response.tool_calls:
            target.tool_call_result_chunk_query = better_focus
        else:
            print(
                f"Iteration {instance_number} has no tool call to update for better_focus {better_focus}"
            )

        target.compression_limit = None
        target.tool_call_result_chunks = None

    if utility != target.tool_call_result_utility:
        target.tool_call_result_utility = utility
        target.compression_limit = None

    return (
        f"Updated assessment of result instance_number {instance_number} "
        f"utility {utility} with focus: '{better_focus or target.tool_call_result_chunk_query}'."
    )
